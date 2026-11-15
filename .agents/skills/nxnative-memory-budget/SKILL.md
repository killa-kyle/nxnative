---
name: nxnative-memory-budget
description: Size and diagnose an nxnative game profile's guest address space (alias region, stacks, heap, and an Unreal engine's pool window) so a Switch title boots and keeps playing on an iPhone. Use when a game aborts with an out-of-memory report, `Break#1`, `reserve guest AS`, or dies at a scene/menu/save transition while the host shows plenty of memory free, and when adding a profile for a new title.
---

# nxnative memory budget

The host gives a game one reserved block of guest address space and partitions it. Get the partition wrong and the
game dies at a point that looks unrelated (a save mount, a menu, a boss) while the host reports gigabytes free. This
skill is the order to measure it in, and the two iOS limits that decide what is even possible.

## The four numbers

| Profile key | Meaning | Measured by |
|---|---|---|
| `mem_reserve` | the whole guest block | `host AS` log line; `dm/tools/check_memory.py` |
| `mem_alias` | region the SDK maps physical memory into (address regions, virtual address memory, stacks of guest threads) | `[mem] alias region mapped up to +X GB of Y` |
| `mem_stack` | guest thread stacks | profile |
| `app_pool` / `mem_used` | the pool and used memory `QueryMemoryInfo` reports; the SDK sizes the heap from them | `[mem] SetHeapSize …` lines |

The heap is what is left: `mem_reserve − 0x10000000 (guard) − alias − stack`.

## The two limits that bound every profile

1. **The block is reserved as `mem_reserve + 1 GB`.** The extra gigabyte keeps the alias start 1 GB-aligned
   (`hle_svc.c` `mem_init_once`). iOS caps one reservation at 6 GB without the extended-virtual-addressing
   entitlement, so **`mem_reserve` ≤ 5 GB**, and 4.875 GB is the reliable ceiling.
   Exceeding it fails *before the game runs*: `FATAL reserve guest AS` (now with the sizes printed).
2. **An Unreal engine's `-SwitchVirtualAddressSpaceSize=<MB>` in `game_args` is the pool window, not the alias.**
   `FSwitchPlatformMemory::StaticInit` keeps that region and the engine allocates its whole runtime out of it. Its
   own `AllocateAddressRegion(0xfe000000)` also has to fit in the alias beside the SDK's node area, so the alias must
   be **wider than the window**: measured on Tetris Effect 2.0.2, a 3 GB window ran with a 4.0625 GB alias and broke
   in `nninitStartup` with 4 GB — the gap is the SDK's ~1 GB node area beside it. 2304 MB is a legal value; it only failed
   beside the 3.125 GB alias that a 2048 MB window had booted in.

## Order of work

1. **Run the checker before a build, not after.** `python3 dm/tools/check_memory.py <title id>` (or `--all`) prints
   the budget, the reservation against the 6 GB cap, and the pool window, and fails a profile whose window is wider
   than its alias. A sign/install cycle is tens of minutes; a relaunch is seconds.
2. **Reproduce with the device profile on the Mac.** `DM_GAMES_DIR=<profile dir> make -C dm/host GAME=<id>` and run
   with the same `DM_ROMFS` etc. A "clean Mac run" with the 64 GB probe profile proves nothing about a phone — say
   which profile a benchmark used, every time.
3. **Watch the right number while it runs.** `DM_MEM_TRACE=1` prints the budget and the window at startup; each
   `[mem] alias region mapped up to +X GB of Y (Z%)` line is the alias high-water. `DM_ALIAS_WINDOWS=<MB>` reports
   per-window mapping when a game spreads out. `DM_SVC=1` logs every `MapPhysicalMemory`.
4. **At the abort, read the game's own pool, not the host's.** For Unreal 4.27 the pool object is at
   `main+0x7490240` (`+0x28` base, `+0x30` end, `+0x50` bump cursor, 64 size classes from `+0x70`). Break at the
   out-of-memory report (`main+0xd4ec40` on Tetris 2.0.2; reached from `0xd0c728` → `0xd0d1b8` → `0x337aaf8` →
   `0x337a7c8`). If `cursor` is at or past `end`, the window is the bug.
5. **Do not believe the message.** Unreal's `"Ran out of memory allocating %llu bytes with alignment %u"` prints the
   window **span** (34 GB for a 2 GB window), never the request. Compute the shortfall from `end − cursor`.
6. **Change the window in whole-GB steps and re-run.** Then re-run the checker, rebuild the host, and only after a
   clean host run rebuild the IPA.

## Traps that cost time

- **Guest frame-pointer backtraces are unreliable** through the rewriter's patched code. A breakpoint that never
  fires is evidence the path is different, not that the breakpoint is wrong; prefer a hardware watchpoint on the
  value (`SBThread`/`WatchAddress` in lldb) to find the writer, and the host's own backtrace for the truth.
- **`SBProcess.ReadMemory` returns `bytes`**, not `SBData`: `struct.unpack_from` it, do not call `GetU32`.
- **Set `process handle SIGSEGV -p true -s false -n true`** before running under lldb: the host uses SIGSEGV for
  dirty-page tracking, and `sig=14` in a log is the alarm that bounds the run, not a crash.
- **A game can be refused by the OS, not by the profile.** `FATAL reserve guest AS` is an mmap failure in
  `mem_init`, before any game code runs; no amount of window tuning fixes it.
- **Do not grow the alias to fix a full window.** They are different budgets; a window wider than the alias cannot
  be served and an alias wider than the block cannot be reserved.

## Where the knowledge lives

- `docs/reference/memory.md` — the mechanism entries (this skill's source of truth; add new findings there).
- `dm/games/<id>/README.md` — the per-game numbers and what was measured on that title.
- `dm/tools/check_memory.py` — the budget checker.
- `docs/env_switches.tsv` — `DM_MEM_TRACE`, `DM_ALIAS_WINDOWS`, `DM_SVC`.
