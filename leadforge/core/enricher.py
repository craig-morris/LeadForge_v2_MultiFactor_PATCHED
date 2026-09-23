from datetime import datetime, timezone
from urllib.parse import urlparse
from .email_extractor import choose_primary
from .entity_matcher import name_similarity, address_similarity

REVIEW_SCORE_FLOOR = 15
HIGH_CONFIDENCE_SCORE = 75
CACHE_VERSION = "matching-v5"

class Enricher:
    def __init__(self, search, scraper, socials, directories, cache, checkpoint=None, logger=None):
        self.search,self.scraper,self.socials,self.directories=search,scraper,socials,directories
        self.cache,self.checkpoint,self.logger=cache,checkpoint,logger
    def log(self,msg,level="info"):
        if self.logger: self.logger(msg,level)
    def _empty(self,now):
        cols=["website_url","email_primary","email_all","phone_primary","phone_all","facebook_url","instagram_url","linkedin_url","twitter_url","youtube_url","google_maps_url","yelp_url","bbb_url","business_hours","description","enrichment_status","enrichment_notes","last_enriched","website_confidence","website_source","email_source","phone_source","social_source","match_components","match_reason","candidate_count","review_required"]
        for candidate_number in range(1, 6):
            cols.extend([
                f"candidate_{candidate_number}_url",
                f"candidate_{candidate_number}_score",
                f"candidate_{candidate_number}_reason",
            ])
        return {k:"" for k in cols} | {"last_enriched":now}
    def enrich(self,row,name_col,address_col,scope):
        name=(row.get(name_col) or "").strip(); address=(row.get(address_col) or "").strip(); now=datetime.now(timezone.utc).isoformat()
        cached=self.cache.get(f"{CACHE_VERSION}:{name}",address)
        if cached:
            if cached.get("enrichment_status") == "success":
                cached["enrichment_status"] = "enriched"
            return {**row,**cached}
        out=self._empty(now); notes=[]; found=False
        try:
            candidates=self.search.search(name,address) if scope.get("website",True) else []
            out["candidate_count"]=str(len(candidates))
            chosen=None; chosen_data=None; chosen_score=0
            evaluated=[]
            for cand in candidates[:5]:
                if cand.get("score",0)<REVIEW_SCORE_FLOOR: continue
                parsed=urlparse(cand["url"].split('#',1)[0])
                if not parsed.netloc: continue
                base=f"{parsed.scheme or 'https'}://{parsed.netloc}/"
                data=self.scraper.scrape(base)
                ns=name_similarity(name,data.get("title",""))
                ads=address_similarity(address," ".join(data.get("addresses",[])))
                evidence=ns*55+ads*45
                reasons=list(cand.get("reasons",[]))
                if ns>=.55: reasons.append("website title supports business name")
                if ads>=.55: reasons.append("website address supports business location")
                has_site_evidence=bool(data.get("title") or data.get("addresses"))
                combined=min(100, cand.get("score",0)*.65+evidence*.35) if has_site_evidence else cand.get("score",0)
                evaluated.append({**cand, "score": round(combined, 1), "reasons": reasons})
                if combined>chosen_score: chosen,chosen_data,chosen_score=evaluated[-1],data,combined
                if combined>=82 and (ns>=.55 or ads>=.55): break
            for candidate_number, candidate in enumerate(evaluated, 1):
                out[f"candidate_{candidate_number}_url"] = candidate.get("url", "")
                out[f"candidate_{candidate_number}_score"] = str(candidate["score"])
                out[f"candidate_{candidate_number}_reason"] = "; ".join(candidate.get("reasons", []))
            if chosen and chosen_score>=REVIEW_SCORE_FLOOR:
                parsed=urlparse(chosen["url"]); base=f"{parsed.scheme or 'https'}://{parsed.netloc}/"
                out["website_url"]=base; out["website_confidence"]=str(round(chosen_score,1)); out["website_source"]=chosen.get("url","")
                comp=chosen.get("components",{}); out["match_components"]=f"name={comp.get('name',0)}; address={comp.get('address',0)}; domain={comp.get('domain',0)}"
                out["match_reason"]="; ".join(chosen.get("reasons",[])) or "multi-factor candidate match"
                out["review_required"]="yes" if chosen_score<HIGH_CONFIDENCE_SCORE else "no"
                if chosen_score<HIGH_CONFIDENCE_SCORE: notes.append("Website match is plausible but should be manually reviewed")
                data=chosen_data or {}; emails=sorted(data.get("emails",set())); phones=sorted(data.get("phones",set()))
                out["email_all"]="; ".join(emails); out["email_primary"]=choose_primary(emails); out["email_source"]=base if emails else ""
                out["phone_all"]="; ".join(phones); out["phone_primary"]=phones[0] if phones else ""; out["phone_source"]=base if phones else ""
                out["description"]=data.get("description","")
                for k,v in data.get("socials",{}).items(): out[k+"_url"]=v
                found=True
            else:
                notes.append("No website candidate was discovered" if not candidates else "No candidate passed the multi-factor website match threshold")
                out["review_required"]="yes" if candidates else "no"
            if scope.get("socials",True):
                sf=self.socials.find(name,address)
                for k,v in sf.items():
                    if not out.get(k+"_url"): out[k+"_url"]=v
                if sf: out["social_source"]="search"
            if scope.get("directories",True):
                for k,v in self.directories.find(name,address).items():
                    if v: out[k]=v
            out["enrichment_status"]="enriched" if found else "partial"
        except Exception as e:
            notes.append(type(e).__name__+": "+str(e)); out["enrichment_status"]="partial" if found else "failed"
        out["enrichment_notes"]="; ".join(notes)
        self.cache.set(f"{CACHE_VERSION}:{name}",address,out)
        return {**row,**out}
