"""Verify deployed paper pages and fresh evidence against checked local files."""
import hashlib
import json
from pathlib import Path
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://bostonanalytics.github.io/IndustryClassification/'


def fetch(path):
    request = Request(BASE + path + '?refresh=' + str(time.time_ns()), headers={'Cache-Control': 'no-cache'})
    with urlopen(request, timeout=30) as response:
        return response.read()


def main():
    paths = [p.name for p in sorted((ROOT/'_site').glob('*.html'))]
    paths += [f'data/{name}/run.json' for name in ('study', 'multiclass', 'spark-study', 'eda')]
    paths += ['data/overview/coverage.json', 'data/naics/snapshot.json', 'data/global/snapshot.json',
              'data/study/paper-refresh.json', 'images/evaluation-comparison.png',
              'images/naics-coverage.png', 'images/multiclass-confusion.png', 'images/confusion.png',
              'images/spark-comparison.png', 'data/naics/column_coverage.csv', 'data/spark-study/runtime.json',
              'scripts/run_study.py', 'scripts/run_multiclass.py', 'scripts/run_spark_study.py',
              'scripts/naics-explorer.js', 'final_report.docx',
              'data/overview/dataset_counts.csv', 'data/overview/csv-tables.json',
              'data/eda/sector.csv', 'data/eda/remote.csv', 'data/eda/posted_month.csv',
              'data/naics/industries.csv']
    for attempt in range(12):
        try:
            checked = {}
            for path in paths:
                expected = (ROOT/'_site'/path).read_bytes()
                actual = fetch(path)
                if actual != expected:
                    raise ValueError('Published bytes differ: ' + path)
                checked[path] = hashlib.sha256(actual).hexdigest()
            receipt = {'status': 'verified', 'url': BASE, 'verified_at_epoch': time.time(),
                       'checks': ['restored paper pages equal local render', 'new model and source manifests',
                                  'updated figures', 'NAICS explorer', 'regenerated Word report'],
                       'verified_sha256': checked}
            (ROOT/'docs/maintenance/website-deployment.json').write_text(json.dumps(receipt, indent=2)+'\n')
            print('LIVE PAPER VERIFIED:', BASE, len(checked), 'exact file matches')
            return
        except Exception as exc:
            print(f'Attempt {attempt + 1}: {type(exc).__name__}: {exc}', flush=True)
            if attempt == 11:
                raise
            time.sleep(10)


if __name__ == '__main__':
    main()
