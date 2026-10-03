## Executed sample: code and partial output

This walkthrough uses `sample=true` on the local Jobs_2026_US partitions. With sampling enabled, SHA-256 of seed 2017 and posting ID selects approximately 10% of IDs across all partitions; missing IDs are excluded and duplicates keep their first occurrence. This scans every partition but retains only selected rows. These descriptive sample results are separate from the full-study tables below. Code is shown expanded; outputs are captured from that exact code by `scripts/publish_sample.py`. Only aggregates and a schema preview are published. Run chunks in page order: preparation, market, skills, evaluation.

### Decode skills and calculate posting shares

```python
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
```

Partial output (computed from this run):

```text
Denominator: 7 cohort postings; malformed skill lists: 0
                              skill  postings  share
                   Microsoft Office         3 0.4286
                      Data Analysis         2 0.2857
                    Data Collection         2 0.2857
                Quality Improvement         2 0.2857
         SQL (Programming Language)         2 0.2857
        Verbal Communication Skills         2 0.2857
Artificial Intelligence Development         1 0.1429
                 Business Analytics         1 0.1429
         C++ (Programming Language)         1 0.1429
                  Care Coordination         1 0.1429
```
