"""Export browser-ready charts, tables and visible code from saved aggregates only."""
import csv
import hashlib
import html
import json
from pathlib import Path

import plotly
import plotly.graph_objects as go
from plotly.offline import get_plotlyjs

ROOT = Path(__file__).resolve().parents[1]
FIG = ROOT / 'images/interactive'
OUT = ROOT / 'data/interactive'
INPUTS = {}


def rows(name):
    path = ROOT / name
    INPUTS[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    with path.open(encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


def export(fig, name, title):
    fig.update_layout(template='plotly_white', title=title, font_size=14,
                      margin=dict(l=65, r=30, t=90, b=70), height=520)
    fig.write_json(OUT / f'{name}.json')
    fig.write_html(FIG / f'{name}.html', include_plotlyjs='directory',
                   div_id=name, config={'responsive': True, 'displaylogo': False,
                                        'topojsonURL': './'})
    return f'''\n### {title}

<iframe src="images/interactive/{name}.html" title="{html.escape(title)}" width="100%" height="550" loading="lazy" style="border:0"></iframe>

[Open chart](images/interactive/{name}.html) · [Download figure data](data/interactive/{name}.json)
'''


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    # Always refresh the shared bundle when the local Plotly version changes.
    (FIG / 'plotly.min.js').write_text(get_plotlyjs(), encoding='utf-8')
    assert (FIG / 'usa_110m.json').is_file(), 'US geometry must be present before exporting'
    parts = ['## Interactive charts\n']
    months = sorted(rows('data/eda/posted_month.csv'), key=lambda r: r['value'])
    fig = go.Figure(go.Bar(x=[r['value'] for r in months], y=[int(r['rows']) for r in months],
                          marker_color='#087e8b'))
    fig.update_layout(yaxis_title='Source records', xaxis_title='Posting month', xaxis_type='category')
    parts.append(export(fig, 'months', 'Posting months · full source snapshot'))
    parts.append('All source records, including dates outside the January–September study window. Counts are advertisements, not employment estimates.\n')
    skills = rows('data/study/eda_skills.csv')[::-1]
    fig = go.Figure(go.Bar(x=[int(r['postings']) for r in skills], y=[r['skill'] for r in skills],
                          orientation='h', marker_color='#087e8b'))
    fig.update_layout(xaxis_title='Selected career postings (skills may overlap)', yaxis_automargin=True)
    parts.append(export(fig, 'skills', 'Most listed skills · healthcare career cohort'))
    parts.append('The denominator is the full selected career cohort; missing skill lists remain in that denominator.\n')
    states = rows('data/eda/state.csv')
    names = 'Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|District of Columbia|Florida|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|New Hampshire|New Jersey|New Mexico|New York|North Carolina|North Dakota|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode Island|South Carolina|South Dakota|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West Virginia|Wisconsin|Wyoming'.split('|')
    codes = 'AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY'.split()
    mapping = dict(zip(names, codes))
    located = [r for r in states if r['value'] in mapping]
    unknown = sum(int(r['rows']) for r in states if r['value'] not in mapping)
    fig = go.Figure(go.Choropleth(locations=[mapping[r['value']] for r in located],
        z=[int(r['rows']) for r in located], text=[r['value'] for r in located],
        locationmode='USA-states', colorscale='Teal', colorbar_title='Records',
        hovertemplate='%{text}: %{z:,} records<extra></extra>'))
    fig.update_geos(scope='usa')
    parts.append(export(fig, 'states', 'US posting locations · full source snapshot'))
    parts.append(f'{unknown:,} missing or unrecognized state records are excluded from the map and retained in the source table. Colors show raw counts, not population-adjusted rates.\n')
    parts.append('## Searchable aggregate tables\n\nFilter any table by typing. CSV downloads preserve the complete table. Source-wide, career-cohort and historical comparison tables retain their separate folders and denominators.\n')
    for index, path in enumerate(sorted((ROOT / 'data').rglob('*.csv'))):
        name = path.relative_to(ROOT).as_posix()
        table = rows(name)
        if not table:
            continue
        fields = list(table[0])
        header = ''.join(f'<th scope="col">{html.escape(key)}</th>' for key in fields)
        body = ''.join('<tr>' + ''.join(f'<td>{html.escape(row[key])}</td>' for key in fields) + '</tr>' for row in table)
        # A standalone HTML table is also a portable export, usable outside Quarto.
        markup = f'<table><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>'
        filename = name.removeprefix('data/').replace('/', '-').removesuffix('.csv') + '.html'
        (OUT / filename).write_text('<!doctype html><meta charset="utf-8"><title>' + html.escape(name) + '</title>' + markup, encoding='utf-8')
        parts.append(f'\n### {name}\n\n[CSV]({name}) · [HTML table](data/interactive/{filename})\n\n'
                     f'<label for="filter-{index}">Filter {html.escape(name)}</label>\n'
                     f'<input id="filter-{index}" type="search" class="aggregate-filter" data-table="table-{index}">\n'
                     f'<div id="table-{index}" class="aggregate-table">{markup}</div>\n')
    parts.append('''
<script>
document.querySelectorAll('.aggregate-filter').forEach(input => {
  input.addEventListener('input', () => {
    const query = input.value.toLocaleLowerCase();
    document.querySelectorAll('#' + input.dataset.table + ' tbody tr').forEach(row => {
      row.hidden = !row.textContent.toLocaleLowerCase().includes(query);
    });
  });
});
</script>
''')
    (ROOT / '_content/interactive-results.md').write_text('\n'.join(parts), encoding='utf-8')
    code = []
    for path in sorted((ROOT / 'scripts').glob('*.py')):
        name = path.relative_to(ROOT).as_posix()
        INPUTS[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        code.append(f'## {path.name}\n\n[Download source]({name})\n\n````python\n{path.read_text(encoding="utf-8")}\n````\n')
    (ROOT / '_content/analysis-code.md').write_text('\n'.join(code), encoding='utf-8')
    assets = sorted([*FIG.glob('*'), *OUT.glob('*'), ROOT / '_content/interactive-results.md', ROOT / '_content/analysis-code.md'])
    manifest = {'plotly': plotly.__version__, 'inputs': INPUTS,
                'geometry_source': 'https://cdn.plot.ly/un/usa_110m.json',
                'outputs': {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in assets if p.name != 'manifest.json'}}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print('INTERACTIVE EXPORTED: charts, map, searchable tables and complete source')


if __name__ == '__main__':
    main()
