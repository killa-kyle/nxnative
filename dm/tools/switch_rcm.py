#!/usr/bin/env python3
"""Push an RCM payload to a Nintendo Switch over USB from macOS, and see whether the console is in RCM.

    switch_rcm.py --list                 USB devices, marking an RCM (APX) target
    switch_rcm.py hekate.bin             push a payload to a waiting console
    switch_rcm.py hekate.bin --wait 60   wait up to a minute for it to appear
    switch_rcm.py hekate.bin --retries 3 retry a refused transfer with fresh handles

An RCM console enumerates as USB 0955:7321 ('NVIDIA Corp.' / 'APX'), interface class 0xff, bulk IN 0x81 and
out 0x01 with 512-byte packets. The payload protocol is the one fusee-launcher implements: a 16-byte
"smashing the stack for fun and profit" vendor control transfer arms the buffer, the payload goes out in 4 KB
bulk blocks, and a 4-byte 0x00000000 control transfer starts it. The console then re-enumerates and runs the
payload, so success looks like the APX device disappearing.

Only a payload crosses this: no keys, no console storage, nothing written to the console's NAND.

Dependency: pyusb (`python3 -m venv .venv && .venv/bin/pip install pyusb`). The repository's other tools are
stdlib-only, so this one is imported lazily and reports how to install it instead of failing at import time.
"""
import argparse
import sys
import time

VID, PID = 0x0955, 0x7321
BLOCK = 0x1000


def _usb():
    try:
        import usb.core
        import usb.util
    except ImportError:
        sys.exit("pyusb is not installed: python3 -m venv .venv && .venv/bin/pip install pyusb, then run this with .venv/bin/python")
    return usb.core, usb.util


def list_devices():
    core, util = _usb()
    rcm = None
    for d in core.find(find_all=True):
        try:
            product = util.get_string(d, d.iProduct) if d.iProduct else ""
        except Exception:
            product = "?"
        mark = ""
        if d.idVendor == VID and d.idProduct == PID:
            rcm = d
            mark = "  <-- RCM target"
        print(f"  {d.idVendor:04x}:{d.idProduct:04x}  {product}{mark}")
    return rcm


def wait_for_console(core, timeout, verbose):
    t0 = time.time()
    announced = False
    while time.time() - t0 < timeout:
        d = core.find(idVendor=VID, idProduct=PID)
        if d:
            return d
        if verbose and not announced:
            print("waiting for an RCM device (0955:7321)...", flush=True)
            announced = True
        time.sleep(0.25)
    return None


def push_once(core, util, dev, payload, verbose):
    try:
        dev.set_configuration()
    except core.USBError:
        pass                                    # macOS has configured it already
    try:
        util.claim_interface(dev, 0)
    except core.USBError as e:
        if verbose:
            print(f"claim_interface: {e} (continuing)")
    try:
        dev.ctrl_transfer(0x21, 0, 0, 0, b"\x00" * 16)
        for off in range(0, len(payload), BLOCK):
            dev.write(0x01, payload[off:off + BLOCK], timeout=5000)
    finally:
        try:
            util.release_interface(dev, 0)
        except core.USBError:
            pass
    try:
        dev.ctrl_transfer(0x21, 0, 0, 0, b"\x00\x00\x00\x00")
    except core.USBError:
        pass                                    # the console resets as the payload starts


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("payload", nargs="?", help="payload .bin (hekate, fusee, lockpick)")
    ap.add_argument("--list", action="store_true", help="list USB devices and mark an RCM target")
    ap.add_argument("--wait", type=float, default=30, help="seconds to wait for the console (default 30)")
    ap.add_argument("--retries", type=int, default=2, help="fresh-handle retries after a refused transfer (default 2)")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(argv[1:])
    core, util = _usb()
    if a.list or not a.payload:
        rcm = list_devices()
        print("RCM target present" if rcm else "no RCM target on USB")
        return 0 if rcm else 1
    with open(a.payload, "rb") as f:
        payload = f.read()
    if len(payload) % 4:
        payload += b"\x00" * (4 - len(payload) % 4)
    attempt = 0
    while True:
        attempt += 1
        dev = wait_for_console(core, a.wait, a.verbose)
        if not dev:
            print("no RCM device on USB: is the console in RCM (black screen, no boot logo, Vol+ held at power on) "
                  "and is the cable a data one, plugged straight into the Mac rather than a hub?")
            return 1
        try:
            push_once(core, util, dev, payload, a.verbose)
        except core.USBError as e:
            print(f"payload transfer refused ({e})")
            try:
                util.dispose_resources(dev)
            except Exception:
                pass
            if attempt > a.retries:
                print("the console's RCM buffer is wedged: hold Power ~15 s to force it off, re-enter RCM and retry. "
                      "A USB hub between the Mac and the console causes the same error.")
                return 2
            time.sleep(1.5)
            continue
        print(f"pushed {len(payload)} bytes of {a.payload}; the console should have left RCM (the APX device disappears)")
        return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
