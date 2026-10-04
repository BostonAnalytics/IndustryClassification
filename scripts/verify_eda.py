"""Reconcile published EDA with the saved study and inspect its integration."""
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'data/study'
d = json.loads((OUT/'run.json').read_text())
c = d['career']; n = c['postings']
def rows(name):
    with (OUT/name).open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))

manifest = json.loads((OUT/'eda_manifest.json').read_text())
for name, digest in manifest['inputs'].items():
    assert hashlib.sha256((OUT/name).read_bytes()).hexdigest() == digest, 'Stale EDA source'
for row, key in zip(rows('eda_selection.csv'), ['source_rows','period_rows','us_rows','sector_known_rows','nonstaffing_or_unknown_rows'], strict=True):
    assert int(row['postings']) == d['ledger'][key]
    assert math.isclose(float(row['share_source']), int(row['postings'])/d['ledger']['source_rows'])
expected = [c['skills_observed'],n-c['counts']['states'].get('Unknown or non-state',0),c['experience_observed'],n-c['counts']['remote'].get('Unknown',0),c['salary_usd_observed']]
for row, count in zip(rows('eda_coverage.csv'), expected, strict=True):
    assert int(row['observed']) == count
    assert int(row['observed'])+int(row['unavailable']) == int(row['denominator']) == n
    assert math.isclose(float(row['share_observed']), count/n)
for row in rows('eda_roles.csv'):
    assert c['counts']['roles'][row['role']] == int(row['postings'])
    assert math.isclose(float(row['share_all_postings']), int(row['postings'])/n)
original = {r['skill']:int(r['postings']) for r in rows('market_skills.csv')}
for row in rows('eda_skills.csv'):
    assert original[row['skill']] == int(row['postings'])
    assert math.isclose(float(row['share_all_postings']), int(row['postings'])/n)
    assert math.isclose(float(row['share_with_skills']), int(row['postings'])/c['skills_observed'])
for name in manifest['figures']:
    assert (ROOT/'images'/name).read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    assert name in (ROOT/'_content/eda-results.md').read_text(encoding='utf-8')
for name in ['market_baseline.qmd','final_report.qmd']:
    assert 'include _content/eda-results.md' in (ROOT/name).read_text()
expected_pages = {'index','introduction','data_preparation','market_baseline','skill_gap_analysis','career_evaluation','pyspark_analysis','interactive','analysis_code','final_recommendations','references','ai-disclosure','final_report'}
assert {p.stem for p in ROOT.glob('*.qmd')} == expected_pages
print('EDA VERIFIED: source hashes, counts, denominators, four PNGs and thirteen QMD sources including PySpark analysis and interactive exports')
