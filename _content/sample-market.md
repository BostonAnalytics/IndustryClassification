## Executed sample: code and partial output

This walkthrough uses `sample=true` on the local Jobs_2026_US partitions. With sampling enabled, SHA-256 of seed 2017 and posting ID selects approximately 10% of IDs across all partitions; missing IDs are excluded and duplicates keep their first occurrence. This scans every partition but retains only selected rows. These descriptive sample results are separate from the full-study tables below. Code is shown expanded; outputs are captured from that exact code by `scripts/publish_sample.py`. Only aggregates and a schema preview are published. Run chunks in page order: preparation, market, skills, evaluation.

### Inspect coverage and work arrangements

```python
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
```

Partial output (computed from this run):

```text
cohort postings           7
recognized state          5
known work arrangement    2
positive USD salary       0
nonnegative experience    6
Work arrangement counts:
REMOTE_TYPE_NAME
Unknown    5
Remote     1
Hybrid     1
State counts (first 5):
STATE_NAME
Unknown           2
North Carolina    1
Florida           1
Ohio              1
Texas             1
```
