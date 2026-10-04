"""Publish the additional experiment from saved aggregates, without source access."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/multiclass'


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |',
                      '|' + '|'.join('---' for _ in headers) + '|'] +
                     ['| ' + ' | '.join(map(str, row)) + ' |' for row in rows]) + '\n'


def main():
    d = json.loads((OUT / 'run.json').read_text(encoding='utf-8'))
    support, classes = d['class_support'], d['classes']
    selected = next(m for m in d['models'] if m['model'] == d['selected_model'])
    metrics, per_class, confusion = [], [], []
    for m in d['models']:
        report = m['test_report']
        metrics.append({'model': m['model'], 'validation_macro_f1': m.get('validation_macro_f1'),
                        'test_macro_f1': report['macro avg']['f1-score'],
                        'test_weighted_f1': report['weighted avg']['f1-score'],
                        'test_accuracy': m['accuracy'], 'test_balanced_accuracy': report['macro avg']['recall']})
        for i, sector in enumerate(classes):
            per_class.append({'model': m['model'], 'sector': sector, **report[sector]})
            for j, predicted in enumerate(classes):
                confusion.append({'model': m['model'], 'actual_sector': sector, 'predicted_sector': predicted,
                                  'employers': m['confusion_matrix'][i][j]})
    for name, rows in [('metrics', metrics), ('per_class', per_class), ('confusion', confusion)]:
        pd.DataFrame(rows).to_csv(OUT / f'{name}.csv', index=False)
    cm = np.array(selected['confusion_matrix'])
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.imshow(cm / cm.sum(axis=1, keepdims=True), cmap='Blues', vmin=0, vmax=1)
    ax.set(xticks=range(len(classes)), yticks=range(len(classes)), xticklabels=classes,
           yticklabels=classes, xlabel='Predicted NAICS sector', ylabel='Dataset-derived NAICS sector',
           title=f'{selected["model"]}: test employer counts')
    for i in range(len(classes)):
        for j in range(len(classes)):
            ax.text(j, i, str(cm[i, j]), ha='center', va='center',
                    color='white' if cm[i, j] / cm[i].sum() > .5 else 'black')
    fig.tight_layout()
    fig.savefig(ROOT / 'images/multiclass-confusion.png', dpi=180)
    plt.close(fig)
    baseline = metrics[-1]['test_macro_f1']
    excluded = [r for r in support if not r['included']]
    included = [r for r in support if r['included']]
    result = selected['test_report']
    comparison = d['comparison_with_saved_binary']
    provenance = ('Source file hashes match the saved healthcare experiment.' if comparison['exact_snapshot_match'] else
                  f"Source file hashes differ from the saved healthcare experiment in {comparison['changed_partition_hashes']} partitions. "
                  'The current dataset documents a NAICS hierarchy repair, while the healthcare results retain their earlier input manifest. '
                  'Equal row counts do not establish an identical snapshot; this extension is evaluated separately.')
    text = f'''## Multiclass industry classification

The additional experiment predicts one broad NAICS sector per employer. It extends the employer-name and job-title feature design in @goindani2017 beyond separate industry-membership questions. The healthcare career benchmark and the binary experiments retain their original scope.

### Sector definitions and coverage

The input contains {d['ledger']['source_rows']:,} records in {len(d['files'])} Jobs_2026_US partitions. {provenance} The January–September 2026, US, staffing, employer-name and normalized-title filters apply before employer aggregation. Codes 31, 32 and 33 map to manufacturing (31–33); 44 and 45 to retail trade (44–45); and 48 and 49 to transportation and warehousing (48–49). These mappings change {d['ledger']['sector_normalized_rows']:,} posting labels in the current input, which already uses combined sectors, before computing employer dominance. Missing and invalid sectors are excluded, not treated as a learnable industry.

Employers require at least 20 retained postings and an 80% dominant-sector share. After normalization, {d['ledger']['eligible_employers']:,} employers satisfy these rules. A sector requires at least {d['minimum_class_employers']} eligible employers to enter the experiment. This support rule retains {len(classes)} sectors and {d['ledger']['model_employers']:,} employers; {d['ledger']['excluded_low_support_employers']} eligible employers belong to sectors below the threshold. There is no employer cap. Labels describe broad sectors and remain unadjudicated dataset labels.

'''
    text += table(['NAICS', 'Industry', 'Employers'], [[r['sector'], r['industry'], r['eligible_employers']] for r in included])
    text += '\nExcluded sectors (eligible employer counts): ' + '; '.join(f'{r["sector"]} {r["industry"]} ({r["eligible_employers"]})' for r in excluded) + '.\n'
    text += '''
### Employer partitions and features

Within each retained class, employers are ordered by SHA-256 of the seed 2017 and normalized employer name. The first floor(70%) form training, the next employers up to floor(80%) form validation, and the remainder form testing. Each employer belongs to exactly one partition. Normalized names do not resolve corporate aliases, so related entities may still cross partitions. The class-support rule is set before feature fitting; it uses label counts to define the study population.

'''
    text += table(['NAICS', 'Train', 'Validation', 'Test'], [[r['sector'], r['train'], r['validation'], r['test']] for r in included])
    text += f'''
The partitions contain {d['splits']['train']} training, {d['splits']['validation']} validation and {d['splits']['test']} test employers. For each class, title and employer-word significance/frequency thresholds are calculated against the other training classes; the union of those selected vocabularies supplies {d['features']['count']} features. This replaces the healthcare-only positive-class feature selection. Titles retain the 1% within-employer share cutoff. Validation and test employers contribute neither vocabulary nor thresholds. Zero-feature employers remain in evaluation: {d['features']['zero_vectors_by_split']['train']} training, {d['features']['zero_vectors_by_split']['validation']} validation and {d['features']['zero_vectors_by_split']['test']} test.

### Model selection and held-out results

Scikit-learn implementations [@pedregosa2011] compare linear SVM, logistic regression, random forest and multiclass GBDT on identical partitions. SVM and logistic regression search C = 0.1, 1 and 10 with balanced class weights; random forest uses 200 trees and maximum depths 5 or unrestricted with balanced class weights; GBDT uses 100 boosting stages and tree depths 2 or 3 with default learning rate 0.1. GBDT uses unweighted training. Random states are fixed at 2017. Hyperparameters and then the model family are selected by validation macro-F1, with ties resolved by the listed order. Models are not refitted on validation data. The baseline always predicts the most frequent training class.

Macro-F1 gives each retained sector equal weight. Weighted-F1 and accuracy describe the observed test mix; balanced accuracy averages sector recall. Zero-denominator precision or F1 is recorded as zero. The validation-selected model is {selected['model']}, with test macro-F1 {result['macro avg']['f1-score']:.3f}, compared with {baseline:.3f} for the training-majority baseline. This is a separate endpoint from healthcare-positive F1, so scores cannot be read as a direct improvement over the binary experiment.

'''
    text += table(['Model', 'Valid. macro-F1', 'Test macro-F1', 'Weighted-F1', 'Accuracy', 'Bal. accuracy'],
                  [[r['model'], '—' if r['validation_macro_f1'] is None else f'{r["validation_macro_f1"]:.3f}',
                    *[f'{r[k]:.3f}' for k in ('test_macro_f1', 'test_weighted_f1', 'test_accuracy', 'test_balanced_accuracy')]] for r in metrics])
    text += f'\nPer-sector test results for the validation-selected {selected["model"]}:\n\n'
    text += table(['NAICS', 'Precision', 'Recall', 'F1', 'Test employers'],
                  [[s, *[f'{result[s][k]:.3f}' for k in ('precision', 'recall', 'f1-score')], int(result[s]['support'])] for s in classes])
    missed = [s for s in classes if result[s]['recall'] == 0]
    if missed:
        text += '\nThe selected model recovered no test employers in sector(s) ' + ', '.join(missed) + '. This limits its use for filtering those industries.\n'
    text += '''
![Confusion matrix for the validation-selected model. Cells show employer counts; color is normalized within each actual-sector row. Sector names appear in the coverage table.](images/multiclass-confusion.png){width=85%}

### Interpretation and limits

This experiment measures agreement across the supported broad industries. The predictions cover only retained sectors: an employer from an excluded sector would still be forced into one of these classes. No open-set detection or deployment inference is claimed. Rare sectors remain in the coverage report instead of being merged into an incoherent “other” class. The two-employer minimum validation support makes tuning sensitive to individual cases, and this single split does not establish stable sector-level performance. Independent label review, repeated employer-grouped evaluation and a later-period test remain necessary. Missing industry labels limit population coverage, and the results do not establish national hiring patterns.

The multiclass results do not replace the 112-posting healthcare career analysis or support personal skill-gap scores. Aggregate class support, metrics, per-sector results and all model confusion matrices accompany the source and run manifest.
'''
    (ROOT / '_content/multiclass-results.md').write_text(text, encoding='utf-8')
    print('MULTICLASS PUBLISHED: shared report section, four CSVs and confusion figure')


if __name__ == '__main__':
    main()
