# Densha de GO!! Hashirou Yamanote Sen

## Base build survey

- Title ID: `0100BC501355A000`. Version 1.0.0, main build ID `72556bdf87ff54ea037a56370036d49b`.
- Unreal Engine with NVN and Nintendo SDK 9.3.1. The provisional profile loads `main`, `subsdk0` (NintendoSDK_movie), and `sdk`.
- The base archive passed full extraction and RomFS integrity checking. The RomFS contains 17 version 8 Unreal paks with 98,233 index entries total. The global Switch shader cache is in chunk 0.
- The static shader split found 5,922 shaders. Mac rendering passed a bounded startup run. Gameplay validation remains pending on Mac and iOS.

## Address space

The uncapped Mac probe observed a 62 GiB engine reservation returning to `main+0x60b9a0` and about 0.74 GiB mapped, with mappings reaching alias +37.86 GiB. The early UE4 `FMallocBinned3` vtable at `main+0x4966a70` has its name getter at slot 17 and no TryMalloc or TryRealloc slots. The rewriter replaces the constructor call at `main+0x60be98` through the shared host allocator path. With a 4.375 GiB alias window on Mac, the existing engine-region gate at `main+0x60b998` reduced the request to 4.0625 GiB, the host malloc zone took over, and the process reached 300 presented frames using the compiled shader library. Device validation is pending.

## English localization

- The base game's control metadata advertises Japanese only. The Unreal engine and OnlineSubsystem plugins ship English localization resources. The pak indexes contain no game-specific `.locres` or `.locmeta` files.
- A scan of chunk 1 found 3,598 candidate length-prefixed UTF-16 Japanese strings across 173 cooked Blueprint and data table export files. These are candidate occurrences, including duplicates and possible internal text. A patch needs to preserve Unreal export sizes and offsets, or use the runtime text loader once the text serialization path is confirmed.
- The game has cooked UI widgets and menu artwork, including a Yamanote tutorial selection card. Inventory the cooked text fields and the textures backing those screens before choosing how to replace them. CRIWARE audio and USM video are separate assets and need their own coverage check for spoken prompts and embedded captions.
- Verify title and main menus, settings, tutorials, mission selection, and one route through its results screen before marking an English build playable. Keep the translation tied to the tested game version and keep game assets in the local work folder.

A local proof of concept replaces five fixed-width UTF-16 fields in two cooked
exports. The Mac host opens the version 8 patch pak through
`DM_ROMFS_OVERLAY`, and the new-save prompt rendered its English sentence.
The confirmation button and control hints on the same screen still need
translation. The probe also stages English menu headers, save-slot labels and autosave
messages. Those additions and iOS overlay delivery are pending visual validation.

Run `build_english_probe.py <RomFS.img> <overlay directory> --repak <repak>`
with repak 0.2.3. The script checks each original export’s fingerprint and
writes a separate pak. Use the overlay directory as `DM_ROMFS_OVERLAY` in the
Mac host test. Keep the rebuilt pak and its source assets outside Git.
