"""Deterministic business/entity matching for company-name + address enrichment.

No LLM or opaque score is required: the matcher combines normalized name tokens,
address tokens, domain relevance, and evidence discovered on the candidate site.
"""
import re
from urllib.parse import urlparse
from .constants import DIRECTORY_HOSTS, hostname

STOPWORDS = {
    'the','and','of','a','an','inc','incorporated','llc','ltd','limited','co','company',
    'corp','corporation','pllc','pc','llp','group','services','service','solutions'
}
UNIT_WORDS = {'apt','suite','ste','unit','floor','fl','room','rm','#'}
STATE_NAMES = {
    'alabama':'al','alaska':'ak','arizona':'az','arkansas':'ar','california':'ca','colorado':'co',
    'connecticut':'ct','delaware':'de','florida':'fl','georgia':'ga','hawaii':'hi','idaho':'id',
    'illinois':'il','indiana':'in','iowa':'ia','kansas':'ks','kentucky':'ky','louisiana':'la',
    'maine':'me','maryland':'md','massachusetts':'ma','michigan':'mi','minnesota':'mn','mississippi':'ms',
    'missouri':'mo','montana':'mt','nebraska':'ne','nevada':'nv','new hampshire':'nh','new jersey':'nj',
    'new mexico':'nm','new york':'ny','north carolina':'nc','north dakota':'nd','ohio':'oh','oklahoma':'ok',
    'oregon':'or','pennsylvania':'pa','rhode island':'ri','south carolina':'sc','south dakota':'sd',
    'tennessee':'tn','texas':'tx','utah':'ut','vermont':'vt','virginia':'va','washington':'wa',
    'west virginia':'wv','wisconsin':'wi','wyoming':'wy','district of columbia':'dc'
}

def normalize(s):
    s=(s or '').lower().replace('&',' and ')
    s=re.sub(r'[^a-z0-9\s]',' ',s)
    return re.sub(r'\s+',' ',s).strip()

def tokens(s, stop=True):
    out=normalize(s).split()
    return [x for x in out if len(x)>1 and (not stop or x not in STOPWORDS)]

def compact(s): return ''.join(tokens(s, stop=False))

def jaccard(a,b):
    a,b=set(a),set(b)
    return len(a&b)/len(a|b) if a and b else 0.0

def address_parts(s):
    n=normalize(s)
    for full,abbr in STATE_NAMES.items(): n=n.replace(full,abbr)
    nums=re.findall(r'\b\d{5}(?:-\d{4})?\b', n)
    return {
        'tokens': set(tokens(n, stop=False)),
        'zip': nums[0][:5] if nums else '',
        'number': re.search(r'\b\d+\b',n).group(0) if re.search(r'\b\d+\b',n) else '',
    }

def name_similarity(a,b):
    ta,tb=tokens(a),tokens(b)
    if not ta or not tb: return 0
    jac=jaccard(ta,tb)
    ca,cb=compact(a),compact(b)
    containment=1 if (ca and (ca in cb or cb in ca)) else 0
    return min(1.0, jac*0.75+containment*0.25)

def address_similarity(a,b):
    pa,pb=address_parts(a),address_parts(b)
    tok=jaccard(pa['tokens'],pb['tokens'])
    zip_score=1 if pa['zip'] and pa['zip']==pb['zip'] else 0
    num_score=1 if pa['number'] and pa['number']==pb['number'] else 0
    return min(1.0, tok*0.65+zip_score*0.25+num_score*0.10)

def domain_score(url, name):
    h=hostname(url)
    if not h or any(h==d or h.endswith('.'+d) for d in DIRECTORY_HOSTS): return 0.0
    stem=h.split('.')[0]
    ncompact=compact(name)
    if stem and ncompact and stem in ncompact or ncompact and ncompact in stem: return 1.0
    nt=tokens(name)
    dt=tokens(stem.replace('-',' '))
    token_overlap=jaccard(nt,dt)
    partial_overlap=any(len(token)>=4 and (token in stem or stem in token) for token in nt)
    return max(token_overlap, 0.5 if partial_overlap else 0.0)

def candidate_score(name,address,candidate):
    title=candidate.get('title','')
    url=candidate.get('url','')
    snippet=candidate.get('snippet','')
    text=' '.join([title,url,snippet])
    ns=name_similarity(name,title+' '+url)
    # Search snippets often contain the physical location; reward it but never require it.
    ad=address_similarity(address,text)
    ds=domain_score(url,name)
    directory=any((hostname(url)==d or hostname(url).endswith('.'+d)) for d in DIRECTORY_HOSTS)
    score=(ns*55)+(ad*25)+(ds*20)
    if directory: score*=0.45
    reasons=[]
    if ns>=.75: reasons.append('strong name match')
    elif ns>=.45: reasons.append('partial name match')
    if ad>=.75: reasons.append('strong address/location match')
    elif ad>=.4: reasons.append('partial address/location match')
    if ds>=.75: reasons.append('domain matches business name')
    elif ds>=.35: reasons.append('domain partially matches name')
    if directory: reasons.append('directory result')
    return round(min(100,score),1), reasons, {'name':round(ns*100,1),'address':round(ad*100,1),'domain':round(ds*100,1)}

def rank_candidates(name,address,candidates):
    ranked=[]
    seen=set()
    for c in candidates:
        u=(c.get('url') or '').split('#',1)[0]
        h=hostname(u)
        if not h or h in seen: continue
        seen.add(h)
        s,r,components=candidate_score(name,address,c)
        ranked.append({**c,'score':s,'reasons':r,'components':components})
    return sorted(ranked,key=lambda x:x['score'],reverse=True)
