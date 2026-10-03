"""Independently reconcile saved aggregate counts and model metrics."""
import csv
import json
from pathlib import Path
import math
ROOT=Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'data/study/run.json').read_text())
l=d['ledger']
assert sum(f['rows'] for f in d['files'])==l['source_rows']
assert len({f['file'] for f in d['files']})==len(d['files'])
assert all(len(f['sha256'])==64 for f in d['files'])
assert l['source_rows']==l['unique_id_rows']+l.get('duplicate_id',0)+l.get('missing_id',0)
for total,kept,excluded in [('unique_id_rows','period_rows','outside_period_or_unknown_date'),('period_rows','us_rows','non_us_or_unknown_country'),('us_rows','sector_known_rows','missing_or_invalid_sector'),('sector_known_rows','nonstaffing_or_unknown_rows','staffing_excluded'),('nonstaffing_or_unknown_rows','employer_model_postings','missing_employer_or_title')]:
    assert l[total]==l[kept]+l[excluded],total
assert l['employers_before_filters']==l['employers_below_20']+l['employers_without_dominant_sector']+l['eligible_employers_before_cap']
assert sum(s['employers'] for s in d['splits'].values())==l['model_employers']
assert d['employer_overlap']==0
for m in d['models']:
    (tn,fp),(fn,tp)=m['confusion_matrix']
    assert tn+fp==d['splits']['test']['negative']
    assert fn+tp==d['splits']['test']['positive']
    expected={'precision':tp/(tp+fp) if tp+fp else 0,'recall':tp/(tp+fn) if tp+fn else 0,'f1-score':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0}
    for metric,value in expected.items(): assert math.isclose(value,m['test_report']['1'][metric])
for values in d['career']['counts'].values(): assert sum(values.values())==d['career']['postings']
with (ROOT/'data/study/market_skills.csv').open(newline='',encoding='utf-8') as f:
    for row in csv.DictReader(f): assert math.isclose(int(row['postings'])/d['career']['postings'],float(row['share_all_scope_postings']))
print('STUDY VERIFIED: filter ledger reconciles; metrics match confusion counts; benchmark denominators reconcile')
