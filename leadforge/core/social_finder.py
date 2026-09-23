from urllib.parse import quote
from .search_engine import SearchEngine

class SocialFinder:
    def __init__(self, search): self.search=search
    def find(self,name,location):
        out={}
        for platform,site in (("facebook","facebook.com"),("instagram","instagram.com"),("linkedin","linkedin.com/company"),("twitter","x.com"),("youtube","youtube.com")):
            for r in self.search.ddg(f'"{name}" {location} site:{site}')[:3]:
                title=r["title"].lower(); target=(name or "").lower().split()
                if any(t in title for t in target[:2]): out[platform]=r["url"]; break
        return out
