#!/usr/bin/env python3
"""Export inline NVN shaders from readable Unreal IoStore export bundles."""

import argparse
import json
from pathlib import Path

import shader_split as split
from uepak import Toc


def inventory(containers, output):
    output.mkdir(parents=True)
    pairs = output / 'pairs'
    pairs.mkdir()
    catalog = {}
    coverage = []
    for path in containers:
        toc = Toc(str(path))
        if toc.encrypted:
            raise ValueError(f'{path}: encrypted IoStore payload')
        bundles = toc.export_bundles()
        coverage.append({'source': str(path), 'export_bundles': len(bundles)})
        for index in bundles:
            chunk = toc.ids[index].hex()
            records = []
            split.ue_inline_shaders(toc.read(index), f'{path.name}#{chunk}', records)
            for source, stage, control, code in records:
                key = split.skey(control, code)
                if key in catalog:
                    previous = catalog[key]
                    if previous['stage'] != stage or not split.same_shader(
                        ((pairs / f'{key}.ctl').read_bytes(), (pairs / f'{key}.code').read_bytes()),
                        (control, code),
                    ):
                        raise ValueError(f'{source}: conflicting shader key {key}')
                    continue
                (pairs / f'{key}.ctl').write_bytes(control)
                (pairs / f'{key}.code').write_bytes(code)
                catalog[key] = {'stage': stage, 'source': str(path), 'chunk': chunk,
                                'offset': int(source.rsplit('#UE', 1)[1], 16)}
    manifest = {'coverage': coverage, 'shaders': catalog}
    (output / 'catalog.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    return catalog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='New directory for catalog and shader pairs')
    parser.add_argument('containers', nargs='+', type=Path, help='Explicit .utoc inputs')
    args = parser.parse_args()
    try:
        catalog = inventory(args.containers, args.output)
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')
    print(f'{len(catalog)} unique shader keys in {args.output / "catalog.json"}')


if __name__ == '__main__':
    main()
