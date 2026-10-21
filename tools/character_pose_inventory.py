"""List captured body fingerprints once, preserving their native aliases.

Metadata only: no game session, image generation, uploads or image changes.
"""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--template', type=Path, required=True)
    parser.add_argument('--character', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    native = json.loads((args.template / 'character.json').read_text(encoding='utf-8-sig'))
    active = json.loads((args.character / 'character.json').read_text(encoding='utf-8-sig'))
    groups = defaultdict(list)
    for frame in native['frames']:
        groups[frame['id'].split('-', 1)[1]].append(frame)
    hd = defaultdict(list)
    for frame in active['frames']:
        if frame.get('hd'):
            hd[frame['id'].split('-', 1)[1]].append(frame)
    rows = []
    for fingerprint, frames in groups.items():
        matches = hd[fingerprint]
        rows.append({
            'body_hash': fingerprint,
            'native_ids': ';'.join(f['id'] for f in frames),
            'atlas_cells': ';'.join(str(f['cell']) for f in frames),
            'label': ';'.join(f.get('label', '') for f in matches),
            'hd_images': ';'.join(f['hd']['image'] for f in matches),
            'status': 'HD present' if len(matches) == 1 else 'ambiguous' if matches else 'HD missing',
        })
    result = {
        'template': str(args.template.resolve()),
        'character': str(args.character.resolve()),
        'captured_entries': len(native['frames']),
        'unique_body_hashes': len(rows),
        'duplicate_entries': len(native['frames']) - len(rows),
        'hd_covered_groups': sum(row['status'] == 'HD present' for row in rows),
        'missing_groups': sum(row['status'] == 'HD missing' for row in rows),
        'note': 'Observed poses only, not a complete game inventory. Hashes are palette-independent. CSV order is not animation order.',
        'groups': rows,
    }
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / 'inventory.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    with (args.out / 'poses.csv').open('w', newline='', encoding='utf-8-sig') as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys() if rows else [
            'body_hash', 'native_ids', 'atlas_cells', 'label', 'hd_images', 'status'])
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({key: value for key, value in result.items() if key != 'groups'}, indent=2))


if __name__ == '__main__':
    main()
