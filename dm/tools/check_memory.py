#!/usr/bin/env python3
"""Check a game profile's guest address-space budget before a build or a sign/install cycle.

    check_memory.py <title id> [<title id> …]   check these profiles (dm/games/<id>, or DM_GAMES_DIR)
    check_memory.py --all                       check every profile in dm/games
    check_memory.py --dir <profile dir>         check one profile directory

The budget is the three numbers in hle_svc.c's mem_init: the guest block is 0x10000000 of alignment guard,
the alias region, the stacks and the rest as heap. iOS decides two of them:

  * the block is reserved as `mem_reserve + 1 GB` (the 1 GB alias-alignment slack), and a single reservation is
    capped at 6 GB without the extended-virtual-addressing entitlement, so mem_reserve must stay at or below 5 GB;
  * an Unreal engine's `-SwitchVirtualAddressSpaceSize=<MB>` (game_args) is the pool window the engine's own
    allocations must fit in, and its nninitStartup also asks for one 0xfe000000 address region, so the alias
    region has to be wider than the window (measured: 3 GB window fits a 4.0625 GB alias, not a 4 GB one).

Everything is in GB unless the profile says otherwise. Exit status is 1 when a profile cannot work on a phone.
"""
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[2]
GUARD = 0x10000000           # hle_svc.c: the alias region starts this far into the guest block
ALIGN_SLACK = 1 << 30        # hle_svc.c: reserved on top of mem_reserve to 1 GB-align the alias start
IOS_CAP = 6 << 30            # iOS without the extended-virtual-addressing entitlement
UE_REGION = 0xFE000000       # Unreal's nninitStartup AllocateAddressRegion (Tetris Effect 2.0.2, DRAGON QUEST XI S)
MIN_HEAP = 0x4000000         # below this the SDK's SetHeapSize fails at boot (256 MB)

WINDOW = '-SwitchVirtualAddressSpaceSize='


def profile_dir(name_or_dir):
    """A profile directory: an explicit path with game.tsv, or dm/games/<id> / $DM_GAMES_DIR/<id>."""
    p = Path(name_or_dir)
    if (p / 'game.tsv').is_file():
        return p
    import os
    for base in (REPO / 'dm' / 'games', Path(os.environ['DM_GAMES_DIR']) if os.environ.get('DM_GAMES_DIR') else None):
        if base and (base / name_or_dir / 'game.tsv').is_file():
            return base / name_or_dir
    return None


def keys(d):
    out = {}
    for line in (d / 'game.tsv').read_text().splitlines():
        if not line or line.startswith('#'):
            continue
        f = line.split('\t')
        if len(f) >= 2:
            out[f[0]] = f[1]
    return out


def num(v, default=None):
    if v is None:
        return default
    v = v.strip()
    return int(v, 0) if v and not v.startswith('-') else default


def window_mb(args):
    if not args:
        return None
    for tok in args.split():
        if tok.startswith(WINDOW):
            try:
                return int(tok[len(WINDOW):])
            except ValueError:
                return -1
    return None


def check(d):
    """Return (errors, warnings, lines) for one profile directory."""
    k = keys(d)
    reserve, alias, stack = num(k.get('mem_reserve')), num(k.get('mem_alias')), num(k.get('mem_stack'))
    pool, used = num(k.get('app_pool')), num(k.get('mem_used'))
    err, warn, lines = [], [], []
    if not reserve or not alias or not stack:
        err.append('mem_reserve, mem_alias and mem_stack must all be set')
        return err, warn, lines
    heap = reserve - GUARD - alias - stack
    mmap = reserve + ALIGN_SLACK
    g = lambda n: n / 1073741824.0
    lines.append(f"reserve {g(reserve):.4f} GB = guard {g(GUARD):.3f} + alias {g(alias):.4f} + stack {g(stack):.4f} + heap {g(heap):.4f}")
    lines.append(f"mmap    {g(mmap):.3f} GB of the 6 GB iOS cap ({g(IOS_CAP - mmap):.3f} GB spare)")
    if heap <= 0:
        err.append(f'heap {g(heap):.4f} GB: alias + stack do not fit in the block (hle_svc.c dies with "invalid native boundaries")')
    elif heap < MIN_HEAP:
        warn.append(f'heap {g(heap):.4f} GB is under {g(MIN_HEAP):.3f} GB: SetHeapSize can fail at boot')
    if mmap > IOS_CAP:
        err.append(f'mmap {g(mmap):.3f} GB is over the 6 GB iOS cap: the device dies in mem_init with "reserve guest AS" '
                   f'(a Mac-only probe profile may exceed it deliberately)')
    elif mmap > IOS_CAP - (1 << 28):
        warn.append(f'mmap {g(mmap):.3f} GB leaves under 0.25 GB under the cap; Metal and the app need address space too')
    for name, v in (('mem_reserve', reserve), ('mem_alias', alias), ('mem_stack', stack)):
        if v & 0xFFF:
            err.append(f'{name} {v:#x} is not page aligned')
    win = window_mb(k.get('game_args'))
    if win:
        lines.append(f"pool window {win / 1024.0:.3f} GB (-SwitchVirtualAddressSpaceSize, {win} MB)")
        if win < 0:
            err.append('game_args -SwitchVirtualAddressSpaceSize= is not a number')
        elif win / 1024.0 > g(alias):
            err.append(f'pool window {win / 1024.0:.3f} GB is wider than the {g(alias):.3f} GB alias region: the engine fills the window and '
                       f'reports "Ran out of memory allocating" (the number it prints is the window span, not the request)')
        elif g(alias) - win / 1024.0 <= 1.0:
            warn.append(f'pool window {win / 1024.0:.3f} GB leaves {g(alias) - win / 1024.0:.3f} GB of alias: the SDK\'s node area (~1 GB) sits '
                        f'beside the engine\'s address region, so this only boots with the node-area cut in sdk_patches.py '
                        f'(measured: a 3 GB window fits 4.0625 GB of alias, not 4 GB; 2304 MB needs more than 3.125 GB)')
    if pool and used and used > pool:
        err.append(f'mem_used {used:#x} is above app_pool {pool:#x}: the heap sized from the pool would be negative')
    return err, warn, lines


def one(target, show_ok=True):
    d = profile_dir(target)
    if not d:
        print(f'{target}: no game.tsv (dm/games/{target} or $DM_GAMES_DIR/{target})')
        return 1
    err, warn, lines = check(d)
    rel = d.relative_to(REPO) if str(d).startswith(str(REPO)) else d
    if err or warn or show_ok:
        print(f'{rel}:')
        for l in lines:
            print(f'  {l}')
        for w in warn:
            print(f'  WARN  {w}')
        for e in err:
            print(f'  ERROR {e}')
        if not err and not warn:
            print('  OK    fits an iOS device')
    return 1 if err else 0


def main(argv):
    if '--all' in argv:
        rc = 0
        for d in sorted((REPO / 'dm' / 'games').iterdir()):
            if (d / 'game.tsv').is_file() and one(str(d), show_ok=False):
                rc = 1
        return rc
    if '--dir' in argv:
        i = argv.index('--dir')
        return one(argv[i + 1]) if i + 1 < len(argv) else 2
    args = [a for a in argv[1:] if not a.startswith('-')]
    if not args:
        print(__doc__.strip())
        return 2
    return max(one(a) for a in args)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
