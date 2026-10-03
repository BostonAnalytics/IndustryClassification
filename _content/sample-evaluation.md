## Executed sample: code and partial output

This walkthrough uses `sample=true` on the local Jobs_2026_US partitions. With sampling enabled, SHA-256 of seed 2017 and posting ID selects approximately 10% of IDs across all partitions; missing IDs are excluded and duplicates keep their first occurrence. This scans every partition but retains only selected rows. These descriptive sample results are separate from the full-study tables below. Code is shown expanded; outputs are captured from that exact code by `scripts/publish_sample.py`. Only aggregates and a schema preview are published. Run chunks in page order: preparation, market, skills, evaluation.

### Check sample support before model fitting

```python
# Apply the existing employer eligibility rules to the sampled postings.
import re
employers = {}
for row in jobs.to_dict('records'):
    name = re.sub(r'\s+', ' ', clean(row['COMPANY_NAME']).casefold())
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
```

Partial output (computed from this run):

```text
Eligible employers in this sample: 54
Healthcare: 29; other sectors: 25
Minimum split support met: True
No classifier is fitted in this sample walkthrough.
The model metrics below belong to the separate full-study run.
```
