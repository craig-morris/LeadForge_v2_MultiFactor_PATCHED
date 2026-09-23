import re
from .constants import PHONE_RE

def normalize_phone(raw):
    s=re.sub(r"[^0-9+]", "", raw or "")
    if s.startswith("00"): s="+"+s[2:]
    if len(re.sub(r"\D","",s)) < 8: return ""
    return s

def extract_phones(text):
    out=[]
    for raw in PHONE_RE.findall(text or ""):
        p=normalize_phone(raw)
        if p and p not in out: out.append(p)
    return out
