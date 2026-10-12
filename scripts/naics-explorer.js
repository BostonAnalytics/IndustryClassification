/* Aggregate-only explorer; no requests or raw employer records. */
function selectIndustries(data, level, parent, query, sort) {
  query = query.trim().toLowerCase();
  return data.groups.filter(r => r.level === Number(level) &&
    (!parent || r.parent === parent) &&
    (!query || (r.code + ' ' + r.name).toLowerCase().includes(query)))
    .sort((a, b) => sort === 'code' ? a.code.localeCompare(b.code) :
      b[sort] - a[sort] || a.code.localeCompare(b.code));
}
if (typeof module !== 'undefined') module.exports = { selectIndustries };
if (typeof document !== 'undefined') {
  const data = window.NAICS_DATA;
  const level = document.getElementById('level');
  const parent = document.getElementById('parent');
  const search = document.getElementById('search');
  const sort = document.getElementById('sort');
  const format = n => n.toLocaleString('en-US');
  function parents(selected = '') {
    parent.replaceChildren(new Option('All parents', ''));
    const codes = [...new Set(data.groups.filter(r => r.level === Number(level.value)).map(r => r.parent))].filter(Boolean).sort();
    for (const code of codes) {
      const record = data.groups.find(r => r.code === code && r.level === Number(level.value) - 1);
      parent.add(new Option(code + (record ? ' — ' + record.name : ''), code));
    }
    parent.value = selected;
    parent.disabled = Number(level.value) === 4;
  }
  function render() {
    const rows = selectIndustries(data, level.value, parent.value, search.value, sort.value);
    const body = document.getElementById('industry-rows');
    body.replaceChildren();
    for (const row of rows) {
      const tr = document.createElement('tr');
      for (const value of [row.code, row.name, format(row.postings), format(row.employers),
        (100 * row.postings / data.counts.posting_records).toFixed(2) + '%']) {
        const td = document.createElement('td'); td.textContent = value; tr.append(td);
      }
      const td = document.createElement('td');
      if (row.level < 6) {
        const button = document.createElement('button'); button.type = 'button'; button.className = 'btn btn-sm btn-outline-primary';
        button.textContent = 'View level ' + (row.level + 1);
        button.setAttribute('aria-label', 'Explore children of ' + row.code);
        button.addEventListener('click', () => { level.value = String(row.level + 1); search.value = ''; parents(row.code); render(); });
        td.append(button);
      }
      tr.append(td); body.append(tr);
    }
    const coverage = data.coverage[level.value];
    document.getElementById('explorer-status').textContent = `${format(rows.length)} industries shown · ${format(rows.reduce((n,r) => n+r.postings,0))} posting records in these rows. Level ${level.value} overall: ${format(coverage.classified)} classified; ${format(coverage.missing)} missing; ${format(coverage.invalid_format)} invalid-format codes. Employer counts overlap across industries.`;
    if (!rows.length) {
      const tr = document.createElement('tr'); const td = document.createElement('td'); td.colSpan = 6;
      td.textContent = 'No industries match these filters. Try another level or search.'; tr.append(td); body.append(tr);
    }
  }
  level.addEventListener('change', () => { parents(); render(); });
  parent.addEventListener('change', render); search.addEventListener('input', render); sort.addEventListener('change', render);
  parents(); render();
}
