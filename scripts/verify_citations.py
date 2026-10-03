"""Verify resolved Quarto citation targets and the report bibliography."""
from html.parser import HTMLParser
from pathlib import Path
import re
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]

class Citations(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.cites, self.targets = set(), set(), set()
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if 'id' in a: self.ids.add(a['id'])
        self.cites.update(a.get('data-cites', '').split())
        if a.get('href', '').startswith('#ref-'): self.targets.add(a['href'][1:])

def verify_page(html, keys):
    parser = Citations(); parser.feed(html)
    for key in parser.cites:
        assert key in keys, f'Unknown key {key}'
        assert 'ref-'+key in parser.ids, f'Missing bibliography target {key}'
    assert parser.targets <= parser.ids, 'Broken citation link'
    return parser.cites

def main():
    entries = re.findall(r'@\w+\s*\{\s*([^,\s]+)\s*,', (ROOT/'reference.bib').read_text(encoding='utf-8'))
    assert entries and len(entries) == len(set(entries)), 'Empty or duplicate bibliography keys'
    keys = set(entries)
    used = set()
    for page in (ROOT/'_site').glob('*.html'):
        used.update(verify_page(page.read_text(encoding='utf-8'), keys))
    core = {'goindani2017','chern2018','tsvetkova2024','naics2022','pedregosa2011'}
    intro = (ROOT/'_site/introduction.html').read_text(encoding='utf-8')
    assert core <= verify_page(intro, keys), 'Missing literature-review citations'
    catalog = Citations(); catalog.feed((ROOT/'_site/references.html').read_text(encoding='utf-8'))
    assert {'ref-'+k for k in keys} <= catalog.ids, 'Incomplete central bibliography'
    # A bibliography catalog may retain uncited records; every actual citation must resolve.
    assert core <= used, 'Required literature sources are not cited'
    with ZipFile(ROOT/'final_report.docx') as archive:
        doc = ET.fromstring(archive.read('word/document.xml'))
        ns = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        text = ' '.join(n.text or '' for n in doc.findall('.//w:t',ns))
        for term in ['References','Goindani','Chern','Tsvetkova','Pedregosa','0.717','0.553']:
            assert term in text, f'Report missing {term}'
        assert not re.search(r'@(goindani2017|chern2018|tsvetkova2024|naics2022|pedregosa2011)',text)
        refs = text[text.rfind('References'):]
        for title in ['Automatically Detecting Errors','Scikit-learn','North American Industry Classification']:
            assert title.lower() in refs.lower(), f'Missing generated report reference: {title}'
        for phrase in ['Exploratory data analysis', 'Role-label consistency', 'Field coverage']:
            assert phrase in text, f'Missing report EDA section: {phrase}'
        for name in ['eda-selection.png','eda-coverage.png','eda-roles.png','eda-skills.png']:
            expected_image = (ROOT/'images'/name).read_bytes()
            assert any(archive.read(p) == expected_image for p in archive.namelist() if p.startswith('word/media/')), f'Missing report figure: {name}'
    # Negative control: a citation whose reference target is absent must fail.
    try:
        verify_page('<span data-cites="goindani2017"></span>',keys)
    except AssertionError:
        pass
    else:
        raise AssertionError('Broken citation negative control was incorrectly accepted')
    print(f'CITATIONS VERIFIED: {len(keys)} bibliography entries; five-source review; HTML targets and Word bibliography resolve')

if __name__ == '__main__':
    main()
