from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from .email_extractor import extract_emails
from .phone_extractor import extract_phones
from .constants import CONTACT_WORDS, SOCIAL_HOSTS, hostname
import re, random, time

class WebsiteScraper:
    def __init__(self, http, limiter, max_pages=6): self.http,self.limiter,self.max_pages=http,limiter,max_pages
    def fetch(self,url):
        self.limiter.wait(url); r=self.http.get(url)
        if not r or r.status_code>=400: return None
        if "text/html" not in r.headers.get("content-type",""): return None
        return r.text
    def scrape(self,base):
        seen=[]; queue=[base]; data={"emails":set(),"phones":set(),"socials":{},"description":"","hours":"","addresses":[],"title":"","canonical":"","pages":[]}
        while queue and len(seen)<self.max_pages:
            url=queue.pop(0)
            if url in seen: continue
            seen.append(url); html=self.fetch(url)
            if not html: continue
            soup=BeautifulSoup(html,"lxml")
            data["pages"].append(url)
            if not data["title"] and soup.title: data["title"] = soup.title.get_text(" ",strip=True)
            if not data["canonical"]:
                canon=soup.select_one("link[rel=canonical]")
                data["canonical"] = urljoin(url, canon.get("href")) if canon and canon.get("href") else ""
            for a in soup.select('a[href]'):
                href=urljoin(url,a.get("href","")); h=hostname(href); text=a.get_text(" ",strip=True).lower()
                if href.lower().startswith("mailto:"): data["emails"].update(extract_emails(href[7:]))
                if href.lower().startswith("tel:"): data["phones"].update(extract_phones(href[4:]))
                for key,hosts in SOCIAL_HOSTS.items():
                    if any(h==x or h.endswith("."+x) for x in hosts): data["socials"].setdefault(key,href)
                if h==hostname(base) and any(w in (text+href.lower()) for w in CONTACT_WORDS) and href not in seen and href not in queue: queue.append(href)
            text=soup.get_text(" ",strip=True)
            data["emails"].update(extract_emails(text)); data["phones"].update(extract_phones(text))
            if not data["description"]:
                m=soup.select_one('meta[name="description"]'); data["description"]=(m.get("content","").strip() if m else "")
            for tag in soup.select("address,[itemprop='streetAddress'],[itemprop='addressLocality'],[itemprop='postalCode']"):
                t=tag.get_text(" ",strip=True)
                if t and t not in data["addresses"]: data["addresses"].append(t)
        return data
