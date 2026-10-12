"""Reprocess both complete snapshots and publish only aggregate evidence."""
from datetime import datetime, timezone
import argparse
import csv
import json
from pathlib import Path
from build_naics import ROOT, build, sha


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reuse-verified-exports', action='store_true')
    args = parser.parse_args()
    if args.reuse_verified_exports:
        global_data = json.loads((ROOT/'data/global/snapshot.json').read_bytes())
        us = json.loads((ROOT/'data/naics/snapshot.json').read_bytes())
        for name, data in [('Jobs_2026', global_data), ('Jobs_2026_US', us)]:
            if sha(Path('E:/Data')/name/'manifest.json') != data['source_manifest_sha256']:
                raise ValueError('Published snapshot changed; reprocess it')
    else:
        global_data = build(Path('E:/Data/Jobs_2026'), ROOT/'data/global')
        us = build(Path('E:/Data/Jobs_2026_US'))
    preview_path = ROOT/'docs/maintenance/sec-full-disk-preview.json'
    preview = json.loads(preview_path.read_bytes())
    corpus = Path('D:/Repositories/met-employability-services/artifacts/sec-full-integration-20261011/summary.json')
    bundle = Path('D:/Repositories/met-employability-services/artifacts/sec-integration/full-bundle-v1.json')
    audit = json.loads(corpus.read_bytes())
    if sha(bundle) != preview['bundle_sha256'] or audit['headers_audited'] != audit['files']:
        raise ValueError('SEC source evidence changed or audit incomplete')
    stores = {'Jobs_2026': global_data, 'Jobs_2026_US': us}
    for name, data in stores.items():
        if (preview['stores'][name]['manifest_sha256'] != data['source_manifest_sha256']
                or preview['stores'][name]['rows'] != data['counts']['posting_records']):
            raise ValueError('Recompute SEC preview against this release first')
    now = datetime.now(timezone.utc).isoformat()
    lines = [f'Aggregate refresh: **{now[:10]} UTC**. Full published snapshots; all 20 files per dataset.', '',
             '| Dataset | Posting records | Distinct employer names | Source columns |',
             '|---|---:|---:|---:|']
    for name, data in stores.items():
        c = data['counts']
        lines.append(f"| {'Global' if name == 'Jobs_2026' else 'US 2026'} | **{c['posting_records']:,}** | **{c['distinct_employer_names']:,}** | {data['source_columns']} |")
    lines += ['', 'The US dataset overlaps the global dataset: **do not add their totals**. Employer counts are normalized names, not verified legal entities. Posting records retain duplicate advertisements and do not measure currently live vacancies.', '',
              '## Industry groups are not job counts', '',
              'A result around 200 can describe the number of industry categories. Each category can contain thousands of posting records. The explorer shows both measures separately.', '',
              '### US classification coverage', '', '{{< include ../naics/summary.md >}}', '',
              '## SEC evidence: source coverage and candidate matches', '',
              f"The full header audit inspected **{audit['files']:,} filings**, extracting **{audit['counts']['issuer_header_extracted']:,} usable filing observations** for **{audit['unique_unambiguous_ciks']:,} CIKs**. These describe historical filing entities, not the number of employers in the jobs dataset.", '',
              '| Dataset | Job records with a candidate issuer | Share of records | Ambiguous job records |', '|---|---:|---:|---:|']
    for name, data in stores.items():
        c = preview['stores'][name]
        lines.append(f"| {'Global' if name == 'Jobs_2026' else 'US 2026'} | {c['candidate_job_records']:,} | {100*c['candidate_job_records']/c['rows']:.2f}% | {c['ambiguous_job_records']:,} |")
    lines += ['', '**Candidate matches are not verified employer links.** They use exact normalized filed names and filings dated no later than the posting. No confirmed employer CIK or job classification is inferred from a name match. These preview results have not been written into the published job snapshots.', '',
              'The SEC reference import is complete locally. Azure migration and production job enrichment remain pending; this site reports published data and the separate matching preview.', '',
              '## Posting dates in the US snapshot', '', '| Posting month | Records |', '|---|---:|']
    lines += [f'| {month} | {count:,} |' for month, count in us['months'].items()]
    future_month_rows = sum(count for month, count in us['months'].items() if month != 'Unknown' and month > now[:7])
    if future_month_rows:
        lines += ['', f'**Date-quality flag:** {future_month_rows:,} records have posting months later than this refresh month. They remain in the source totals and should be reviewed.']
    lines += ['', 'Posting dates describe source records, not confirmed hiring activity or job liveness.', '',
              '[Download coverage evidence](data/overview/coverage.json) · [Global snapshot evidence](data/global/snapshot.json) · [US industry explorer](naics_explorer.qmd)', '']
    fields = {r['column']: r for r in csv.DictReader((ROOT/'data/naics/column_coverage.csv').read_text(encoding='utf-8-sig').splitlines())}
    useful = [('CITY_NAME', 'City name'), ('MSA_NAME', 'Metro area'), ('SOC_5', 'Detailed occupation code'),
              ('SALARY_FROM', 'Salary lower bound'), ('SALARY_TO', 'Salary upper bound'),
              ('RAW_HTML', 'Archived posting HTML'), ('COMPANY_URL', 'Employer website'),
              ('COMPANY_DESCRIPTION', 'Employer description'), ('COMPANY_CAREERS_URL', 'Employer careers page'),
              ('ALIVE_CHECKED_AT', 'Recorded liveness-check time')]
    readiness = []
    lines += ['## Useful field coverage in US records', '', '| Field | Populated records | Share of US records |', '|---|---:|---:|']
    for name, label in useful:
        count = int(fields[name]['populated']) if name in fields else 0
        readiness.append({'column': name, 'label': label, 'populated': count, 'in_schema': name in fields})
        lines.append(f"| {label} | {count:,} | {100*count/us['counts']['posting_records']:.2f}% |")
    lines += ['', 'Populated means a value is present in the source coverage export; it does not prove accuracy. A recorded liveness check is not evidence that the job is open today. Missing employer and location detail remains visible rather than being inferred.', '']
    out = ROOT/'data/overview'; out.mkdir(parents=True, exist_ok=True)
    # Quarto resolves included paths from the project document, not this include.
    content = '\n'.join(lines).replace('{{< include ../naics/summary.md >}}', (ROOT/'data/naics/summary.md').read_text(encoding='utf8'))
    (out/'summary.md').write_text(content, encoding='utf8')
    report = {'generated_at_utc': now, 'datasets': {name: {k: d[k] for k in ('counts', 'coverage', 'release_id', 'source_manifest_sha256')} for name, d in stores.items()},
              'sec': {'audit': {k: v for k, v in audit.items() if k != 'root'}, 'preview': preview, 'audit_sha256': sha(corpus)},
              'useful_fields': readiness, 'future_posting_month_records': future_month_rows,
              'production_sec_backfill': 'pending', 'verified_employer_links': 0}
    (out/'coverage.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf8')
    print('OVERVIEW VERIFIED: both full snapshots and pinned SEC preview')


if __name__ == '__main__':
    main()
