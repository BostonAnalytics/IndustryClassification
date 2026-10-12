"""Verify a published snapshot and export aggregate-only website evidence."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import re

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
LEVELS = (4, 5, 6)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify_snapshot(root, expected_parts=20):
    root = Path(root)
    if (root / 'PUBLICATION_IN_PROGRESS.json').exists():
        raise ValueError('Source publication is in progress')
    manifest_bytes = (root / 'manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    parts = manifest['parts']
    names = [p['file'] for p in parts]
    if len(parts) != expected_parts or len(set(names)) != len(parts):
        raise ValueError(f'Expected exactly {expected_parts} unique parts')
    if any(not re.fullmatch(r'jobs_2026_part_\d+\.parquet', name) for name in names):
        raise ValueError('Invalid partition path')
    if set(names) != {p.name for p in root.glob('jobs_2026_part_*.parquet')}:
        raise ValueError('Canonical part set differs from manifest')
    verified = manifest.get('status') == 'verified'
    if not verified and (root / 'verification.json').exists():
        verification = json.loads((root / 'verification.json').read_bytes())
        verified = (verification.get('status') == 'verified'
                    and verification.get('rows') == manifest['rows']
                    and verification.get('parts') == parts
                    and verification.get('full_ordered_value_replay') is True
                    and verification.get('changed_cells') == 0)
    if not verified or not manifest.get('layout_release'):
        raise ValueError('A verified layout release is required')
    schema = None
    for part in parts:
        path = root / part['file']
        if sha(path) != part['sha256']:
            raise ValueError('Partition hash mismatch: ' + part['file'])
        pf = pq.ParquetFile(path)
        if pf.metadata.num_rows != part['rows']:
            raise ValueError('Partition row count mismatch')
        if schema is not None and not schema.equals(pf.schema_arrow, check_metadata=True):
            raise ValueError('Partition schemas differ')
        schema = pf.schema_arrow
    if sum(p['rows'] for p in parts) != manifest['rows']:
        raise ValueError('Manifest row total differs')
    return manifest, hashlib.sha256(manifest_bytes).hexdigest()


def text(value):
    return '' if value is None else str(value).strip()


def aggregate(rows):
    groups = defaultdict(lambda: {'postings': 0, 'employers': set(), 'names': Counter()})
    employers, ids = set(), set()
    counts = Counter()
    coverage = {n: Counter() for n in LEVELS}
    months = Counter()
    for row in rows:
        counts['posting_records'] += 1
        identifier = row.get('ID')
        if identifier is None:
            counts['missing_ids'] += 1
        else:
            ids.add(str(identifier))
        employer = ' '.join(text(row.get('COMPANY_NAME')).casefold().split())
        if employer in {'', 'unknown', 'unclassified', 'none', 'null', 'nan'}:
            employer = ''
            counts['postings_without_employer_name'] += 1
        else:
            employers.add(employer)
        stamp = text(row.get('POSTED'))[:7]
        months[stamp if re.fullmatch(r'\d{4}-\d{2}', stamp) else 'Unknown'] += 1
        for level in LEVELS:
            code = text(row.get(f'NAICS_2022_{level}'))
            if not code:
                coverage[level]['missing'] += 1
                continue
            if not re.fullmatch(r'\d{' + str(level) + '}', code):
                coverage[level]['invalid_format'] += 1
                continue
            coverage[level]['classified'] += 1
            g = groups[level, code]
            g['postings'] += 1
            if employer:
                g['employers'].add(employer)
            name = text(row.get(f'NAICS_2022_{level}_NAME'))
            if name:
                g['names'][name] += 1
    counts['distinct_posting_ids'] = len(ids)
    counts['repeated_id_rows'] = counts['posting_records'] - counts['missing_ids'] - len(ids)
    counts['distinct_employer_names'] = len(employers)
    result = []
    for (level, code), g in sorted(groups.items()):
        names = g['names']
        result.append({'level': level, 'code': code, 'parent': code[:-1] if level > 4 else '',
                       'name': names.most_common(1)[0][0] if names else 'Title unavailable',
                       'title_variants': len(names), 'postings': g['postings'],
                       'employers': len(g['employers'])})
    return {'counts': dict(counts), 'coverage': {str(n): {k: coverage[n][k] for k in
            ('classified', 'missing', 'invalid_format')} for n in LEVELS}, 'groups': result,
            'months': dict(sorted(months.items()))}


def build(root, out=None):
    manifest, fingerprint = verify_snapshot(root)
    columns = ['ID', 'COMPANY_NAME', 'POSTED'] + [f'NAICS_2022_{n}{s}' for n in LEVELS for s in ('', '_NAME')]
    def rows():
        for part in manifest['parts']:
            pf = pq.ParquetFile(root / part['file'])
            for batch in pf.iter_batches(columns=columns, batch_size=10000):
                yield from batch.to_pylist()
    report = aggregate(rows())
    coverage_bytes = (root / 'column_coverage.csv').read_bytes()
    source_coverage = list(csv.DictReader(coverage_bytes.decode('utf-8-sig').splitlines()))
    if len(source_coverage) != manifest['column_count'] or any(
            int(r['populated']) + int(r['missing']) != manifest['rows'] for r in source_coverage):
        raise ValueError('Source field coverage does not reconcile')
    # Recheck bytes after reading; no export may span two source snapshots.
    _, final_fingerprint = verify_snapshot(root)
    if fingerprint != final_fingerprint or report['counts']['posting_records'] != manifest['rows']:
        raise ValueError('Source changed while aggregating')
    report.update(release_id=manifest['layout_release'], source_manifest_sha256=fingerprint,
                  source_column_coverage_sha256=hashlib.sha256(coverage_bytes).hexdigest(),
                  generated_at_utc=datetime.now(timezone.utc).isoformat(), files=manifest['parts'],
                  source_columns=manifest['column_count'],
                  employer_definition='Distinct non-placeholder COMPANY_NAME after case-folding and whitespace normalization; not verified legal entities.',
                  posting_definition='All source posting records, duplicates retained; not unique vacancies.',
                  classification_definition='Existing NAICS 2022 source labels with expected numeric code length; coverage is not independent industry accuracy validation.')
    out = out or ROOT / 'data/naics'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'snapshot.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (out / 'column_coverage.csv').write_bytes(coverage_bytes)
    sparse = sorted((r for r in source_coverage if float(r['missing_pct']) > 80),
                    key=lambda r: (-float(r['missing_pct']), r['column']))
    field_summary = (f"The release's field-coverage export lists **{len(sparse)} of {len(source_coverage)} columns above 80% missing**. "
                     "The first 15 are shown below; all fields are in the download. These source-export population counts "
                     "do not establish semantic completeness of nested objects or placeholder values.\n\n"
                     "| Field | Missing records | Missing share |\n|---|---:|---:|\n")
    for r in sparse[:15]:
        field_summary += f"| `{r['column']}` | {int(r['missing']):,} | {float(r['missing_pct']):.2f}% |\n"
    (out / 'field-coverage.md').write_text(field_summary, encoding='utf-8')
    with (out / 'industries.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(report['groups'][0]))
        writer.writeheader(); writer.writerows(report['groups'])
    c = report['counts']
    summary = (f"**{c['posting_records']:,} posting records** · **{c['distinct_employer_names']:,} distinct employer names** · "
               f"**{len(manifest['parts'])} verified files**\n\nSnapshot: `{manifest['layout_release']}`. "
               "All records are included; no title, industry, staffing, or model-training filter is applied.\n\n"
               "| NAICS level | Industry groups | Classified posting records | Coverage | Missing codes |\n|---|---:|---:|---:|---:|\n")
    for level, v in report['coverage'].items():
        groups = sum(g['level'] == int(level) for g in report['groups'])
        summary += f"| {level} | {groups:,} | {v['classified']:,} | {100*v['classified']/c['posting_records']:.1f}% | {v['missing']:,} |\n"
    (out / 'summary.md').write_text(summary, encoding='utf-8')
    # Inline data works for both file:// previews and GitHub Pages, without a server.
    payload = json.dumps(report, ensure_ascii=True).replace('<', '\\u003c')
    (out / 'data.js').write_text('window.NAICS_DATA = ' + payload + ';\n', encoding='utf-8')
    print('SNAPSHOT VERIFIED:', report['release_id'], c, report['coverage'])
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=Path('E:/Data/Jobs_2026_US'))
    build(parser.parse_args().source)
