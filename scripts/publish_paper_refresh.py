"""Regenerate the paper's cross-experiment interpretation from completed runs."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    study = json.loads((ROOT/'data/study/run.json').read_text())
    multi = json.loads((ROOT/'data/multiclass/run.json').read_text())
    naics = json.loads((ROOT/'data/naics/snapshot.json').read_text())
    spark = json.loads((ROOT/'data/spark-study/run.json').read_text())
    signatures = lambda files: {r['file']: r['sha256'] for r in files}
    assert all(signatures(d['files']) == signatures(study['files']) for d in (multi, naics, spark)), 'Experiments must share the released snapshot'
    c, ledger = study['career'], study['ledger']
    svm, gbdt = study['models'][:2]
    selected = next(m for m in multi['models'] if m['model'] == multi['selected_model'])
    spark_best = max(spark['models'][:9], key=lambda m: m['validation_f1'])
    f1 = lambda m: m['test_report']['1']['f1-score']
    macro = selected['test_report']['macro avg']['f1-score']
    text = f'''The refreshed analysis uses **{ledger['source_rows']:,} posting records in {len(study['files'])} files** from release `{naics['release_id']}`. The complete source contains **{naics['counts']['distinct_employer_names']:,} distinct normalized employer names**. These names are not independently resolved legal entities, and posting records are not necessarily unique vacancies.

The original January–September 2026 observation window and cohort rules are retained. They yield **{ledger['model_employers']} employers** for binary classification, **{multi['ledger']['model_employers']} employers in {len(multi['classes'])} sectors** for multiclass classification, and **{c['postings']} healthcare analyst postings** for the career benchmark. The small modeling and career samples reflect these filters, not a source dataset of only a few hundred jobs.

On held-out employers, linear SVM achieves healthcare-positive F1 **{f1(svm):.3f}** and GBDT **{f1(gbdt):.3f}**. The multiclass model selected by validation macro-F1 is {selected['model']}, with test macro-F1 **{macro:.3f}**. All three experiments, including the separately split Spark comparison, use matching input-file hashes. These scores measure agreement with supplied industry labels, not independent verification of employer industry.

![Held-out model performance on the refreshed release. Panels use different targets and test populations; compare models within each panel. The multiclass family is selected on validation data.](images/evaluation-comparison.png)

GBDT identifies {gbdt['confusion_matrix'][1][1]} of {study['splits']['test']['positive']} healthcare employers and misses {gbdt['confusion_matrix'][1][0]}. Its high precision therefore does not justify automatic exclusion of employers predicted to be outside healthcare. The all-positive baseline reaches F1 {f1(study['models'][3]):.3f}, illustrating why precision, recall and confusion counts are needed alongside F1. In the multiclass experiment, the selected model recovers no finance-and-insurance employers in the test set. Uneven sector support and a single small validation split constrain broader claims.

The Spark comparison selects {spark_best['model']} by validation F1 and obtains test F1 {spark_best['f1']:.3f}. Its deterministic hash-based split differs from the scikit-learn binary split. Score differences consequently mix partition and implementation effects and cannot establish an engine advantage.

## Finer industry labels and the scope of evaluation

The NAICS 4, 5 and 6 explorer describes labels already present in the full source. It does not evaluate a trained fine-code classifier. Coverage decreases with code depth, so missing codes must remain visible in the denominator.

![NAICS code availability in the complete US release. Coverage is the share of posting records with a numeric source code of the required length; it is not a measure of classification accuracy.](images/naics-coverage.png)

The career benchmark remains at sector 62 for continuity with the original design. A four-, five- or six-digit prediction experiment would need its own employer-support assessment, independently reviewed labels and leakage-controlled evaluation. SEC CIK and filing markers can supply dated employer evidence, but candidate name matches are not verified links or ground-truth NAICS labels.
'''
    (ROOT/'_content/refresh-results.md').write_text(text, encoding='utf-8')
    summary = f'''The January–September 2026 analysis selects **{c['postings']} career postings** and **{ledger['model_employers']} employers** for binary classification from **{ledger['source_rows']:,} posting records in {len(study['files'])} files**. The full source contains **{naics['counts']['distinct_employer_names']:,} normalized employer names**. The multiclass extension retains **{multi['ledger']['model_employers']} employers across {len(multi['classes'])} sectors**.

Employer-name-disjoint test F1 is **{f1(svm):.3f} for linear SVM** and **{f1(gbdt):.3f} for GBDT**. The validation-selected multiclass {selected['model'].lower()} scores **{macro:.3f} macro-F1**. These are measures of agreement with dataset-derived labels. SQL appears in 63 career postings; only three have a positive normalized salary with explicit USD.

The original research structure and observation window are retained. The [refreshed evaluation](career_evaluation.qmd) explains the samples, errors and implications. [Full dataset coverage](data_coverage.qmd) and the [NAICS 4/5/6 explorer](naics_explorer.qmd) supplement the paper with source-wide counts.
'''
    (ROOT/'_content/paper-summary.md').write_text(summary, encoding='utf-8')
    abstract = f'''This exploratory study examines employer-industry classification as a data-quality component of a career evaluation product for healthcare data analysts. It reconstructs a 2017 study and adapts its approach to the published 20-file Jobs_2026_US release. A scan of {ledger['source_rows']:,} records yielded {ledger['model_employers']} eligible employers for binary classification and {c['postings']} postings for a January–September 2026 US career benchmark. Employer-name-disjoint scikit-learn evaluation produced positive-class F1 scores of {f1(svm):.3f} for linear SVM and {f1(gbdt):.3f} for GBDT. A separate PySpark experiment compares nine classifier families and two baselines; the validation-selected {spark_best['model'].lower()} achieved test F1 of {spark_best['f1']:.3f}. Different employer splits prevent direct attribution of score differences to the software engine. A multiclass extension retains {len(multi['classes'])} broad NAICS sectors and {multi['ledger']['model_employers']} employers; the validation-selected {selected['model'].lower()} achieved test macro-F1 of {macro:.3f}, against {multi['models'][-1]['test_report']['macro avg']['f1-score']:.3f} for the training-majority baseline. These scores measure agreement with dataset-derived labels rather than independently established employer truth. SQL appeared in 63 career postings. Sparse salary evidence, missing work-arrangement fields and incomplete fine-code industry coverage restrict recommendations. The findings do not establish national hiring patterns or personal skill deficits.
'''
    (ROOT/'_content/paper-abstract.md').write_text(abstract, encoding='utf-8')
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(2, 1, figsize=(8, 7.5), layout='constrained')
    for ax, models, metric, title in [(axes[0], study['models'], f1, 'Binary healthcare · positive-class F1'),
                                    (axes[1], multi['models'], lambda m: m['test_report']['macro avg']['f1-score'], 'Multiclass sectors · macro-F1')]:
        values = [metric(m) for m in models]
        bars = ax.barh([m['model'] for m in models], values, color=['#087e8b' if 'majority' not in m['model'].lower() and m['model'] != 'All positive' else '#8a959e' for m in models])
        ax.bar_label(bars, fmt='%.3f', padding=3)
        ax.set(xlim=(0, 1), xlabel='Held-out test score', title=title)
        ax.invert_yaxis()
    fig.savefig(ROOT/'images/evaluation-comparison.png', dpi=180)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 3.8), layout='constrained')
    levels = list(naics['coverage'])
    values = [naics['coverage'][l]['classified']/ledger['source_rows']*100 for l in levels]
    ax.barh([f'NAICS {l}' for l in levels], [100]*3, color='#e6ebed', label='Missing or invalid code')
    bars = ax.barh([f'NAICS {l}' for l in levels], values, color='#087e8b', label='Code present')
    ax.bar_label(bars, labels=[f" {v:.1f}% · {naics['coverage'][l]['classified']:,} postings" for l, v in zip(levels, values)], padding=4)
    ax.set(xlim=(0, 100), xlabel=f"Share of all {ledger['source_rows']:,} posting records (%)", title='Finer NAICS coverage in the complete US release')
    ax.invert_yaxis()
    fig.savefig(ROOT/'images/naics-coverage.png', dpi=180)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(9, 6), layout='constrained')
    y = np.arange(len(spark['models']))
    for offset, key, color in [(-.24, 'precision', '#087e8b'), (0, 'recall', '#b76933'), (.24, 'f1', '#526a88')]:
        ax.barh(y+offset, [m[key] for m in spark['models']], height=.23, label=key.capitalize(), color=color)
    ax.set(yticks=y, yticklabels=[m['model'] for m in spark['models']], xlim=(0, 1.05),
           xlabel='Healthcare-positive test metric', title=f"Spark comparison · {spark['models'][0]['support']} held-out employers")
    ax.invert_yaxis()
    ax.legend(loc='upper center', bbox_to_anchor=(.5, -.12), ncol=3, fontsize=9)
    fig.savefig(ROOT/'images/spark-comparison.png', dpi=180)
    plt.close(fig)
    receipt = {'release_id': naics['release_id'], 'source_manifest_sha256': naics['source_manifest_sha256'],
               'inputs': {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                          [ROOT/f'data/{n}/run.json' for n in ('study', 'multiclass', 'spark-study', 'eda')]},
               'binary_employers': ledger['model_employers'], 'career_postings': c['postings'],
               'multiclass_employers': multi['ledger']['model_employers'], 'matched_input_hashes': True}
    (ROOT/'data/study/paper-refresh.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print('PAPER REFRESH GENERATED: matching snapshots; narrative and comparative figures')


if __name__ == '__main__':
    main()
