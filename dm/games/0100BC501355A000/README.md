# Densha de GO!! Hashirou Yamanote Sen

## Base build survey

- Title ID: `0100BC501355A000`. Version 1.0.0, main build ID `72556bdf87ff54ea037a56370036d49b`.
- Unreal Engine with NVN and Nintendo SDK 9.3.1. The provisional profile loads `main`, `subsdk0` (NintendoSDK_movie), and `sdk`.
- The base archive passed full extraction and RomFS integrity checking. The RomFS contains 17 version 8 Unreal paks with 98,233 index entries total. The global Switch shader cache is in chunk 0.
- Native gameplay validation is pending on Mac and iOS.

## English localization

- The base game's control metadata advertises Japanese only. The Unreal engine and OnlineSubsystem plugins ship English localization resources. The pak indexes contain no game-specific `.locres` or `.locmeta` files.
- The game has cooked UI widgets and menu artwork, including a Yamanote tutorial selection card. Inventory the cooked text fields and the textures backing those screens before choosing how to replace them. CRIWARE audio and USM video are separate assets and need their own coverage check for spoken prompts and embedded captions.
- Verify title and main menus, settings, tutorials, mission selection, and one route through its results screen before marking an English build playable. Keep the translation tied to the tested game version and keep game assets in the local work folder.
