"""Check the saved sample execution against visible HTML, without a server."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = {'preparation': 'data_preparation', 'market': 'market_baseline',
         'skills': 'skill_gap_analysis', 'evaluation': 'career_evaluation'}


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def verify(result, site):
    assert result['sample'] is True
    assert result['fraction'] == .1 and result['seed'] == 2017
    study = json.loads((ROOT / 'data/study/run.json').read_text(encoding='utf-8'))
    assert result['source_directory'] == study['source_directory']
    assert {(r['file'], r['rows']) for r in result['inputs']} == {(r['file'], r['rows']) for r in study['files']}
    assert result['script_sha256'] == hashlib.sha256((ROOT / 'scripts/publish_sample.py').read_bytes()).hexdigest()
    assert sum(item['rows'] for item in result['inputs']) == result['source_rows']
    assert 0 < result['sampled_rows'] < result['source_rows']
    counts = list(result['ledger'].values())
    assert all(a >= b for a, b in zip(counts, counts[1:])) and counts[-1] > 0
    for chunk in result['chunks']:
        html = (site / (PAGES[chunk['page']] + '.html')).read_text(encoding='utf-8')
        parser = Text()
        parser.feed(html)
        visible = ''.join(parser.parts)
        assert chunk['title'] in visible
        assert 'sourceCode python' in html, 'Missing highlighted Python chunk'
        for line in chunk['code'].splitlines() + chunk['output'].splitlines():
            assert line.strip() in visible, f'Missing displayed code/output: {line}'


if __name__ == '__main__':
    result = json.loads((ROOT / 'data/sample/run.json').read_text(encoding='utf-8'))
    verify(result, ROOT / '_site')
    # A known bad output must fail, proving the output check is active.
    result['chunks'][0]['output'] += '\nINTENTIONALLY_MISSING_SAMPLE_OUTPUT'
    try:
        verify(result, ROOT / '_site')
    except AssertionError:
        pass
    else:
        raise AssertionError('Negative control did not fail')
    print('SAMPLE VERIFIED: all 5 code chunks and partial outputs visible; negative control rejected')
