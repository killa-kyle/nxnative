#!/usr/bin/env python3
"""Build a local RomFS overlay for early Densha 1.0.0 menus."""
import argparse
import hashlib
from pathlib import Path
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'gfx' / 'tools'))
from uepak import Pak

CONTENT = 'DgocGame/Content'
TABLES = {
    'DataTables/OutGame/OutGameMainMenuHeaderTextDataTable': (
        '7f0e0193949b0a7df6288426629705415818a758aa56334662ad9b2454317c2e',
        {0xd7: 'Routes', 0x19f: 'Setup', 0x201: 'Buy Points', 0x26f: 'Modes'},
    ),
    'DgocBlueprints/OutGame/InitializeData/DgocInitializeDataDialogContentDataTable': (
        '1535f054164d499831063b8b7a0bd192fcc9fa0cb728a22bbd5a83e0766d9643',
        {0x409: 'No save. Create one?',
         0x500: 'Autosave is on. Keep the game open while the save icon is shown.',
         0x647: 'Saving...'},
    ),
    'DgocBlueprints/OutGame/SlotSelect/Widgets/WI_SaveDataButton': (
        '93b3bd142e550c4415bca55b0f055db1fe7244bfeeffdaab311a10f4528ffa3c',
        {0x21d50: 'New Game', 0x22c3b: 'New Game'},
    ),
    'DgocBlueprints/OutGame/SlotSelect/Widgets/WI_SlotSelectMenu': (
        'd3ef7887f944fd175fd64f373f3bcc78c9c127e704aeb740d9950bc8ca09e203',
        {0x337da: 'Choose a save slot.', 0x33a7e: 'Choose a save slot.',
         0x34d58: 'New Game', 0x35c43: 'New Game', 0x36b2e: 'New Game'},
    ),
}


def replace_text(data, offset, text):
    count = -struct.unpack_from('<i', data, offset)[0]
    end = offset + 4 + 2 * count
    encoded = text.encode('utf-16le')
    if count < 2 or end > len(data) or data[end - 2:end] != b'\0\0':
        raise ValueError(f'invalid UTF-16 FString at {offset:#x}')
    if len(encoded) > 2 * (count - 1):
        raise ValueError(f'translation exceeds the export field at {offset:#x}')
    # Preserve export sizes and offsets so the original .uasset stays valid.
    data[offset + 4:end - 2] = encoded + b' \0' * (count - 1 - len(encoded) // 2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('romfs_image', type=Path)
    parser.add_argument('overlay', type=Path)
    parser.add_argument('--repak', default='repak')
    args = parser.parse_args()

    pak = Pak(str(args.romfs_image / CONTENT / 'Paks/pakchunk1-Switch.pak'))
    output = args.overlay / CONTENT / 'Paks/pakchunk1-English_P.pak'
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as temp:
        stage = Path(temp) / 'assets'
        for name, (digest, replacements) in TABLES.items():
            data = bytearray(pak.read(name + '.uexp'))
            if hashlib.sha256(data).hexdigest() != digest:
                parser.error(f'unsupported base export: {name}')
            for offset, text in replacements.items():
                replace_text(data, offset, text)
            path = stage / CONTENT / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.with_suffix('.uasset').write_bytes(pak.read(name + '.uasset'))
            path.with_suffix('.uexp').write_bytes(data)

        candidate = Path(temp) / output.name
        subprocess.run([args.repak, 'pack', '--version', 'V8B', stage, candidate], check=True)
        candidate.replace(output)


if __name__ == '__main__':
    main()
