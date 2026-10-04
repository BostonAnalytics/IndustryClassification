"""Additional multiclass experiment; source records and employer identities stay private."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import platform
import re

import numpy as np
import pandas as pd
import pyarrow
import pyarrow.parquet as pq
import sklearn
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, f1_score
from sklearn.svm import LinearSVC

from run_study import clean, tokens, select_vocab

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/multiclass'
SECTORS = {
    '11': 'Agriculture, forestry, fishing and hunting',
    '21': 'Mining, quarrying, and oil and gas extraction',
    '22': 'Utilities', '23': 'Construction', '31-33': 'Manufacturing',
    '42': 'Wholesale trade', '44-45': 'Retail trade',
    '48-49': 'Transportation and warehousing', '51': 'Information',
    '52': 'Finance and insurance', '53': 'Real estate and rental and leasing',
    '54': 'Professional, scientific and technical services',
    '55': 'Management of companies and enterprises',
    '56': 'Administrative/support and waste management/remediation services',
    '61': 'Educational services', '62': 'Health care and social assistance',
    '71': 'Arts, entertainment and recreation',
    '72': 'Accommodation and food services',
    '81': 'Other services (except public administration)',
    '92': 'Public administration',
}
COMBINED = {**dict.fromkeys(['31', '32', '33'], '31-33'),
            **dict.fromkeys(['44', '45'], '44-45'),
            **dict.fromkeys(['48', '49'], '48-49')}
COLS = ['ID', 'POSTED', 'COMPANY_NAME', 'TITLE_NAME', 'PARSED_COUNTRY_ISO_ABBR',
        'NAICS_2022_2', 'NAICS2', 'COMPANY_IS_STAFFING']


def normalize_sector(value):
    value = clean(value)
    value = COMBINED.get(value, value)
    return value if value in SECTORS else None


def read_employers(data_dir):
    files = sorted(data_dir.glob('jobs_2026_part_*.parquet'))
    if not files:
        raise ValueError('No source partitions found')
    ledger, seen, manifests = Counter(), set(), []
    employers = defaultdict(lambda: {'count': 0, 'titles': Counter(), 'sectors': Counter()})
    for path in files:
        parquet = pq.ParquetFile(path)
        with path.open('rb') as handle:
            digest = hashlib.file_digest(handle, 'sha256').hexdigest()
        manifests.append({'file': path.name, 'bytes': path.stat().st_size,
                          'rows': parquet.metadata.num_rows, 'sha256': digest})
        for batch in parquet.iter_batches(columns=COLS, batch_size=20000):
            dates = pd.to_datetime(batch.column('POSTED').to_pylist(), errors='coerce', utc=True, format='mixed')
            for row, date in zip(batch.to_pylist(), dates):
                ledger['source_rows'] += 1
                if row['ID'] is None:
                    ledger['missing_id'] += 1
                    continue
                if row['ID'] in seen:
                    raise ValueError('Duplicate posting ID; resolve source ordering before analysis')
                seen.add(row['ID'])
                ledger['unique_id_rows'] += 1
                if pd.isna(date) or not (pd.Timestamp('2026-01-01', tz='UTC') <= date < pd.Timestamp('2026-10-01', tz='UTC')):
                    ledger['outside_period_or_unknown_date'] += 1
                    continue
                ledger['period_rows'] += 1
                if clean(row['PARSED_COUNTRY_ISO_ABBR']).upper() != 'US':
                    ledger['non_us_or_unknown_country'] += 1
                    continue
                ledger['us_rows'] += 1
                raw_sector = clean(row['NAICS_2022_2']) or clean(row['NAICS2'])
                sector = normalize_sector(raw_sector)
                if sector is None:
                    ledger['missing_or_invalid_sector'] += 1
                    continue
                ledger['sector_known_rows'] += 1
                ledger['sector_normalized_rows'] += sector != raw_sector
                if row['COMPANY_IS_STAFFING'] == 1:
                    ledger['staffing_excluded'] += 1
                    continue
                ledger['nonstaffing_or_unknown_rows'] += 1
                name = re.sub(r'\s+', ' ', clean(row['COMPANY_NAME']).casefold())
                title = clean(row['TITLE_NAME']).casefold()
                if name in ('', 'unknown', 'unclassified') or title in ('', 'unknown', 'unclassified'):
                    ledger['missing_employer_or_title'] += 1
                    continue
                e = employers[name]
                e['count'] += 1
                e['titles'][title] += 1
                e['sectors'][sector] += 1
                ledger['employer_model_postings'] += 1
        print(f'Read {path.name}: {ledger["source_rows"]:,} rows', flush=True)
    return employers, ledger, manifests


def make_splits(employers, minimum_class=20):
    """Require 20 employers per class before splitting, giving at least 14/2/4."""
    if minimum_class < 20:
        raise ValueError('At least 20 employers per class are required')
    groups = defaultdict(list)
    ledger = Counter(employers_before_filters=len(employers))
    for name, e in employers.items():
        sector, count = e['sectors'].most_common(1)[0]
        if e['count'] < 20:
            ledger['employers_below_20'] += 1
        elif count / e['count'] < .8:
            ledger['employers_without_dominant_sector'] += 1
        else:
            groups[sector].append(name)
    classes = sorted(s for s, names in groups.items() if len(names) >= minimum_class)
    if len(classes) < 3:
        raise ValueError('Fewer than three sectors meet the declared class-support threshold')
    names, labels, split_indices, support = [], [], defaultdict(list), []
    for sector in sorted(SECTORS):
        members = sorted(groups[sector], key=lambda n: (hashlib.sha256(('2017:' + n).encode()).hexdigest(), n))
        row = {'sector': sector, 'industry': SECTORS[sector], 'eligible_employers': len(members),
               'included': sector in classes, 'train': 0, 'validation': 0, 'test': 0}
        if sector in classes:
            for rank, name in enumerate(members):
                split = 'train' if rank < int(.7 * len(members)) else ('validation' if rank < int(.8 * len(members)) else 'test')
                split_indices[split].append(len(names))
                names.append(name)
                labels.append(sector)
                row[split] += 1
        support.append(row)
    ledger['eligible_employers'] = sum(len(v) for v in groups.values())
    ledger['excluded_low_support_employers'] = ledger['eligible_employers'] - len(names)
    ledger['model_employers'] = len(names)
    return names, np.array(labels), {k: np.array(v) for k, v in split_indices.items()}, support, ledger


def build_features(employers, names, y, train):
    """Union of training-only one-versus-rest vocabularies extends the paper's filter."""
    all_t, all_w = Counter(), Counter()
    pos_t, pos_w = defaultdict(Counter), defaultdict(Counter)
    for i in train:
        e = employers[names[i]]
        all_t.update(e['titles'])
        all_w.update(tokens(names[i]))
        pos_t[y[i]].update(e['titles'])
        pos_w[y[i]].update(tokens(names[i]))
    titles, words, thresholds = set(), set(), {}
    for label in sorted(set(y[train])):
        thresholds[label] = {}
        for kind, total, positive, target in [('titles', all_t, pos_t[label], titles), ('words', all_w, pos_w[label], words)]:
            if any(c > 1 for c in positive.values()):
                vocab, rule = select_vocab(total, positive)
                target.update(vocab)
                thresholds[label][kind] = rule | {'selected': len(vocab)}
            else:
                thresholds[label][kind] = {'selected': 0, 'reason': 'No token occurs more than once in this training class'}
    rows = []
    for name in names:
        e = employers[name]
        row = {'t:' + t: n / e['count'] for t, n in e['titles'].items() if t in titles and n / e['count'] >= .01}
        row.update({'w:' + w: 1. for w in tokens(name) & words})
        rows.append(row)
    vectorizer = DictVectorizer()
    vectorizer.fit([rows[i] for i in train])
    if not vectorizer.feature_names_:
        raise ValueError('No training features survived selection')
    return vectorizer.transform(rows), vectorizer, thresholds


