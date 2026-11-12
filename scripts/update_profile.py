"""Generate profile artwork from public GitHub data using the authenticated gh CLI"""
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets'
USER = 'monolithcraft'
def api(endpoint, *args):
    return json.loads(subprocess.check_output(['gh', 'api', endpoint, *args], text=True))
user = api(f'users/{USER}')
repos = api(f'users/{USER}/repos?per_page=100&sort=pushed')
projects = [repo for repo in repos if repo['name'].lower() != USER.lower()]
query = 'query { user(login:"'+USER+'") { contributionsCollection { contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } } } } }'
calendar = api('graphql', '-f', 'query='+query)['data']['user']['contributionsCollection']['contributionCalendar']
days = [d for week in calendar['weeks'] for d in week['contributionDays']]
updates=[]
for repo in projects[:8]:
    try:
        for c in api(f"repos/{repo['full_name']}/commits?per_page=6"):
            if c['commit']['message'].startswith('chore: refresh profile'): continue
            updates.append({'repo':repo['name'],'sha':c['sha'][:7],'title':c['commit']['message'].splitlines()[0], 'date':c['commit']['committer']['date'],'url':c['html_url']})
    except subprocess.CalledProcessError:
        continue
updates.sort(key=lambda x:x['date'], reverse=True)
now=datetime.now(timezone.utc).strftime('%d %b %Y').upper()
class Panel:
    def __init__(self,h,title,label):
        self.h=h
        self.p=[f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{h}" viewBox="0 0 1200 {h}" role="img" aria-label="{escape(title)}">',f'<rect x="1" y="1" width="1198" height="{h-2}" rx="8" fill="#0a0c0f" stroke="#30343a"/>']
        self.text(38,46,title,19,'#e9e7e1','Georgia,serif','letter-spacing="3"')
        self.text(1162,44,label,11,'#818891',extra='text-anchor="end" letter-spacing="2"')
        self.path('M38 69H1162','#2e3238')
    def text(self,x,y,s,size=14,color='#c4c7cc',font='monospace',extra=''):
        self.p.append(f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" fill="{color}" {extra}>{escape(str(s))}</text>')
    def rect(self,x,y,w,h,fill,rx=0,stroke='none'):
        self.p.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}"/>')
    def path(self,d,color='#89919b',extra=''):
        self.p.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.5" {extra}/>')
    def save(self,name):
        (OUT/name).write_text('\n'.join(self.p+['</svg>']))

p=Panel(230,'OVERVIEW','PUBLIC GITHUB DATA')
metrics=[('REPOSITORIES',len(repos)),('CONTRIBUTIONS',calendar['totalContributions']),('STARS',sum(r['stargazers_count'] for r in repos)),('FOLLOWERS',user['followers'])]
for i,(label,value) in enumerate(metrics):
    x=40+i*290
    if i: p.path(f'M{x-20}99V194','#282d34')
    p.text(x,161,value,57,'#eeede7','Georgia,serif')
    p.text(x,194,label,11,'#949ba4',extra='letter-spacing="2"')
p.save('overview.svg')

p=Panel(310,'CONTRIBUTIONS','LAST 12 MONTHS')
weeks=calendar['weeks']
colors=['#171b21','#4d555f','#818a94','#b9c0c7','#eceee9']
for wi,week in enumerate(weeks):
    for day in week['contributionDays']:
        dt=datetime.strptime(day['date'],'%Y-%m-%d')
        row=(dt.weekday()+1)%7
        n=day['contributionCount']; col=colors[0 if n==0 else min(4,1+(n-1)//3)]
        x=72+wi*20;y=115+row*19
        p.p.append(f'<rect x="{x}" y="{y}" width="15" height="15" rx="2" fill="{col}"><title>{day["date"]} — {n} contributions</title></rect>')
last_month=None
for wi,week in enumerate(weeks):
    d=week['contributionDays'][0]['date']; month=d[:7]
    if month!=last_month and wi<51:
        p.text(72+wi*20,100,datetime.strptime(d,'%Y-%m-%d').strftime('%b').upper(),10,'#878f99')
        last_month=month
for row,label in [(1,'M'),(3,'W'),(5,'F')]:p.text(40,127+row*19,label,10,'#7d8590')
p.text(40,285,f'{calendar["totalContributions"]} contributions in the last year',12,'#a4abb4')
p.text(945,285,'LESS',10,'#7d8590')
for i,c in enumerate(colors):p.rect(985+i*20,273,14,14,c,2)
p.text(1095,285,'MORE',10,'#7d8590')
p.save('contributions.svg')

p=Panel(365,'ACTIVITY','LAST 30 DAYS')
recent=days[-30:]; maxval=max(1,max(d['contributionCount'] for d in recent))
for j in range(4):
    y=112+j*55;p.path(f'M65 {y}H1150','#22272e');p.text(36,y+4,round(maxval*(3-j)/3),10,'#68717d')
for i,d in enumerate(recent):
    x=73+i*36; n=d['contributionCount']; height=165*n/maxval
    p.rect(x,277-height,22,max(2,height),'#d2d6d9' if n else '#232a33',2)
    if i in (0,7,14,21,29):p.text(x+10,303,d['date'][5:],10,'#858f9b',extra='text-anchor="middle"')
p.text(40,342,f'{sum(d["contributionCount"] for d in recent)} CONTRIBUTIONS',11,'#b2b9c2',extra='letter-spacing="2"')
p.text(1160,342,f'{sum(d["contributionCount"]>0 for d in recent)} ACTIVE DAYS',11,'#858f9b',extra='text-anchor="end" letter-spacing="2"')
p.save('activity.svg')

p=Panel(max(170,120+len(updates[:6])*88),'LATEST UPDATES','PROJECT ACTIVITY')
if not updates:
    p.text(40,119,'No public project updates yet',16,'#929da9')
for i,u in enumerate(updates[:6]):
    y=109+i*88
    p.p.append(f'<a href="{escape(u["url"])}" target="_blank">')
    p.text(40,y,u['date'][:10],11,'#8b95a1')
    p.text(200,y,u['repo'],11,'#8b95a1')
    p.text(1160,y,u['sha'],11,'#8b95a1',extra='text-anchor="end"')
    title=u['title']; title=title if len(title)<83 else title[:80]+'…'
    p.text(40,y+32,title,18,'#d7dce1')
    p.p.append('</a>')
    if i<len(updates[:6])-1:p.path(f'M40 {y+55}H1160','#242a32')
p.save('updates.svg')

shown=projects[:5]
p=Panel(max(170,110+len(shown)*130),'REPOSITORIES','PUBLIC PROJECTS')
if not shown:
    p.text(40,119,'No public projects yet',16,'#929da9')
for i,r in enumerate(shown):
    y=98+i*130
    p.p.append(f'<a href="{escape(r["html_url"])}" target="_blank">')
    p.text(40,y+24,r['name'],25,'#e2e5e8','Georgia,serif')
    desc=r.get('description') or ('Profile artwork and live GitHub dashboard' if r['name']==USER else 'Public repository')
    p.text(40,y+58,desc[:95],13,'#929da9')
    p.text(40,y+89, r['language'] or 'PROFILE',10,'#a6afba',extra='letter-spacing="2"')
    p.text(1160,y+24,f'{r["stargazers_count"]} STARS    {r["forks_count"]} FORKS',11,'#929da9',extra='text-anchor="end"')
    p.p.append('</a>')
p.save('repositories.svg')

p=Panel(125,'MONOLITH','SOFTWARE STUDIO')
p.text(40,104,'github.com/monolithcraft',12,'#b2bac4')

p.save('footer.svg')

readme='''<p align="center">
  <img src="assets/banner.jpg" alt="MONOLITH software studio" width="100%">
</p>

<p align="center">
  <a href="https://github.com/monolithcraft?tab=repositories">Repositories</a>
  &nbsp;&nbsp;/&nbsp;&nbsp;
  <a href="https://github.com/monolithcraft?tab=projects">Projects</a>
  &nbsp;&nbsp;/&nbsp;&nbsp;
  <a href="https://github.com/monolithcraft?tab=overview">Activity</a>
</p>

<p align="center">
  <img src="https://komarev.com/ghpvc/?username=monolithcraft&amp;label=PROFILE+VIEWS&amp;color=555555&amp;style=flat-square" alt="Profile views">
</p>

<img src="assets/overview.svg" width="100%" alt="Public GitHub statistics">

<img src="assets/contributions.svg" width="100%" alt="Contribution calendar for the last 12 months">

<img src="assets/activity.svg" width="100%" alt="Contribution activity over the last 30 days">

<img src="assets/updates.svg" width="100%" alt="Latest commits">

<a href="https://github.com/monolithcraft?tab=repositories"><img src="assets/repositories.svg" width="100%" alt="Public repositories"></a>

<img src="assets/footer.svg" width="100%" alt="Monolith studio">
'''
(ROOT/'README.md').write_text(readme)
# Ensure generated assets are valid XML before any commit
import xml.etree.ElementTree as ET
for name in ['overview','contributions','activity','updates','repositories','footer']:
    ET.parse(OUT/(name+'.svg'))
print('Generated dashboard with',len(updates[:6]),'updates and',len(shown),'repositories')
