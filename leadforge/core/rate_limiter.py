import threading, time, random
from urllib.parse import urlparse

class RateLimiter:
    def __init__(self, delay=2.0):
        self.delay=float(delay); self.last={}; self.lock=threading.Lock()
    def wait(self,url):
        host=(urlparse(url).hostname or "").lower()
        with self.lock:
            elapsed=time.time()-self.last.get(host,0)
            wait=max(0,self.delay-elapsed)
            if wait: time.sleep(wait)
            self.last[host]=time.time()+random.uniform(0,.25)
