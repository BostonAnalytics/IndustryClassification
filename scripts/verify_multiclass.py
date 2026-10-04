"""Verify saved multiclass evidence using only the standard library."""
import csv
import argparse
import hashlib
import json
import math
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def verify(d):
    binary = json.loads((ROOT / 'data/study/run.json').read_text(encoding='utf-8'))
    comparison = d['comparison_with_saved_binary']
    assert comparison['binary_manifest_sha256'] == hashlib.sha256((ROOT / 'data/study/run.json').read_bytes()).hexdigest()
    assert comparison['exact_snapshot_match'] == (d['files'] == binary['files'])
    assert comparison['same_file_names_and_rows'] == ([(f['file'], f['rows']) for f in d['files']] == [(f['file'], f['rows']) for f in binary['files']])
    old_files = {f['file']: f for f in binary['files']}
    assert comparison['changed_partition_hashes'] == sum(f['sha256'] != old_files.get(f['file'], {}).get('sha256') for f in d['files'])
    assert d['script_sha256'] == hashlib.sha256((ROOT / 'scripts/run_multiclass.py').read_bytes()).hexdigest()
    assert d['feature_helper_sha256'] == hashlib.sha256((ROOT / 'scripts/run_study.py').read_bytes()).hexdigest()
    ledger = d['ledger']
    assert sum(f['rows'] for f in d['files']) == ledger['source_rows']
    assert ledger['source_rows'] == ledger['unique_id_rows'] + ledger.get('missing_id', 0)
    for total, kept, excluded in [('unique_id_rows', 'period_rows', 'outside_period_or_unknown_date'),
                                  ('period_rows', 'us_rows', 'non_us_or_unknown_country'),
                                  ('us_rows', 'sector_known_rows', 'missing_or_invalid_sector'),
                                  ('sector_known_rows', 'nonstaffing_or_unknown_rows', 'staffing_excluded'),
                                  ('nonstaffing_or_unknown_rows', 'employer_model_postings', 'missing_employer_or_title')]:
        assert ledger[total] == ledger[kept] + ledger.get(excluded, 0)
    assert ledger['employers_before_filters'] == ledger.get('employers_below_20', 0) + ledger.get('employers_without_dominant_sector', 0) + ledger['eligible_employers']
    assert ledger['eligible_employers'] == ledger['model_employers'] + ledger['excluded_low_support_employers']
    assert d['employer_overlap'] == 0
    assert len(d['classes']) >= 3
    included = {r['sector']: r for r in d['class_support'] if r['included']}
    assert sorted(included) == d['classes']
    assert sum(r['eligible_employers'] for r in d['class_support']) == ledger['eligible_employers']
    for row in d['class_support']:
        assert row['included'] == (row['eligible_employers'] >= d['minimum_class_employers'])
        if row['included']:
            assert row['train'] == int(.7 * row['eligible_employers'])
            assert row['validation'] == int(.8 * row['eligible_employers']) - row['train']
            assert row['test'] == row['eligible_employers'] - row['train'] - row['validation']
            assert min(row[s] for s in ('train', 'validation', 'test')) >= 2
        else:
            assert row['train'] + row['validation'] + row['test'] == 0
    for split, count in d['splits'].items():
        assert count == sum(r[split] for r in included.values())
    assert sum(d['splits'].values()) == ledger['model_employers']
    for model in d['models']:
        cm, report = model['confusion_matrix'], model['test_report']
        k = len(d['classes'])
        assert len(cm) == k and all(len(row) == k for row in cm)
        assert all(isinstance(n, int) and n >= 0 for row in cm for n in row)
        n = sum(map(sum, cm))
        assert n == d['splits']['test']
        values = []
        for i, label in enumerate(d['classes']):
            tp, actual, predicted = cm[i][i], sum(cm[i]), sum(row[i] for row in cm)
            assert actual == included[label]['test']
            expected = {'precision': tp / predicted if predicted else 0,
                        'recall': tp / actual, 'f1-score': 2 * tp / (actual + predicted), 'support': actual}
            for key, value in expected.items():
                assert math.isclose(report[label][key], value, abs_tol=1e-12), (model['model'], label, key)
            values.append(expected)
        for key in ('precision', 'recall', 'f1-score'):
            assert math.isclose(report['macro avg'][key], sum(v[key] for v in values) / k, abs_tol=1e-12)
            assert math.isclose(report['weighted avg'][key], sum(v[key] * v['support'] for v in values) / n, abs_tol=1e-12)
        assert math.isclose(model['accuracy'], sum(cm[i][i] for i in range(k)) / n)
        if 'trials' in model:
            trial = max(model['trials'], key=lambda t: t['validation_macro_f1'])
            assert model['selected_params'] == trial['params']
            assert model['validation_macro_f1'] == trial['validation_macro_f1']
    assert d['selected_model'] == max(d['models'][:-1], key=lambda m: m['validation_macro_f1'])['model']
    baseline = d['models'][-1]
    assert baseline['model'] == 'Training majority'
    majority = sorted(included, key=lambda c: (-included[c]['train'], c))[0]
    assert baseline['majority_sector'] == majority
    j = d['classes'].index(majority)
    assert all(all(n == 0 for i, n in enumerate(row) if i != j) for row in baseline['confusion_matrix'])
    with (ROOT / 'data/multiclass/class_support.csv').open(newline='', encoding='utf-8') as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == len(d['class_support'])
    for row, expected in zip(rows, d['class_support']):
        assert row == {k: str(v) for k, v in expected.items()}


