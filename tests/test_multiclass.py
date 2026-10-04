"""Behavioral controls for label handling, employer isolation and feature leakage."""
from collections import Counter
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from run_multiclass import normalize_sector, make_splits, build_features


def employer(sector, title='analyst', count=20):
    return {'count': count, 'titles': Counter({title: count}), 'sectors': Counter({sector: count})}


class MulticlassTests(unittest.TestCase):
    def test_sector_ranges_and_unknowns(self):
        for raw, expected in [('31', '31-33'), ('33', '31-33'), ('44', '44-45'),
                              ('49', '48-49'), (' 62 ', '62'), ('48-49', '48-49'),
                              (None, None), ('99', None), ('00', None), ('620', None)]:
            self.assertEqual(normalize_sector(raw), expected)

    def test_class_support_and_deterministic_employer_splits(self):
        data = {f'employer-{s}-{i}': employer(s) for s in ('62', '54', '48-49') for i in range(20)}
        data.update({f'rare-{i}': employer('11') for i in range(19)})
        data['too small'] = employer('62', count=19)
        data['mixed'] = {'count': 20, 'titles': Counter(analyst=20), 'sectors': Counter({'62': 15, '54': 5})}
        names, y, splits, support, ledger = make_splits(data)
        self.assertEqual(len(names), 60)
        self.assertEqual(ledger['excluded_low_support_employers'], 19)
        self.assertEqual(ledger['employers_below_20'], 1)
        self.assertEqual(ledger['employers_without_dominant_sector'], 1)
        self.assertEqual(set(np.concatenate(list(splits.values()))), set(range(60)))
        self.assertEqual(sum(map(len, splits.values())), 60)
        for row in support:
            if row['included']:
                self.assertEqual([row[s] for s in ('train', 'validation', 'test')], [14, 2, 4])
        again = make_splits(dict(reversed(list(data.items()))))
        self.assertEqual(names, again[0])
        for split in splits:
            np.testing.assert_array_equal(splits[split], again[2][split])

    def test_holdout_tokens_never_enter_features(self):
        names = ['alpha hospital', 'beta hospital', 'gamma transport', 'delta transport', 'holdoutonly private']
        data = {n: employer('62' if i < 2 else '48-49', 'nurse' if i < 2 else 'driver') for i, n in enumerate(names)}
        data[names[-1]] = employer('62', 'unseentitle')
        y = np.array(['62', '62', '48-49', '48-49', '62'])
        X, vectorizer, _ = build_features(data, names, y, np.array([0, 1, 2, 3]))
        self.assertIn('t:nurse', vectorizer.feature_names_)
        self.assertIn('t:driver', vectorizer.feature_names_)
        self.assertNotIn('t:unseentitle', vectorizer.feature_names_)
        self.assertNotIn('w:holdoutonly', vectorizer.feature_names_)
        self.assertEqual(X[-1].nnz, 0)

    def test_too_few_classes_fails(self):
        with self.assertRaisesRegex(ValueError, 'Fewer than three'):
            make_splits({'only': employer('62')})


if __name__ == '__main__':
    unittest.main()
