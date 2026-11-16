# Densha de GO!! Hashirou Yamanote Sen

## Base build survey

- Title ID: `0100BC501355A000`. Version 1.0.0, main build ID `72556bdf87ff54ea037a56370036d49b`.
- Unreal Engine with NVN and Nintendo SDK 9.3.1. The provisional profile loads `main`, `subsdk0` (NintendoSDK_movie), and `sdk`.
- The base archive passed full extraction and RomFS integrity checking. The RomFS contains 17 version 8 Unreal paks with 98,233 index entries total. The global Switch shader cache is in chunk 0.
- The static shader split found 5,922 shaders. Native gameplay validation is pending on Mac and iOS.

## Open iOS address-space issue

The Mac probe observed a 62 GiB engine reservation returning to `main+0x60b9a0`. The provisional iPhone alias region is 4.375 GiB. The rewriter located the engine region size store at `main+0x60b998` and the `FMallocBinned3` vtable at `main+0x4966a70`, but its name getter is slot 17, an unsupported vtable layout. Identify the allocator method slots and constructor call before extending the host substitution. Re-run the reduced-alias boot check before packaging for the Duo.

## English localization

- The base game's control metadata advertises Japanese only. The Unreal engine and OnlineSubsystem plugins ship English localization resources. The pak indexes contain no game-specific `.locres` or `.locmeta` files.
- A scan of chunk 1 found 3,598 candidate length-prefixed UTF-16 Japanese strings across 173 cooked Blueprint and data table export files. These are candidate occurrences, including duplicates and possible internal text. A patch needs to preserve Unreal export sizes and offsets, or use the runtime text loader once the text serialization path is confirmed.
- The game has cooked UI widgets and menu artwork, including a Yamanote tutorial selection card. Inventory the cooked text fields and the textures backing those screens before choosing how to replace them. CRIWARE audio and USM video are separate assets and need their own coverage check for spoken prompts and embedded captions.
- Verify title and main menus, settings, tutorials, mission selection, and one route through its results screen before marking an English build playable. Keep the translation tied to the tested game version and keep game assets in the local work folder.
