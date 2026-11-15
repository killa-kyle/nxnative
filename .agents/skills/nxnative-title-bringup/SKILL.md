---
name: nxnative-title-bringup
description: Bring a newly extracted Switch title up in nxnative and get real pixels. Covers the shader capture loop (run → harvest → build → verify), why a frame counter is not a rendered frame, and the attribution traps. Use after scripts/build_ipa_from_nsp.py has produced a provisional profile and the host boots to nninitStartup or the frame loop, and whenever a run logs "shader ... is not in the shader map".
---

# nxnative title bring-up

Start with the asset inventory in docs/agents/04-graphics.md. Capture shader
variants from representative routes to fill gaps in the shipped archives. Set
DM_NVN_SHDUMP=shdump on iOS to capture under Documents. On the Mac, point it
at a capture folder on the project SSD.

## The loop

```bash
# 1. run it (headless is fine for capture) with a work-folder capture path
DM_NVN_SHDUMP=$R/shdump DM_ROOT=$R DM_ROMFS=$ROMFS DM_SAVE=$R/run/s DM_TEMP=$R/run/t DM_LANG=en-US DM_WINDOW=0 DM_AUDIO=0 \
  dm/host/dmhost $PATCHED > $R/run.log 2>&1

# 2. fold what it asked for into the package + map (idempotent; prints what it added)
python3 dm/tools/harvest_shaders.py $R/shdump $PKG $PROFILE

# 3. build the libraries — the Mac target compiles the metallibs the host loads
DMSH_TARGETS=mac python3 dm/gfx/tools/dmsh_build.py $PKG $CACHE

# 4. run again: expect "missing shaders 0" and draws per frame > 0
```

Repeat 1–4 until a run reports no `is not in the shader map` lines. Serve `DM_NVN_SHMAP` from the profile's
`shader_map.tsv`; `shdump/` is relative to the working directory unless `DM_NVN_SHDUMP=<dir>` says otherwise.

## Verify pixels, not frames

A cleared surface presents at 60 fps just like a rendered one, so "frames: 1500" proves nothing. Capture a real
frame and assert the draw count:

```bash
: > /tmp/ctl
DM_CTL=/tmp/ctl DM_WINDOW=1 dmhost ... &
sleep 12; echo 'shot /tmp/frame.png' >> /tmp/ctl      # DM_CTL is an appended command file, polled by offset
```

Then check both `N draws per frame` (> 0) and zero `[RED]` lines, and look at the PNG. `submit ... cycles` and
`GPU 0.2 ms` in the frame timing are the tell for a surface that is being cleared and presented but not drawn.

## Attribute a memory failure

Walk the guest's saved frame pointer at the map gate. Stack scans can contain
stale module addresses, so corroborate a return site against disassembly and
the allocation's arguments before changing pool sizes.

## Traps that cost real time

- **A shader library with source but no metallibs loads nothing.** `shader_lib.py expand` on an image built
  without the Metal target yields `.metal` + `.json` only, every draw is dropped, and the only symptom is a blank
  frame. Rebuild with `DMSH_TARGETS=mac` (host) or with `IOSOUT` (device) and check the image holds metallibs.
- **The device is a different memory world.** A title that renders on the Mac may still need tens of GB of
  address space at boot; see `.agents/skills/nxnative-memory-budget` and `docs/reference/memory.md` before
  blaming the renderer for a boot abort.
- **Paths on the device are the app container.** `Documents/log.txt` for logs, `Documents/shdump/` for captures,
  both pulled with `xcrun devicectl device copy from --domain-type appDataContainer`.
