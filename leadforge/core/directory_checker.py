from urllib.parse import quote
class DirectoryChecker:
    """Conservative directory discovery. It does not bypass CAPTCHAs or access controls."""
    def __init__(self, search): self.search=search
    def find(self,name,location):
        out={}
        for key,site in (("yelp_url","yelp.com"),("bbb_url","bbb.org"),("google_maps_url","google.com/maps")):
            rs=self.search.ddg(f'"{name}" {location} site:{site}')
            if rs: out[key]=rs[0]["url"]
        return out
