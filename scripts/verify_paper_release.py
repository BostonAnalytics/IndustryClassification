"""Recheck the canonical release after all evaluations; reject mixed snapshots."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from build_naics import verify_snapshot

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=Path, default=Path('E:/Data/Jobs_2026_US'))
    args = parser.parse_args()
    manifest, fingerprint = verify_snapshot(args.data_dir)
    signatures = lambda files: {r['file']: r['sha256'] for r in files}
    expected = signatures(manifest['parts'])
    verified = []
    for name in ('study', 'multiclass', 'spark-study', 'eda'):
        path = ROOT/f'data/{name}/run.json'
        result = json.loads(path.read_text())
        assert signatures(result['files']) == expected, f'{name} uses a different snapshot'
        verified.append({'experiment': name, 'manifest_sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    snapshot = json.loads((ROOT/'data/naics/snapshot.json').read_text())
    assert snapshot['source_manifest_sha256'] == fingerprint
    assert signatures(snapshot['files']) == expected
    receipt = {'status': 'verified', 'verified_at_utc': datetime.now(timezone.utc).isoformat(),
               'release_id': manifest['layout_release'], 'source_manifest_sha256': fingerprint,
               'parts': len(expected), 'rows': manifest['rows'], 'experiments': verified,
               'checks': ['canonical release fully hashed after evaluation', 'four experiment input hashes equal release',
                          'NAICS explorer uses identical release']}
    (ROOT/'docs/maintenance/paper-release-verification.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(f"PAPER RELEASE VERIFIED: {len(expected)} parts; four evaluations and explorer match {manifest['layout_release']}")


if __name__ == '__main__':
    main()
