"""Profile local Jobs_2026 posting partitions; export only aggregate evidence."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from run_study import COLS, KNOWN_SECTORS, STATE_MAP, bar_chart

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data' / 'eda'
MISSING = '(missing)'


def strings(series):
    return series.astype('string').fillna('').str.strip()


def table(headers, rows):
    def cell(value):
        return str(value).replace('|', '\\|').replace('\n', ' ')
    return '\n'.join(['| ' + ' | '.join(headers) + ' |',
                      '|' + '|'.join(['---'] * len(headers)) + '|'] +
                     ['| ' + ' | '.join(cell(v) for v in row) + ' |' for row in rows])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=Path('E:/Data/Jobs_2026'))
    args = parser.parse_args()
    files = sorted(args.data_dir.glob('jobs_2026_part_*.parquet'))
    if not files:
        parser.error('No jobs_2026_part_*.parquet files found')
    counts = Counter()
    missing = Counter()
    distributions = {k: Counter() for k in ['posted_year', 'posted_month', 'country',
                                           'sector', 'state', 'remote', 'staffing']}
    manifest, salaries = [], []
    seen = set()
    date_min = date_max = None
    for file in files:
        parquet = pq.ParquetFile(file)
        absent = set(COLS) - set(parquet.schema_arrow.names)
        if absent:
            raise ValueError(f'{file.name}: missing required columns {sorted(absent)}')
        with file.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        manifest.append({'file': file.name, 'rows': parquet.metadata.num_rows,
                         'bytes': file.stat().st_size, 'sha256': digest,
                         'schema': {f.name: str(f.type) for f in parquet.schema_arrow}})
        for batch in parquet.iter_batches(columns=COLS, batch_size=20000):
            frame = batch.to_pandas()
            counts['source_rows'] += len(frame)
            text = {col: strings(frame[col]) for col in COLS}
            missing.update({col: int(text[col].eq('').sum()) for col in COLS})
            ids = frame['ID'].dropna()
            counts['missing_id'] += int(frame['ID'].isna().sum())
            before = len(seen)
            seen.update(ids.tolist())
            counts['duplicate_id'] += len(ids) - (len(seen) - before)
            dates = pd.to_datetime(frame['POSTED'], errors='coerce', utc=True, format='mixed')
            counts['invalid_or_missing_date'] += int(dates.isna().sum())
            if dates.notna().any():
                lo, hi = dates.min(), dates.max()
                date_min = lo if date_min is None else min(lo, date_min)
                date_max = hi if date_max is None else max(hi, date_max)
            counts['january_september_2026_rows'] += int(
                ((dates >= '2026-01-01') & (dates < '2026-10-01')).sum())
            sector = text['NAICS_2022_2'].where(text['NAICS_2022_2'].ne(''), text['NAICS2'])
            counts['invalid_nonempty_sector'] += int((sector.ne('') & ~sector.isin(KNOWN_SECTORS)).sum())
            state = text['STATE_NAME'].str.upper().map(STATE_MAP).fillna('(missing or unrecognized)')
            remote = text['REMOTE_TYPE_NAME'].str.casefold().replace({'on-site': 'onsite'})
            values = {'posted_year': dates.dt.strftime('%Y').fillna(MISSING),
                      'posted_month': dates.dt.strftime('%Y-%m').fillna(MISSING),
                      'country': text['PARSED_COUNTRY_ISO_ABBR'].str.upper(),
                      'sector': sector, 'state': state, 'remote': remote,
                      'staffing': text['COMPANY_IS_STAFFING']}
            for key, series in values.items():
                distributions[key].update(series.replace('', MISSING).value_counts().to_dict())
            salary = pd.to_numeric(frame['NORMALIZED_SALARY'], errors='coerce')
            usable = (np.isfinite(salary) & salary.gt(0) & text['TEXT_PAY_CURRENCY'].eq('USD'))
            salaries.extend(salary[usable].tolist())
        print(f'Profiled {file.name}', flush=True)
    counts['unique_nonmissing_ids'] = len(seen)
    counts['usable_annual_usd_salary_rows'] = len(salaries)
    quantiles = ({str(q): float(np.quantile(salaries, q)) for q in [0, .25, .5, .75, 1]}
                 if salaries else {})
    study = json.loads((ROOT / 'data/study/run.json').read_text(encoding='utf-8'))
    fingerprints = lambda rows: {(r['file'], r['rows'], r['sha256']) for r in rows}
    matches = fingerprints(manifest) == fingerprints(study['files'])
    result = {'generated_at_utc': datetime.now(timezone.utc).isoformat(),
              'source_directory': str(args.data_dir.resolve()),
              'file_pattern': 'jobs_2026_part_*.parquet',
              'unit': 'raw posting rows before study exclusions; duplicates retained',
              'counts': dict(counts), 'date_min': str(date_min), 'date_max': str(date_max),
              'missingness_definition': 'null or whitespace-only; encoded empty lists and unknown labels are not null',
              'profiled_columns': COLS, 'missing': dict(missing),
              'distributions': distributions, 'annual_usd_salary_quantiles': quantiles,
              'study_manifest_matches': matches, 'files': manifest}
    OUT.mkdir(parents=True, exist_ok=True)
    (ROOT / 'images').mkdir(exist_ok=True)
    (OUT / 'run.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    n = counts['source_rows']
    coverage = pd.DataFrame([{'column': c, 'missing_rows': missing[c],
                             'present_rows': n - missing[c], 'missing_share': missing[c] / n}
                            for c in COLS]).sort_values('missing_rows', ascending=False)
    coverage.to_csv(OUT / 'missingness.csv', index=False)
    for key, values in distributions.items():
        pd.DataFrame([{'value': v, 'rows': count, 'share_source_rows': count / n}
                      for v, count in values.most_common()]).to_csv(OUT / f'{key}.csv', index=False)
    bar_chart(coverage['column'].tolist(), (coverage['missing_share'] * 100).tolist(),
              'Missingness in fields used by the study', '% of all source rows', 'eda_missingness.png')
    years = sorted(distributions['posted_year'].items())
    bar_chart([v for v, _ in years], [c for _, c in years],
              'Posting dates in Jobs_2026', 'Source rows (before exclusions)', 'eda_years.png')
    sections = [f'''## Local Jobs_2026 exploratory analysis

The analysis and EDA use `E:\\Data\\Jobs_2026` [@jobs2026]. This scan contains **{n:,} rows across {len(files)} posting partitions**. Only `jobs_2026_part_*.parquet` files are inputs; supporting exports and backups are excluded. The source is read locally; the repository contains aggregates and file hashes.

EDA describes raw rows before the healthcare study's filters. Duplicate IDs are counted but retained in these distributions. Posting-ID uniqueness does not rule out repeated advertisements with different IDs. Populated industry and skills fields are not independently verified labels.

{table(['Measure', 'Observed value'], [('Nonmissing unique IDs', f"{len(seen):,}"), ('Repeated-ID rows beyond first occurrence', f"{counts['duplicate_id']:,}"), ('Missing IDs', f"{counts['missing_id']:,}"), ('Earliest parsed posting date (UTC)', str(date_min)), ('Latest parsed posting date (UTC)', str(date_max)), ('Missing or unparseable dates', f"{counts['invalid_or_missing_date']:,}"), ('Dated January–September 2026, before other filters', f"{counts['january_september_2026_rows']:,}")])}

![Posting-year distribution across all source rows.](images/eda_years.png)

### Field coverage

Missingness covers the {len(COLS)} fields consumed by the study. Missing means null or whitespace-only; strings such as `[]`, `Unknown` or `Unclassified` still count as populated. Full input schemas are recorded in the EDA manifest.

![Missingness across study fields, denominator all source rows.](images/eda_missingness.png)

{table(['Field', 'Missing rows', 'Missing share'], [(r.column, f'{r.missing_rows:,}', f'{r.missing_share:.1%}') for r in coverage.itertuples()])}

### Industry, geography and work arrangement

The following tables show the ten most frequent categories, including missing where it ranks in the top ten. Every share uses all {n:,} source rows. Full distributions are saved as CSVs. Sector uses `NAICS_2022_2`, falling back to `NAICS2` only when blank; {counts['invalid_nonempty_sector']:,} nonempty values are outside the study's accepted sector vocabulary. States normalize US abbreviations and full names; other state values share an explicit unrecognized category. Remote labels are lowercased and `On-site` is merged with `Onsite`.
''']
    for key, label in [('sector', 'Sector codes'), ('country', 'Parsed country'),
                       ('state', 'US states'), ('remote', 'Work arrangement')]:
        sections.append(f"#### {label}\n\n" + table(['Category', 'Rows', 'Share of source'],
                         [(v, f'{c:,}', f'{c/n:.1%}') for v, c in distributions[key].most_common(10)]))
    sections.append(f'''### Salary coverage and study boundary

There are **{len(salaries):,} rows ({len(salaries)/n:.1%})** with a finite positive normalized salary, explicitly USD currency, consistent with the healthcare study salary filter. These are annual-equivalent advertised amounts; they may include compensation beyond base pay. They are not observed earnings or a representative wage survey. Raw amounts with mixed or unknown pay periods are not pooled.

{table(['Annual-equivalent USD measure', 'Amount'], [(label, f"{quantiles[str(q)]:,.2f}") for q, label in [(0, 'Minimum'), (.25, '25th percentile'), (.5, 'Median'), (.75, '75th percentile'), (1, 'Maximum')]]) if salaries else 'No rows satisfy the salary definition.'}

{'All input filenames, row counts and SHA-256 hashes match the saved healthcare study.' if matches else '**The EDA inputs differ from the saved healthcare study. Re-run the study before interpreting them as the same snapshot.**'} The healthcare analysis further restricts dates, country, sector, staffing status and usable employer/title fields. Its employer model and analyst career sample have different units and denominators; the filtering ledger is in [the 2026 study](career_evaluation.qmd).

Reproduce with `python scripts/run_eda.py --data-dir E:/Data/Jobs_2026`. [EDA manifest](data/eda/run.json), [field missingness](data/eda/missingness.csv), [posting months](data/eda/posted_month.csv), [sector distribution](data/eda/sector.csv), [country distribution](data/eda/country.csv), [state distribution](data/eda/state.csv) and [work arrangements](data/eda/remote.csv) provide the aggregate evidence.
''')
    (ROOT / '_content/source-eda-results.md').write_text('\n\n'.join(sections) + '\n', encoding='utf-8')
    print(f'EDA COMPLETE: {n:,} rows; {len(files)} partitions; study manifest matches={matches}')


if __name__ == '__main__':
    main()