def evaluate(y, pred, classes):
    return {'test_report': classification_report(y, pred, labels=classes, output_dict=True, zero_division=0),
            'confusion_matrix': confusion_matrix(y, pred, labels=classes).tolist(),
            'accuracy': float(np.mean(y == pred))}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--minimum-class-employers', type=int, default=20)
    args = parser.parse_args()
    employers, ledger, files = read_employers(args.data_dir)
    names, y, splits, support, filters = make_splits(employers, args.minimum_class_employers)
    ledger.update(filters)
    classes = sorted(set(y))
    # Integer targets avoid mixed numeric/range-string coercion in estimators.
    class_array = np.array(classes)
    encoded_y = np.searchsorted(class_array, y)
    print(f'Class support: {[(r["sector"], r["eligible_employers"], r["included"]) for r in support]}', flush=True)
    train, valid, test = [splits[s] for s in ('train', 'validation', 'test')]
    assert len(set(names)) == len(names)
    assert set(train).isdisjoint(valid) and set(train).isdisjoint(test) and set(valid).isdisjoint(test)
    X, vectorizer, thresholds = build_features(employers, names, y, train)
    families = [
        ('Linear SVM', [LinearSVC(C=c, class_weight='balanced', random_state=2017, max_iter=20000) for c in [.1, 1, 10]]),
        ('Logistic regression', [LogisticRegression(C=c, class_weight='balanced', random_state=2017, max_iter=3000) for c in [.1, 1, 10]]),
        ('Random forest', [RandomForestClassifier(n_estimators=200, max_depth=d, class_weight='balanced', random_state=2017, n_jobs=1) for d in [5, None]]),
        ('GBDT', [GradientBoostingClassifier(n_estimators=100, max_depth=d, random_state=2017) for d in [2, 3]]),
    ]
    models = []
    for name, candidates in families:
        trials, best_score, best = [], -1, None
        for model in candidates:
            model.fit(X[train], encoded_y[train])
            score = f1_score(y[valid], class_array[model.predict(X[valid])], labels=classes, average='macro', zero_division=0)
            trials.append({'params': model.get_params(), 'validation_macro_f1': float(score)})
            if score > best_score:
                best_score, best = score, model
        result = {'model': name, 'validation_macro_f1': float(best_score), 'trials': trials,
                  'selected_params': best.get_params(), **evaluate(y[test], class_array[best.predict(X[test])], classes)}
        models.append(result)
        print(f'{name}: validation macro-F1={best_score:.3f}; test macro-F1={result["test_report"]["macro avg"]["f1-score"]:.3f}', flush=True)
    majority = sorted(Counter(y[train]), key=lambda c: (-Counter(y[train])[c], c))[0]
    models.append({'model': 'Training majority', 'majority_sector': majority,
                   **evaluate(y[test], np.repeat(majority, len(test)), classes)})
    # Select the family by validation only; test metrics do not enter selection.
    selected = max(models[:-1], key=lambda m: m['validation_macro_f1'])['model']
    binary_path = ROOT / 'data/study/run.json'
    binary = json.loads(binary_path.read_text(encoding='utf-8'))
    old_files = {f['file']: f for f in binary['files']}
    snapshot_comparison = {
        'binary_manifest_sha256': hashlib.sha256(binary_path.read_bytes()).hexdigest(),
        'same_file_names_and_rows': [(f['file'], f['rows']) for f in files] == [(f['file'], f['rows']) for f in binary['files']],
        'changed_partition_hashes': sum(f['sha256'] != old_files.get(f['file'], {}).get('sha256') for f in files),
        'exact_snapshot_match': files == binary['files'],
    }
    result = {'source_directory': str(args.data_dir.resolve()), 'files': files,
              'versions': {'python': platform.python_version(), 'numpy': np.__version__, 'pandas': pd.__version__,
                           'pyarrow': pyarrow.__version__, 'sklearn': sklearn.__version__},
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'feature_helper_sha256': hashlib.sha256((ROOT / 'scripts/run_study.py').read_bytes()).hexdigest(),
              'minimum_class_employers': args.minimum_class_employers, 'ledger': dict(ledger),
              'comparison_with_saved_binary': snapshot_comparison,
              'classes': classes, 'class_support': support, 'employer_overlap': 0,
              'splits': {s: len(ix) for s, ix in splits.items()},
              'split_rule': 'Within-class SHA256(2017:normalized employer), floor 70%/80% boundaries; no cap',
              'features': {'count': X.shape[1], 'thresholds': thresholds,
                           'zero_vectors_by_split': {s: int(np.sum(X[ix].getnnz(axis=1) == 0)) for s, ix in splits.items()}},
              'models': models, 'selected_model': selected}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'run.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    pd.DataFrame(support).to_csv(OUT / 'class_support.csv', index=False)
    print(f'MULTICLASS COMPLETE: {len(classes)} classes; {len(names)} employers; selected {selected}')


if __name__ == '__main__':
    main()
