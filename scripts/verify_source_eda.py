"""Reconcile source EDA aggregates against local partitions and study evidence."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=Path('E:/Data/Jobs_2026_US'))
    args = parser.parse_args()
    out = ROOT / 'data/eda'
    data = json.loads((out / 'run.json').read_text(encoding='utf-8'))
    study = json.loads((ROOT / 'data/study/run.json').read_text(encoding='utf-8'))
    files = {f.name: f for f in args.data_dir.glob('jobs_2026_part_*.parquet')}
    assert files and set(files) == {f['file'] for f in data['files']}
    assert len(files) == len(data['files'])
    total = 0
    for record in data['files']:
        file = files[record['file']]
        parquet = pq.ParquetFile(file)
        assert parquet.metadata.num_rows == record['rows']
        assert file.stat().st_size == record['bytes']
        assert {f.name: str(f.type) for f in parquet.schema_arrow} == record['schema']
        with file.open('rb') as stream:
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == record['sha256']
        total += record['rows']
    counts = data['counts']
    assert Path(data['source_directory']).resolve() == args.data_dir.resolve()
    assert Path(study['source_directory']).resolve() == args.data_dir.resolve()
    if args.data_dir.name == 'Jobs_2026_US':
        assert data['distributions']['country'] == {'US': total}
        assert data['distributions']['posted_year'] == {'2026': total}
    assert total == counts['source_rows']
    assert total == counts['unique_nonmissing_ids'] + counts['duplicate_id'] + counts['missing_id']
    for key, distribution in data['distributions'].items():
        assert sum(distribution.values()) == total, key
        with (out / f'{key}.csv').open(encoding='utf-8', newline='') as stream:
            rows = list(csv.DictReader(stream))
        assert {r['value']: int(r['rows']) for r in rows} == distribution
        assert all(math.isclose(float(r['share_source_rows']), int(r['rows']) / total) for r in rows)
    with (out / 'missingness.csv').open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert {r['column'] for r in rows} == set(data['profiled_columns'])
    for row in rows:
        assert int(row['missing_rows']) == data['missing'][row['column']]
        assert int(row['present_rows']) + int(row['missing_rows']) == total
        assert math.isclose(float(row['missing_share']), int(row['missing_rows']) / total)
    signatures = lambda records: {(r['file'], r['rows'], r['sha256']) for r in records}
    assert data['study_manifest_matches'] == (signatures(data['files']) == signatures(study['files']))
    assert data['study_manifest_matches'], 'Refresh study and EDA: input snapshots differ'
    assert counts['duplicate_id'] == study['ledger'].get('duplicate_id', 0)
    assert counts['missing_id'] == study['ledger'].get('missing_id', 0)
    if counts['duplicate_id'] == counts['missing_id'] == 0:
        assert counts['january_september_2026_rows'] == study['ledger']['period_rows']
    print(f'EDA VERIFIED: {total:,} rows; hashes, schemas, aggregate denominators and study snapshot reconcile')


if __name__ == '__main__':
    main()
