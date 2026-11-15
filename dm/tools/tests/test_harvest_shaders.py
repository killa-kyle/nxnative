import struct
import tempfile
import unittest
from pathlib import Path

from dm.tools import harvest_shaders


class HarvestShadersTests(unittest.TestCase):
    def test_record_preserves_code_and_control_offsets(self):
        key = '1de2753b7a6a0cb8'
        code = bytes.fromhex('78563412') + bytes(0x7c)
        control = bytes.fromhex('34127698') + bytes(0x87c)
        record = harvest_shaders.record(key, control, code)

        self.assertEqual(record[:16], b'BTCDBTCD' + bytes.fromhex(key))
        self.assertEqual(struct.unpack_from('<2I', record, 0x28), (len(control), len(code)))
        self.assertEqual(record[0x38:0x38 + len(code)], code)
        self.assertEqual(record[0x38 + len(code):], control)

    def test_harvest_assigns_stage_and_deduplicates_repeated_capture(self):
        key = 'adcf73fe12815ce9'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dump, package, profile = (root / name for name in ('dump', 'package', 'profile'))
            dump.mkdir()
            profile.mkdir()
            (dump / f'{key}_s1.ctl').write_bytes(bytes(0x40))
            (dump / f'{key}_s1.code').write_bytes(b'code')
            args = ['harvest_shaders.py', dump, package, profile]

            self.assertEqual(harvest_shaders.main(args), 0)
            shader_map = profile / 'shader_map.tsv'
            record = package / 'ps_harvest.bin'
            initial = (shader_map.read_bytes(), record.read_bytes())
            self.assertIn(f'ps_harvest.bin\t0\tpixel\t{key}'.encode(), initial[0])
            self.assertEqual(harvest_shaders.main(args), 0)
            self.assertEqual((shader_map.read_bytes(), record.read_bytes()), initial)
