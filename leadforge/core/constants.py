import re
from urllib.parse import urlparse

EMAIL_RE = re.compile(r"\b[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+\b")
PHONE_RE = re.compile(r"(?:\+?\d[\d().\-\s]{7,}\d)")
SOCIAL_HOSTS = {
    "facebook": ("facebook.com",),
    "instagram": ("instagram.com",),
    "linkedin": ("linkedin.com",),
    "twitter": ("twitter.com", "x.com"),
    "youtube": ("youtube.com", "youtu.be"),
}
DIRECTORY_HOSTS = {
    "yelp.com", "tripadvisor.com", "facebook.com", "yellowpages.com", "bbb.org",
    "mapquest.com", "linkedin.com", "indeed.com", "manta.com", "superpages.com",
    "chamberofcommerce.com", "foursquare.com", "angi.com", "homeadvisor.com",
    "birdeye.com", "unilocal.co.uk", "bizapedia.com", "mapquest.com"
}
CONTACT_WORDS = ("contact", "contact-us", "about", "about-us", "reach-us", "get-in-touch")
BAD_EMAIL_DOMAINS = {"example.com", "example.org", "test.com", "invalid.com", "localhost"}
EMAIL_PREFIX_PREFERENCE = ("info", "contact", "hello", "office", "sales", "support", "admin")
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 Version/17.6 Safari/605.1.15",
]
ENRICHMENT_COLUMNS = [
    "website_url", "email_primary", "email_all", "phone_primary", "phone_all",
    "facebook_url", "instagram_url", "linkedin_url", "twitter_url", "youtube_url",
    "google_maps_url", "yelp_url", "bbb_url", "business_hours", "description",
    "enrichment_status", "enrichment_notes", "last_enriched",
    "website_confidence", "website_source", "email_source", "phone_source", "social_source",
    "match_components", "match_reason", "candidate_count", "review_required"
]

for _candidate_number in range(1, 6):
    ENRICHMENT_COLUMNS.extend([
        f"candidate_{_candidate_number}_url",
        f"candidate_{_candidate_number}_score",
        f"candidate_{_candidate_number}_reason",
    ])

def hostname(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower().lstrip("www.")
    except Exception:
        return ""
