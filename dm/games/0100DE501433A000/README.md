# Tetris Effect: Connected (`0100DE501433A000`)

Update 2.0.2 (v1179648), SDK 13 (nnSdk-13_3_2-Release), Unreal Engine 4.27, on NVN. Modules `main`, `subsdk0` (its video codec), `sdk`. Enhanced's Effects mode, 60 fps, on the iPhone.

## Duo validation (2026-11-15)

Signed and installed on a physical iPhone19,4 (iOS 27) and played: `up to frame 7200`, 0 breaks, 60.0 fps, `on-screen … dropped 0`, 160 draws per frame, GPU allocated 2.0 GB, footprint 2.73 GB. The save mount that had aborted every earlier build (`Break#1 reason=0 Result=0 svc at sdk+0x3ccf40`, at about frame 300) now passes and play continues.

Earlier bring-up states, for the record: the same build booted and rendered at 60 fps (`on-screen up to frame 300: 284 frames, dropped 3, p99 16.67 ms`) but aborted at the first save mount; the Mac host with the 64 GB probe profile ran `frames 1200, breaks 0, missing 0`.

## What it needs

| Setting | Where | Why |
|---|---|---|
| `game_args -SwitchVirtualAddressSpaceSize=3072` | `game.tsv` | Unreal's engine address region, and the window its own allocations fill. At 2048 the window was full by frame 300 and the engine aborted with its out-of-memory report; 3072 needs an alias more than 1 GB wider (a 4 GB alias died in `nninitStartup`) |
| `mem_reserve 0x138000000`, `mem_alias 0x104000000`, `mem_stack 0x4000000` | `game.tsv` | 4.875 / 4.0625 / 0.0625 GB: the widest block that still reserves on a phone (reserve + 1 GB of alignment slack is over iOS's 6 GB single-reservation cap) with an alias wide enough for the engine's own `AllocateAddressRegion(0xfe000000)` |
| `mem_used 0x1000000` | `game.tsv` | the pool the engine reports to itself: the game sizes its heap from the reported total less used memory |
| `app_pool 0xCD500000` | `game.tsv` | 3285 MiB, the Switch 4 GB model's application pool |
| FMallocBinned3 cut + `OBS_UE_MALLOC` gate | `patches.py` | UE 4.27's allocator reserves 37 GB of pools; the host allocator (`hle_uemalloc.c`, row `k_ue` for build `95c56ff8…`) takes the object instead |
| RedpointEOS cut | `patches.py` | the game asks for the online subsystem and dereferences the null result when the host refuses the online SDK (`main+0xb64b7c`) |

No `sdk` cuts: with the engine region capped, SDK 13's node area fits in the alias region.

## Memory

- **Resolved: the run aborted at the first save mount (`Break#1` about frame 300, `Ran out of memory allocating 34359738368 bytes with alignment 4096`).** Unreal's `FSwitchPlatformMemory` keeps one address region (`-SwitchVirtualAddressSpaceSize`, MB) and hands it out as its pool. The profile had 2048, so the window was `base 0x380000000 … end 0x400000000` (2 GB) with the cursor at `0x400e10000` — 100.7% of it — when the save mount asked for 16 MB. The message's `%llu` is the window **span**, not the request, so it reads as nonsense (34 GB) while the real shortfall was 14 MB. The window is the profile's `game_args` value; leave the argument off and the engine takes its 62 GB default, which is why a Mac probe profile runs and a phone does not.
- **How it was measured:** Unreal's pool object at `main+0x7490240` (`+0x28` base, `+0x30` end, `+0x50` bump cursor, 64 size classes from `+0x70`), read at the out-of-memory report `main+0xd4ec40`, reached from `0xd0c728` → `0xd0d1b8` → `0x337aaf8` → `0x337a7c8` → `0x3396248`. The region allocator behind it is the SDK's (`main+0xd0c568`), not the host's; a hardware watchpoint on the free-region count (`+0x8272ed0`) shows it is not a table bound. `DM_MEM_TRACE=1` now prints the block budget and the pool window at startup, and each `[mem] alias region mapped up to` line carries its percentage.
- **Resolved: the profile could not simply be made bigger.** The guest block is `mem_reserve + 1 GB` (the 1 GB slack that keeps the alias start 1 GB aligned), and iOS caps one reservation at 6 GB without the extended-virtual-addressing entitlement: `mem_reserve 0x160000000` (5.5 GB) dies in `mem_init` with `reserve guest AS` before the game starts. 4.875 GB is the largest block that reserves.
- **Resolved: the alias region must clear the engine's own region request.** At init `FSwitchPlatformMemory::StaticInit` asks for an address region of `0xfe000000` (3.97 GB). With a 4 GB alias the request fails beside the SDK's node area and the game breaks in `nninitStartup` (`main+0xd0ba3c`); 4.0625 GB works with a 3 GB window. Measured on the Mac with the phone profile, then confirmed on the Duo.

## Shaders

- The original iOS cache has 161 keys from `DM_NVN_SHDUMP` captures. The
  companion pak has an encrypted index. Its IoStore TOC and export payload
  are readable and contain inline NVN records in 10,271 export bundles.
- Run `DM_GAME=0100DE501433A000 python3 dm/gfx/tools/ue_iostore_inventory.py OUT TetrisEffect-Switch.utoc global.utoc`
  with the TOCs alongside their UCAS files. The catalog records shader key,
  stage, source chunk ID and decoded offset. `OUT/pairs` feeds
  `DM_NVN_CAPTURE_DIRS` in the existing splitter. For overlaps, use the
  packaged pair and include only capture keys absent from the static export.
- Measured on 2.0.2 v1179648: 10,353 static keys, 97 also seen in the original
  captures, and 10,417 unique keys after merging. Of 27 misses logged in the
  Duo session that included the MAX black screen, the static inventory covers
  24. The remaining keys are `1921216ef271df11`, `1b2697f3af11e908` and
  `b7002d5fe1056091`. Coverage outside the scanned export bundles remains open.

## Input

On the Mac the host maps it directly: `DM_KEYS` — J = A, K = B, U = X, I = Y, WASD = left stick, arrows = d-pad, Q/E = L/R, Z/C = ZL/ZR, Return = +, Tab = −, Space = shake (a controller shake, which is how Effects mode takes its "zone" input). On the phone the same mapping runs through `DmGamepad.m`; shaking the device is the shake.

## What is open

- Resolve the three outstanding session keys and rebuild the full merged cache. Verify the MAX route on the Duo.
- A playthrough beyond the menus: 7200 frames cover the boot, the save mount and the first minutes of play, not every Effects mode, the multiplayer or the Journey mode.
- The engine's 3 GB window is what a 4.875 GB block allows with a 4.0625 GB alias; a later scene that maps more than 3 GB of engine region would need [The SDK's address-region node area](../../../docs/reference/memory.md#the-sdks-address-region-node-area) cut to buy the alias room, as Pokémon Legends: Z-A's profile does.
