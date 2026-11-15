"""Yacht Club shader archives and runtime dumps share the offline inventory."""
import hashlib
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[3]


def shader(stage, marker):
    ctl, code = bytearray(0x880), bytearray(0x100)
    ctl[:4] = bytes.fromhex('34127698')
    struct.pack_into('<I', ctl, 0x20, len(ctl))
    struct.pack_into('<I', ctl, 0x704, len(code))
    code[:4] = bytes.fromhex('78563412')
    struct.pack_into('<I', code, 0x30, stage << 10 | 1)
    code[0x80] = marker
    return bytes(ctl), bytes(code)


def ycd_record(ctl, code):
    return struct.pack('<II', len(ctl), len(code)) + ctl + code


class YachtClubShaderInventory(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.romfs = self.root / 'RomFS'
        self.romfs.mkdir()
        self.archive = self.romfs / 'shaders.pak.yc'
        (self.root / 'main').write_bytes(b'NSO0' + bytes(0xfc))
        self.capture = self.root / 'capture'
        self.capture.mkdir()

    def dump(self, ctl, code, filename=None):
        key = hashlib.sha256(ctl + code).hexdigest()[:16]
        stem = filename or key
        (self.capture / f'{stem}.ctl').write_bytes(ctl)
        (self.capture / f'{stem}.code').write_bytes(code)
        return key

    def split(self):
        return subprocess.run(
            [sys.executable, REPO / 'dm/gfx/tools/shader_split.py', self.romfs, self.root / 'main',
             self.root / 'pkg', self.root / 'map.tsv', self.root / 'facts.tsv'],
            env=dict(os.environ, DM_GAME='01007BB017812000', DM_GAMES_DIR='', DM_GAMES_FIRST='',
                     DM_NVN_CAPTURE_DIRS=str(self.capture), J='1'),
            capture_output=True, text=True,
        )

    def test_merge_keeps_static_provenance_and_correct_stage_packages(self):
        vertex_ctl, vertex_code = shader(1, 1)
        pixel_ctl, pixel_code = shader(5, 2)
        self.archive.write_bytes(b'YCD\0\x08\0\0\0' + bytes(16) + ycd_record(vertex_ctl, vertex_code))
        static_key = self.dump(vertex_ctl, vertex_code)
        pixel_key = hashlib.sha256(pixel_ctl + pixel_code).hexdigest()[:16]
        self.dump(pixel_ctl, pixel_code, pixel_key + '_s1')
        (self.capture / '._orphan.ctl').write_bytes(b'ignored')
        result = self.split()
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertIn('shaders: 2 (pixel 1, vertex 1)', result.stdout)
        table = (self.root / 'map.tsv').read_text()
        self.assertEqual(table.count(static_key), 1, table)
        self.assertIn(f'vertex\t{static_key}\t/shaders.pak.yc#YCD@0x18', table)
        self.assertIn(f'pixel\t{pixel_key}\t#DUMP@{pixel_key}', table)
        packed_pixel = (self.root / 'pkg' / 'ps_other.bin').read_bytes()
        self.assertEqual(packed_pixel[0x38:], pixel_code + pixel_ctl)

    def test_truncated_archive_reports_unreadable(self):
        ctl, code = shader(1, 1)
        self.archive.write_bytes(b'YCD\0\x08\0\0\0' + ycd_record(ctl, code)[:-1])
        result = self.split()
        self.assertIn('ends past the archive', result.stdout)
        self.assertIn('1 file(s) could not be read', result.stdout)

    def test_capture_key_must_match_bytes(self):
        self.dump(*shader(1, 1), '0000000000000000_s0')
        result = self.split()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('content key is', result.stderr)

    def test_capture_requires_both_parts(self):
        (self.capture / '0123456789abcdef_s1.ctl').write_bytes(b'partial')
        result = self.split()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('missing its control section or code area', result.stderr)


if __name__ == '__main__':
    unittest.main()
