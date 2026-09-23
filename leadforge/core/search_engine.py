from bs4 import BeautifulSoup
from urllib.parse import quote, unquote
import re
from .constants import DIRECTORY_HOSTS, USER_AGENTS, hostname
from .entity_matcher import rank_candidates
import random, time
try:
    from curl_cffi import requests as cffi_requests
except Exception:
    cffi_requests=None
import requests

class SearchEngine:
    def __init__(self, limiter, timeout=15): self.limiter,self.timeout=limiter,timeout
    def get(self,url):
        self.limiter.wait(url); headers={"User-Agent":random.choice(USER_AGENTS),"Accept-Language":"en-US,en;q=0.9"}
        for attempt in range(3):
            try:
                if cffi_requests: return cffi_requests.get(url,headers=headers,timeout=self.timeout,impersonate="chrome124")
                return requests.get(url,headers=headers,timeout=self.timeout)
            except Exception:
                if attempt<2: time.sleep((2,8,32)[attempt])
        return None
    def ddg(self,q):
        r=self.get("https://html.duckduckgo.com/html/?q="+quote(q)); results=[]
        if not r or r.status_code>=400: return results
        soup=BeautifulSoup(r.text,"lxml")
        for item in soup.select('.result')[:12]:
            a=item.select_one('a.result__a')
            if not a: continue
            href=a.get('href',''); title=a.get_text(' ',strip=True)
            snippet=(item.select_one('.result__snippet').get_text(' ',strip=True) if item.select_one('.result__snippet') else '')
            if href and href.startswith('http'):
                results.append({'url':href,'title':title,'snippet':snippet})
        return results
    def bing(self,q):
        r=self.get("https://www.bing.com/search?q="+quote(q)); results=[]
        if not r or r.status_code>=400: return results
        soup=BeautifulSoup(r.text,"lxml")
        for item in soup.select("li.b_algo")[:12]:
            a=item.select_one("h2 a")
            if not a: continue
            href=a.get("href","")
            snippet=item.select_one(".b_caption p") or item.select_one("p")
            if href.startswith("http"):
                results.append({
                    "url":href,
                    "title":a.get_text(" ",strip=True),
                    "snippet":snippet.get_text(" ",strip=True) if snippet else "",
                })
        return results
    def yahoo(self,q):
        r=self.get("https://search.yahoo.com/search?p="+quote(q)); results=[]
        if not r or r.status_code>=400: return results
        soup=BeautifulSoup(r.text,"lxml")
        for item in soup.select("div#web ol li")[:12]:
            link=None
            for anchor in item.select("a[href]"):
                href=anchor.get("href","")
                if "r.search.yahoo.com/" in href:
                    match=re.search(r"/RU=([^&]+)", href)
                    if match:
                        link=unquote(match.group(1)).split("/RK=", 1)[0]
                        break
            if not link or not link.startswith("http"): continue
            title_anchor=item.select_one("a[href]")
            title=title_anchor.get_text(" ",strip=True) if title_anchor else item.get_text(" ",strip=True)
            snippet=item.get_text(" ",strip=True)
            results.append({"url":link,"title":title,"snippet":snippet})
        return results
    def search(self,name,location):
        queries=[f'"{name}" "{location}"', f'"{name}" {location}', f'{name} {location} official website']
        results=[]
        for q in queries:
            got=self.ddg(q)
            results.extend(got)
            if len(results)>=20: break
        if not results:
            for q in queries:
                results.extend(self.yahoo(q))
                if len(results)>=20: break
        if not results:
            for q in queries:
                results.extend(self.bing(q))
                if len(results)>=20: break
        return rank_candidates(name,location,results)
