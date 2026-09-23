import re
import dns.resolver
from .constants import EMAIL_RE, BAD_EMAIL_DOMAINS, EMAIL_PREFIX_PREFERENCE

def extract_emails(text):
    return sorted(set(x.lower().strip(".,;:()[]<>") for x in EMAIL_RE.findall(text or "")))

def valid_public_email(email):
    if not EMAIL_RE.fullmatch(email or ""): return False
    domain=email.rsplit("@",1)[-1].lower()
    if domain in BAD_EMAIL_DOMAINS: return False
    try:
        dns.resolver.resolve(domain,"MX",lifetime=3)
        return True
    except Exception:
        return False

def choose_primary(emails):
    good=[e for e in emails if valid_public_email(e)]
    for prefix in EMAIL_PREFIX_PREFERENCE:
        for e in good:
            if e.split("@",1)[0].lower()==prefix: return e
    return good[0] if good else (emails[0] if emails else "")
