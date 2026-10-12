"""Read the entire pinned US snapshot; export aggregate research feasibility only."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

import pyarrow.parquet as pq
from build_naics import verify_snapshot

OUT = Path(__file__).resolve().parents[1] / 'docs/research'
FIELDS = ['BODY', 'HTML_DESCRIPTION_TEXT', 'SKILLS_NAME', 'COMPANY_NAME',
          'NAICS_2022_4', 'NAICS_2022_5', 'NAICS_2022_6', 'NAICS_FILL_METHOD',
          'DUPLICATE_STATUS', 'IS_DUPLICATE', 'POSTED']
EMPTY = {'', 'unknown', 'unclassified', 'none', 'null', 'nan', '[]', '{}'}


def normalize(value):
    return re.sub(r'\s+', ' ', str(value or '')).strip().casefold()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', required=True, type=Path)
    args = parser.parse_args()
    manifest, fingerprint = verify_snapshot(args.data_dir)
    counts, lengths, months, duplicate_status, fill_methods = (Counter() for _ in range(5))
    body_hashes, employer_body_hashes = set(), set()
    for part in manifest['parts']:
        pf = pq.ParquetFile(args.data_dir / part['file'])
        for batch in pf.iter_batches(columns=FIELDS, batch_size=4000):
            for row in batch.to_pylist():
                counts['rows'] += 1
                body = normalize(row['BODY'])
                html = normalize(row['HTML_DESCRIPTION_TEXT'])
                employer = normalize(row['COMPANY_NAME'])
                skills = normalize(row['SKILLS_NAME'])
                has_body = body not in EMPTY
                has_skills = skills not in EMPTY
                counts['body_populated'] += has_body
                counts['body_at_least_200_characters'] += has_body and len(body) >= 200
                counts['html_text_populated'] += html not in EMPTY
                counts['skills_nonplaceholder'] += has_skills
                counts['body_and_skills'] += has_body and has_skills
                counts['body_without_skills'] += has_body and not has_skills
                if has_body:
                    lengths['under_200' if len(body) < 200 else '200_to_1999' if len(body) < 2000 else '2000_plus'] += 1
                    body_hashes.add(hashlib.sha256(body.encode()).digest())
                    if employer not in EMPTY:
                        counts['body_with_employer'] += 1
                        employer_body_hashes.add(hashlib.sha256((employer + '\0' + body).encode()).digest())
                for level in (4, 5, 6):
                    valid = bool(re.fullmatch(r'\d{' + str(level) + '}', normalize(row[f'NAICS_2022_{level}'])))
                    counts[f'naics{level}_format_valid'] += valid
                    counts[f'body_and_naics{level}'] += has_body and valid
                months[str(row['POSTED'] or '')[:7]] += 1
                duplicate_status[str(row['DUPLICATE_STATUS'])] += 1
                fill_methods[str(row['NAICS_FILL_METHOD'])] += 1
                counts['source_duplicate_flag_true'] += row['IS_DUPLICATE'] is True
        print('Scanned', part['file'], counts['rows'], flush=True)
    _, after = verify_snapshot(args.data_dir)
    assert fingerprint == after and counts['rows'] == manifest['rows']
    counts['unique_normalized_bodies'] = len(body_hashes)
    counts['repeated_normalized_body_rows'] = counts['body_populated'] - len(body_hashes)
    counts['unique_employer_body_pairs'] = len(employer_body_hashes)
    counts['repeated_employer_body_rows'] = counts['body_with_employer'] - len(employer_body_hashes)
    result = dict(release=manifest['layout_release'], manifest_sha256=fingerprint,
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  parts_verified=len(manifest['parts']), counts=dict(counts),
                  body_length_bands=dict(lengths), months=dict(sorted(months.items())),
                  duplicate_status=dict(duplicate_status), naics_fill_methods=dict(fill_methods),
                  interpretation='Feasibility only. Normalized repeated text is not proof of duplicate vacancies. Nonplaceholder skill fields are not validated skill annotations. Numeric NAICS format is not classification accuracy.')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'feasibility.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(counts, indent=2))
    print('FEASIBILITY VERIFIED')


if __name__ == '__main__':
    main()
