## Executed sample: code and partial output

This walkthrough uses `sample=true` on the local Jobs_2026_US partitions. With sampling enabled, SHA-256 of seed 2017 and posting ID selects approximately 10% of IDs across all partitions; missing IDs are excluded and duplicates keep their first occurrence. This scans every partition but retains only selected rows. These descriptive sample results are separate from the full-study tables below. Code is shown expanded; outputs are captured from that exact code by `scripts/publish_sample.py`. Only aggregates and a schema preview are published. Run chunks in page order: preparation, market, skills, evaluation.

Run from the repository root: `python scripts/publish_sample.py --data-dir E:/Data/Jobs_2026_US --sample=true`, then `quarto render`. For interactive execution, add `scripts` to `sys.path`, set `data_dir = Path("E:/Data/Jobs_2026_US")` and `sample = True` before the first chunk.

### Load a reproducible posting sample

```python
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
```

Partial output (computed from this run):

```text
sample=true, fraction=0.1, seed=2017
Partitions scanned: 82; source rows: 815,193
Selected rows: 81,163; unique posting IDs: 81,163
Schema preview (first 6 columns):
ID                       int64
POSTED                  object
COMPANY_NAME            object
COMPANY_IS_STAFFING    float64
TITLE_NAME              object
TITLE_RAW               object
```

### Apply the study filters

```python
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
```

Partial output (computed from this run):

```text
sample_unique_ids            81163
January–September 2026       79719
US                           79719
recognized sector            35625
nonstaffing or unknown       35099
healthcare analyst cohort        7
```
