"""Execute the website's visible sample chunks; publish aggregate outputs only."""
import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parents[1]

# Each string is both executed and displayed, so outputs cannot drift from code.
CHUNKS = [
    ('preparation', 'Load a reproducible posting sample', '''
from pathlib import Path
from collections import Counter
import hashlib
import json
import pandas as pd
import pyarrow.parquet as pq
from run_study import COLS, KNOWN_SECTORS, ROLE, clean

sample_fraction = 0.10
seed = 2017
files = sorted(data_dir.glob('jobs_2026_part_*.parquet'))
if not files:
    raise ValueError('No Jobs_2026_US posting partitions found')
parts, inputs = [], []
source_rows = 0
def selected(identifier):
    if pd.isna(identifier):
        return False
    key = f'{seed}:{identifier}'.encode('utf-8')
    bucket = int.from_bytes(hashlib.sha256(key).digest()[:8], 'big')
    return not sample or bucket < int(sample_fraction * 2**64)

for path in files:
    parquet = pq.ParquetFile(path)
    inputs.append({'file': path.name, 'rows': parquet.metadata.num_rows})
    for batch in parquet.iter_batches(columns=COLS, batch_size=20000):
        frame = batch.to_pandas()
        source_rows += len(frame)
        parts.append(frame.loc[frame.ID.map(selected)])
jobs = pd.concat(parts, ignore_index=True)
sampled_rows = len(jobs)
jobs = jobs.drop_duplicates('ID', keep='first').copy()
print(f'sample={str(sample).lower()}, fraction={sample_fraction if sample else 1}, seed={seed}')
print(f'Partitions scanned: {len(files):,}; source rows: {source_rows:,}')
print(f'Selected rows: {sampled_rows:,}; unique posting IDs: {len(jobs):,}')
print('Schema preview (first 6 columns):')
print(jobs.dtypes.head(6).to_string())
'''),
    ('preparation', 'Apply the study filters', '''
ledger = {'sample_unique_ids': len(jobs)}
dates = pd.to_datetime(jobs.POSTED, errors='coerce', utc=True, format='mixed')
jobs = jobs.loc[(dates >= '2026-01-01') & (dates < '2026-10-01')].copy()
ledger['January–September 2026'] = len(jobs)
jobs = jobs.loc[jobs.PARSED_COUNTRY_ISO_ABBR.map(clean).str.upper().eq('US')].copy()
ledger['US'] = len(jobs)
jobs['sector'] = jobs.NAICS_2022_2.map(clean)
jobs['sector'] = jobs.sector.where(jobs.sector.ne(''), jobs.NAICS2.map(clean))
jobs = jobs.loc[jobs.sector.isin(KNOWN_SECTORS)].copy()
ledger['recognized sector'] = len(jobs)
jobs = jobs.loc[~jobs.COMPANY_IS_STAFFING.eq(1)].copy()
ledger['nonstaffing or unknown'] = len(jobs)
titles = jobs.TITLE_RAW.map(clean)
titles = titles.where(titles.ne(''), jobs.TITLE_CLEAN.map(clean))
career = jobs.loc[jobs.sector.eq('62') & titles.map(lambda title: bool(ROLE.search(title)))].copy()
ledger['healthcare analyst cohort'] = len(career)
print(pd.Series(ledger, name='Postings').to_string())
'''),
    ('market', 'Inspect coverage and work arrangements', '''
from run_study import STATE_MAP
import numpy as np

states = career.STATE_NAME.map(lambda value: STATE_MAP.get(clean(value).upper(), 'Unknown'))
remote = career.REMOTE_TYPE_NAME.map(lambda value: {
    'remote': 'Remote', 'hybrid': 'Hybrid', 'onsite': 'Onsite', 'on-site': 'Onsite'
}.get(clean(value).lower(), 'Unknown'))
salary = pd.to_numeric(career.NORMALIZED_SALARY, errors='coerce')
salary = salary.where(career.TEXT_PAY_CURRENCY.eq('USD') & salary.gt(0) & np.isfinite(salary))
experience = pd.to_numeric(career.MIN_YEARS_EXPERIENCE, errors='coerce')
coverage = pd.Series({'cohort postings': len(career), 'recognized state': states.ne('Unknown').sum(),
    'known work arrangement': remote.ne('Unknown').sum(), 'positive USD salary': salary.notna().sum(),
    'nonnegative experience': experience.ge(0).sum()}, name='Postings')
print(coverage.to_string())
print('Work arrangement counts:')
print(remote.value_counts().to_string())
print('State counts (first 5):')
print(states.value_counts().head(5).to_string())
'''),
    ('skills', 'Decode skills and calculate posting shares', '''
skills = Counter()
malformed = 0
for value in career.SKILLS_NAME:
    try:
        items = json.loads(clean(value) or '[]')
        if not isinstance(items, list):
            raise ValueError('Expected a skill list')
        skills.update({str(item).strip() for item in items if str(item).strip()})
    except (ValueError, TypeError):
        malformed += 1
skills_table = pd.DataFrame([
    {'skill': skill, 'postings': count, 'share': round(count / len(career), 4)}
    for skill, count in sorted(skills.items(), key=lambda item: (-item[1], item[0]))
], columns=['skill', 'postings', 'share'])
print(f'Denominator: {len(career)} cohort postings; malformed skill lists: {malformed}')
print(skills_table.head(10).to_string(index=False))
'''),
    ('evaluation', 'Check sample support before model fitting', '''
# Apply the existing employer eligibility rules to the sampled postings.
import re
employers = {}
for row in jobs.to_dict('records'):
    name = re.sub(r'\\s+', ' ', clean(row['COMPANY_NAME']).casefold())
    title = clean(row['TITLE_NAME']).casefold()
    if not name or name in ('unknown', 'unclassified') or not title or title == 'unclassified':
        continue
    employers.setdefault(name, Counter()).update([row['sector']])
eligible = [counts for counts in employers.values()
            if counts.total() >= 20 and counts.most_common(1)[0][1] / counts.total() >= .8]
support = Counter(int(counts.most_common(1)[0][0] == '62') for counts in eligible)
print(f'Eligible employers in this sample: {len(eligible)}')
print(f'Healthcare: {support[1]}; other sectors: {support[0]}')
print(f'Minimum split support met: {len(eligible) >= 50 and min(support[0], support[1]) >= 10}')
print('No classifier is fitted in this sample walkthrough.')
print('The model metrics below belong to the separate full-study run.')
'''),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--sample', choices=['true', 'false'], default='true')
    args = parser.parse_args()
    namespace = {'data_dir': args.data_dir, 'sample': args.sample == 'true'}
    pages = {}
    records = []
    for page, title, source in CHUNKS:
        code = textwrap.dedent(source).strip()
        capture = io.StringIO()
        with contextlib.redirect_stdout(capture):
            exec(compile(code, f'<sample:{title}>', 'exec'), namespace)
        output = capture.getvalue().rstrip()
        records.append({'page': page, 'title': title, 'code': code, 'output': output})
        pages.setdefault(page, []).append(f'### {title}\n\n```python\n{code}\n```\n\nPartial output (computed from this run):\n\n```text\n{output}\n```\n')
    for page, sections in pages.items():
        intro = ('## Executed sample: code and partial output\n\n'
                 f'This walkthrough uses `sample={args.sample}` on the local Jobs_2026_US partitions. '
                 'With sampling enabled, SHA-256 of seed 2017 and posting ID selects approximately 10% of IDs across all partitions; '
                 'missing IDs are excluded and duplicates keep their first occurrence. This scans every partition but retains only selected rows. '
                 'These descriptive sample results are separate from the full-study tables below. '
                 'Code is shown expanded; outputs are captured from that exact code by '
                 '`scripts/publish_sample.py`. Only aggregates and a schema preview are published. '
                 'Run chunks in page order: preparation, market, skills, evaluation.\n\n')
        if page == 'preparation':
            intro += (f'Run from the repository root: `python scripts/publish_sample.py --data-dir E:/Data/Jobs_2026_US --sample={args.sample}`, then `quarto render`. '
                      'For interactive execution, add `scripts` to `sys.path`, set `data_dir = Path("E:/Data/Jobs_2026_US")` '
                      f'and `sample = {namespace["sample"]}` before the first chunk.\n\n')
        (ROOT / '_content' / f'sample-{page}.md').write_text(intro + '\n'.join(sections), encoding='utf-8')
    result = {'source_directory': args.data_dir.resolve().as_posix(), 'sample': namespace['sample'], 'fraction': .1 if namespace['sample'] else 1,
              'seed': 2017, 'source_rows': namespace['source_rows'], 'sampled_rows': namespace['sampled_rows'],
              'inputs': namespace['inputs'], 'ledger': namespace['ledger'], 'chunks': records,
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    out = ROOT / 'data' / 'sample'
    out.mkdir(exist_ok=True)
    (out / 'run.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(f'SAMPLE PUBLISHED: {result["sampled_rows"]:,} sampled rows; {len(namespace["career"])} career postings')


if __name__ == '__main__':
    main()
