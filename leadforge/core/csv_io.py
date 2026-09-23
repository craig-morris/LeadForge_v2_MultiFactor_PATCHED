import csv, os
from .constants import ENRICHMENT_COLUMNS

def read_csv(path):
    with open(path,"r",encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f)); fields=list(rows[0].keys()) if rows else []
    return fields, rows

def write_csv(path, fields, rows):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    out_fields=list(fields)
    for c in ENRICHMENT_COLUMNS:
        if c not in out_fields: out_fields.append(c)
    with open(path,"w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=out_fields,extrasaction="ignore"); w.writeheader(); w.writerows(rows)

def guess_columns(fields):
    def pick(words):
        for f in fields:
            x=f.lower().replace("_"," ")
            if any(w in x for w in words): return f
        return fields[0] if fields else ""
    return pick(("business","company","name")), pick(("address","location","street"))
