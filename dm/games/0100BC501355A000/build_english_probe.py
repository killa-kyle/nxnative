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


TUTORIAL_DIR = 'DgocBlueprints/InGame/Screen/Tutorial/Scene/WI_Tutorial'
# EX_TextConst (localized) followed by EX_UnicodeStringConst.
BLUEPRINT_TEXT = bytes.fromhex('290134')
TUTORIALS = {
    'PreviousDeparture': (
        '1e1fbb2efd7ac5bc7474058dd9e457595c8c22afc4d5757d789cceb57e471897',
        {
            0xa98: "Welcome aboard! I'm Futaba, and I'll be helping you drive today.",
            0xd60: 'Arrive on time and stop as close to the marker as you can.',
            0xe65: 'Try stopping within 5 m of the station stop marker.',
            0xf83: 'The better you drive, the better your score. Give it a try!',
            0x10a7: 'Before departure, apply the brake so the train stays put.',
            0x125f: 'Pull the left stick back to apply the brake.',
        },
    ),
    'PreviousDeparture2': (
        '62d920d0ff899ddd09d1c8866a9dc1d487600ff0f8c710d5a845fae1512eb791',
        {
            0x9d2: 'Check the doors. You can only depart once they are all closed.',
            0xd3d: 'The door indicator lights up when the doors close.',
            0xe65: 'When it lights, press X to point and call. In handheld mode, you can also tap the screen.',
            0xfc9: 'Remember to point and call when the door indicator lights up.',
        },
    ),
    'PreviousDeparture3': (
        '94a1bc28be3163f7f05d0437817c53976dedeb779c6fcd412469e152d155da8e',
        {
            0xba2: 'This is the Mission Gauge. You will see it in Home Mode.',
            0xe98: 'The gauge drops over time and for mistakes. At zero you fail, except in this tutorial.',
            0xfee: "Let's learn how to drive.",
            0x10f9: 'This is the time until arrival. You score best when it is close to zero.',
            0x1249: 'This is the distance to the next stop marker. Aim for zero when you stop.',
            0x140d: 'Push the left stick forward to accelerate.',
            0x154b: 'This shows your current power or brake setting.',
            0x1687: 'Hold L to switch input type. Press ZL for the emergency brake.',
            0x17cd: 'We used simple controls here. Try other control types in Options.',
            0x1962: 'Pull the left stick back to brake.',
        },
    ),
    'Speed': (
        '320f0d38cea6b1473562f5df6606f21251783782959ac374fe1a6294509c92d6',
        {
            0xa87: 'The speed limit is about to change. Here is how it works.',
            0xc59: 'Adjust your speed before the new limit starts. The current limit is by the dial.',
            0xdba: 'When the warning appears, press X to point and call, or tap in handheld mode.',
            0xf00: 'After you call it out, use the left stick to stay within the limit.',
            0x1035: 'Going over the limit triggers automatic braking. Back to the controls!',
        },
    ),
    'Score': (
        '4f104848c47ae33d1604e1bb330bec9b389fd45bcda0bb402b608b7fb9c3d87a',
        {
            0xa38: 'A train is approaching. Dim your headlights before it passes.',
            0xc4b: 'Press B to dim the headlights. Press B again after the other train passes.',
            0xdb8: 'Leaving the headlights dimmed will lower your score.',
            0xee4: 'Back to driving. Remember to switch the headlights!',
        },
    ),
    'Gimmick': (
        '0d90ec805ae28529d1893a7af4cf41c2d4df25371b34555ff661bb342d68577c',
        {
            0xa87: 'A bridge is ahead. Sound the horn as you cross it!',
            0xc76: 'Press A to sound the horn.',
            0xd8d: "Time it right and the bridge glows green. Heart Points unlock Driver's Path missions.",
            0xec8: 'There are other places to use the horn. Try them as you learn the route.',
            0xfdb: 'Back to driving. Remember the horn!',
        },
    ),
    'Arrival': (
        '7e7bf01e2eceb7be17e67d3d02087c6c0d3ecbc7f5049a776dc2e19f42ce9fdc',
        {
            0xad6: 'The stop marker is coming up.',
            0xc84: 'Aim to stop within 5 m of the marker.',
            0xd88: 'This shows the distance to the stop marker.',
            0xe90: 'A train takes time to stop. Start braking before you enter the platform.',
            0xfa8: 'When you can, check the time until arrival too.',
            0x10b0: 'Back to driving. Good luck with the stop!',
        },
    ),
    'PreviousEnd': (
        '09cc7de0a562f76b796142b2f718a63bf3d60e4d3713f7d2e2900303e063c25f',
        {
            0xcb7: 'Well done! Keep driving and the controls will feel more natural.',
            0xd85: 'Once you are comfortable, try the other controls.',
            0xe6f: 'Need help? Open the game guide from the Support screen.',
        },
    ),
}


def replace_text(data, offset, text):
    count = -struct.unpack_from('<i', data, offset)[0]
    end = offset + 4 + 2 * count
    if count < 2 or end > len(data) or data[end - 2:end] != b'\0\0':
        raise ValueError(f'invalid UTF-16 FString at {offset:#x}')
    write_text(data, offset + 4, end - 2, text)


def write_text(data, start, end, text):
    encoded = text.encode('utf-16le')
    width = end - start
    if len(encoded) > width or '\0' in text:
        raise ValueError(f'translation does not fit the text field at {start:#x}')
    # Keep the original terminator and byte offsets, including Blueprint jumps.
    data[start:end] = encoded + b' \0' * ((width - len(encoded)) // 2)


def replace_blueprint_text(data, offset, text):
    if offset < len(BLUEPRINT_TEXT) or data[offset - len(BLUEPRINT_TEXT):offset] != BLUEPRINT_TEXT:
        raise ValueError(f'expected a Blueprint text literal at {offset:#x}')
    for end in range(offset, len(data) - 1, 2):
        if data[end:end + 2] == b'\0\0':
            break
    else:
        raise ValueError(f'unterminated Blueprint text at {offset:#x}')
    write_text(data, offset, end, text)


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
        assets = [(name, fields, replace_text) for name, fields in TABLES.items()]
        assets.extend((TUTORIAL_DIR + scene, fields, replace_blueprint_text)
                      for scene, fields in TUTORIALS.items())
        for name, (digest, replacements), replace in assets:
            data = bytearray(pak.read(name + '.uexp'))
            if hashlib.sha256(data).hexdigest() != digest:
                parser.error(f'unsupported base export: {name}')
            for offset, text in replacements.items():
                replace(data, offset, text)
            path = stage / CONTENT / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.with_suffix('.uasset').write_bytes(pak.read(name + '.uasset'))
            path.with_suffix('.uexp').write_bytes(data)

        candidate = Path(temp) / output.name
        subprocess.run([args.repak, 'pack', '--version', 'V8B', stage, candidate], check=True)
        candidate.replace(output)


if __name__ == '__main__':
    main()
