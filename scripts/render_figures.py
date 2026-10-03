"""Regenerate website/report figures from saved aggregates, without model fitting."""
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from run_study import bar_chart, FIG

ROOT=Path(__file__).resolve().parents[1]
d=json.loads((ROOT/'data/study/run.json').read_text())
c=d['career']['counts']
bar_chart(list(c['states'])[:10],list(c['states'].values())[:10],'Healthcare analyst postings by state','Postings in the selected sample','states.png')
bar_chart(list(c['remote']),list(c['remote'].values()),'Reported work arrangement','Postings in the selected sample','remote.png')
with (ROOT/'data/study/market_skills.csv').open(newline='',encoding='utf-8') as f: skills=list(csv.DictReader(f))[:12]
bar_chart([r['skill'] for r in skills],[int(r['postings']) for r in skills],'Most frequently listed skills','Postings mentioning skill; denominator = 112 selected postings','skills.png')
fig,axes=plt.subplots(1,2,figsize=(9,4))
for ax,result in zip(axes,d['models'][:2]):
    matrix=np.array(result['confusion_matrix'])
    ax.imshow(matrix,cmap='Blues')
    for i in range(2):
        for j in range(2):
            ax.text(j,i,str(matrix[i,j]),ha='center',va='center',color='white' if matrix[i,j]>matrix.max()/2 else '#102b3f')
    ax.set(xticks=[0,1],yticks=[0,1],xticklabels=['Other','NAICS 62'],yticklabels=['Other','NAICS 62'],xlabel='Predicted',ylabel='Dataset label',title=result['model'])
fig.tight_layout(); fig.savefig(FIG/'confusion.png',dpi=180,bbox_inches='tight'); plt.close(fig)
print('FIGURES GENERATED')
