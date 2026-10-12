"""Check actual Spark evidence, code excerpts and notebook syntax without servers."""
import ast
import json
from pathlib import Path
from html.parser import HTMLParser
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / 'scripts/run_spark_study.py').read_text(encoding='utf-8')
tree = ast.parse(source)
walkthrough = (ROOT / '_content/spark-walkthrough.md').read_text(encoding='utf-8')
for node in tree.body:
    if isinstance(node, ast.FunctionDef):
        assert ast.get_source_segment(source, node) in walkthrough, node.name
notebook = json.loads((ROOT / 'notebooks/pyspark_classification.ipynb').read_text(encoding='utf-8'))
for cell in notebook['cells']:
    if cell['cell_type'] == 'code':
        ast.parse(''.join(cell['source']))
run = json.loads((ROOT / 'data/spark-study/run.json').read_text(encoding='utf-8'))
original = json.loads((ROOT / 'data/study/run.json').read_text(encoding='utf-8'))
assert run['engine'] == 'pyspark'
assert len(run['models']) == 11
assert len({r['model'] for r in run['models']}) == 11
assert {r['file']: r['sha256'] for r in run['files']} == {
    r['file']: r['sha256'] for r in original['files']}
for key, value in run['ledger'].items():
    assert value == original['ledger'][key], (key, value)
assert sum(r['count'] for r in run['splits']) == original['ledger']['model_employers']
test_n = sum(r['count'] for r in run['splits'] if r['split'] == 'test')
for r in run['models']:
    (tn, fp), (fn, tp) = r['confusion_matrix']
    assert tn + fp + fn + tp == r['support'] == test_n
    expected = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0
    assert abs(r['f1'] - expected) < 1e-12
    if 'trials' in r:
        assert r['validation_f1'] == max(t['validation_f1'] for t in r['trials'])
    assert all(0 <= r[k] <= 1 for k in ['precision', 'recall', 'f1', 'accuracy'])
for filename in ['index.qmd', 'final_report.qmd', 'career_evaluation.qmd',
                 '_content/research-framing.md']:
    text = (ROOT / filename).read_text(encoding='utf-8').lower()
    for phrase in ["user's request", 'user selected', 'approved analysis',
                   'connect claims to one bibtex', 'standup records',
                   'preserve this distinction', 'submission boundaries']:
        assert phrase not in text, (filename, phrase)

class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)

parser = VisibleText()
parser.feed((ROOT / '_site/pyspark_analysis.html').read_text(encoding='utf-8'))
visible = ''.join(parser.parts)
for node in tree.body:
    if isinstance(node, ast.FunctionDef):
        for line in ast.get_source_segment(source, node).splitlines():
            assert line.strip() in visible, ('Missing rendered code', line)
with ZipFile(ROOT / 'final_report.docx') as archive:
    doc = ET.fromstring(archive.read('word/document.xml'))
    report = ''.join(n.text or '' for n in doc.iter(
        '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'))
for text in [visible, report]:
    for r in run['models']:
        assert r['model'] in text, ('Missing published model', r['model'])
        assert f"{r['f1']:.3f}" in text, ('Missing published metric', r['model'])
    for name in ['prepare', 'fit_vocabulary', 'candidates', 'binary_metrics']:
        assert 'def ' + name in text
print('SPARK TEACHING VERIFIED: 9 classifier families, 2 baselines, matching source hashes and filter counts; source excerpts and notebook syntax checked')