def verify_publication(d):
    def rows(name):
        with (ROOT / f'data/multiclass/{name}.csv').open(newline='', encoding='utf-8') as handle:
            return list(csv.DictReader(handle))
    metrics = rows('metrics')
    assert len(metrics) == len(d['models'])
    for r, model in zip(metrics, d['models']):
        assert r['model'] == model['model']
        for column, expected in [('test_macro_f1', model['test_report']['macro avg']['f1-score']),
                                 ('test_weighted_f1', model['test_report']['weighted avg']['f1-score']),
                                 ('test_accuracy', model['accuracy']),
                                 ('test_balanced_accuracy', model['test_report']['macro avg']['recall'])]:
            assert math.isclose(float(r[column]), expected)
    per_class = rows('per_class')
    confusion = rows('confusion')
    assert len(per_class) == len(d['models']) * len(d['classes'])
    assert len(confusion) == len(d['models']) * len(d['classes']) ** 2
    for model in d['models']:
        for sector in d['classes']:
            r = next(r for r in per_class if r['model'] == model['model'] and r['sector'] == sector)
            for key in ('precision', 'recall', 'f1-score', 'support'):
                assert math.isclose(float(r[key]), model['test_report'][sector][key])
        actual = {(r['actual_sector'], r['predicted_sector']): int(r['employers']) for r in confusion if r['model'] == model['model']}
        assert [[actual[a, b] for b in d['classes']] for a in d['classes']] == model['confusion_matrix']
    html = (ROOT / '_site/multiclass_analysis.html').read_text(encoding='utf-8')
    with ZipFile(ROOT / 'final_report.docx') as archive:
        xml = ET.fromstring(archive.read('word/document.xml'))
        text = ' '.join(n.text or '' for n in xml.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'))
        assert any(archive.read(p) == (ROOT / 'images/multiclass-confusion.png').read_bytes()
                   for p in archive.namelist() if p.startswith('word/media/'))
    selected = next(m for m in d['models'] if m['model'] == d['selected_model'])
    for artifact in (html, text):
        for phrase in ('Multiclass industry classification', d['selected_model'],
                       f"{selected['test_report']['macro avg']['f1-score']:.3f}",
                       'Transportation and warehousing (9)', 'Finance and insurance'):
            assert phrase in artifact, phrase
        if not d['comparison_with_saved_binary']['exact_snapshot_match']:
            assert 'Source file hashes differ' in artifact


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--published', action='store_true')
    args = parser.parse_args()
    d = json.loads((ROOT / 'data/multiclass/run.json').read_text(encoding='utf-8'))
    verify(d)
    corrupt = json.loads(json.dumps(d))
    corrupt['models'][0]['confusion_matrix'][0][0] += 1
    try:
        verify(corrupt)
    except AssertionError:
        pass
    else:
        raise AssertionError('Verifier accepted a corrupted confusion matrix')
    corrupt = json.loads(json.dumps(d))
    corrupt['comparison_with_saved_binary']['exact_snapshot_match'] = not d['comparison_with_saved_binary']['exact_snapshot_match']
    try:
        verify(corrupt)
    except AssertionError:
        pass
    else:
        raise AssertionError('Verifier accepted a false snapshot match')
    if args.published:
        verify_publication(d)
    print(f'MULTICLASS VERIFIED: {len(d["classes"])} classes; source hashes, exclusions, splits, metrics and corrupt-data control pass')


if __name__ == '__main__':
    main()
