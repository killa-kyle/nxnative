#!/usr/bin/env python3
"""Fold a run's auto-captured shaders back into a package directory and its shader map.

    harvest_shaders.py <shdump dir> <package dir> <profile dir> [--dry-run]

The host writes every shader it cannot find in the map as `<key>_s<stage>.ctl` / `.code` (default-on;
`DM_NVN_SHDUMP=0` disables). This turns those pairs into the records `dmsh_build.py` understands and appends the
missing rows to the profile's `shader_map.tsv`, so the next build covers them. Run it after any run that logged
`[RED] shader ... is not in the shader map`, rebuild, and repeat until the log reports none.

Record layout (shader_split.py writes the same): 'BTCDBTCD' + key (8 bytes) + padding to 0x28, u32 control length
at +0x28, u32 code length at +0x2c, padded to 0x38, then the code area, then the control section.
"""
import struct
import sys
from pathlib import Path

STAGE = {0: ('vertex', 'vs'), 1: ('pixel', 'ps'), 2: ('geometry', 'gs'),
         3: ('hull', 'hs'), 4: ('domain', 'ds'), 5: ('compute', 'cs')}
MAGIC = b'BTCDBTCD'


def record(key: str, ctl: bytes, code: bytes) -> bytes:
    if len(ctl) < 0x40 or not code:
        raise ValueError('empty control section or code area')
    rec = bytearray(0x38)
    rec[:16] = MAGIC + bytes.fromhex(key)
    struct.pack_into('<2I', rec, 0x28, len(ctl), len(code))
    return bytes(rec) + code + ctl


def main(argv):
    if len(argv) < 4:
        print(__doc__.strip())
        return 2
    dump, pkg, prof = (Path(a) for a in argv[1:4])
    dry = '--dry-run' in argv
    mapp = prof / 'shader_map.tsv'
    have = set()
    rows = mapp.read_text().splitlines() if mapp.exists() else ['package\tindex\tstage\tdm_ctl_sha16\tsource']
    for ln in rows:
        c = ln.split('\t')
        if len(c) > 3 and not ln.startswith('#') and c[0] != 'package':
            have.add(c[3])

    added, skipped = [], 0
    for ctl in sorted(dump.glob('*_s*.ctl')):
        key, s = ctl.stem.rsplit('_s', 1)
        if not s.isdigit() or int(s) not in STAGE:
            print(f'  {ctl.name}: unknown stage, skipped')
            continue
        code = ctl.with_suffix('.code')
        if not code.exists():
            print(f'  {ctl.stem}: no code area, skipped')
            continue
        if key in have:
            skipped += 1
            continue
        stage_name, short = STAGE[int(s)]
        name = f'{short}_harvest.bin'
        blob = record(key, ctl.read_bytes(), code.read_bytes())
        idx = 0
        if (pkg / name).exists():
            idx = (pkg / name).read_bytes().count(MAGIC)
        if not dry:
            pkg.mkdir(parents=True, exist_ok=True)
            with open(pkg / name, 'ab') as f:
                f.write(blob)
        rows.append(f'{name}\t{idx}\t{stage_name}\t{key}\t#DUMP@{key}')
        have.add(key)
        added.append((key, stage_name))

    if added and not dry:
        mapp.write_text('\n'.join(rows) + '\n')
    for key, stage in added:
        print(f'  + {key} ({stage})')
    print(f'  {len(added)} shader(s) added, {skipped} already mapped'
          + ('  (dry run: nothing written)' if dry else ''))
    if not added:
        print('  the run asked for nothing new: the map already covers it')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
