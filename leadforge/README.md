# LeadForge — Local Business Enrichment Suite

LeadForge is a Windows-friendly Tkinter desktop application that enriches CSV leads containing a business name and address using publicly available business information.

## What is improved in this version

- Multi-query website discovery rather than trusting the first search result.
- Bing fallback discovery when DuckDuckGo returns no usable results.
- Candidate scoring using business name, locality, address tokens, title and domain.
- Website verification before accepting a domain as official.
- Contact/about page discovery with bounded crawling.
- Public business email extraction only; no SMTP verification or private-email guessing.
- Phone normalization and validation.
- Social/profile discovery with basic business-name/location verification.
- Field-level provenance and confidence columns so results are auditable.
- SQLite cache, checkpoint/resume, retry/backoff, per-host throttling and graceful failure.
- Accuracy-safe turbo defaults: 10 workers with a 0.75-second per-host delay. Increase the delay for stricter source throttling.
- UTF-8 BOM CSV output for Excel.
- Optional API integrations can be added through the settings file without changing the core pipeline.

## Important design change from the original brief

LeadForge does **not** attempt to defeat CAPTCHA, Cloudflare, browser fingerprinting, robots restrictions, or access controls. Proxy rotation is not used to evade a block. If a source cannot be accessed normally, the source is skipped and the row continues. This makes the tool more appropriate for legitimate public-business-data enrichment and reduces the risk of hammering third-party services.

## Install

Python 3.11+ is recommended.

```text
pip install -r requirements.txt
```

## Run

```text
python main.py
```

## Input CSV

The file must contain a company/business name column and an address column. The GUI lets you map the columns.

```csv
business_name,address
Win Win Realty & Property Management,"5115 Spring Mountain Rd #211, Las Vegas, NV 89146"
Example Dental,"123 Main St, Denver, CO 80202"
```

## Output

Original columns are preserved and enrichment columns are appended. Additional audit fields include confidence and provenance.

The run summary reports `Enriched`, `Partial`, `Skipped`, and `Failed` counts. These values also match the `enrichment_status` values written to the output CSV.

## Proxies

A proxy file can be selected for normal network routing. Supported forms are:

```text
host:port
user:pass@host:port
```

Do not use proxies to circumvent access controls or rate limits.

## Optional API keys

`config/settings.json` contains optional provider placeholders. The base application works without paid APIs.

## Resume

LeadForge writes a checkpoint every 10 rows and when a run is stopped. Use **Resume** after restarting the application.

## Accuracy model

The app does not claim that every discovered domain is official. Website matches use graduated confidence tiers: strong matches can flow through automatically, while plausible matches are retained with `review_required=yes`. Each field gets a source and confidence indicator where available. Ambiguous matches are marked `partial` rather than silently presented as verified.

## Troubleshooting

- **No results:** check the spelling and address, then retry with a smaller worker count.
- **Many timeouts:** reduce concurrency and increase delay.
- **Directory blocked:** the affected source is skipped; the rest of the enrichment continues.
- **DNS failures:** email validation will mark the domain as unverifiable rather than claiming the email is bad.
- **Excel encoding:** output uses UTF-8 BOM.

## Legal / compliance note

This tool only enriches publicly available business data. Respect website terms, robots directives, applicable privacy/data-protection law, and source rate limits. Do not use it to send unsolicited email in violation of CAN-SPAM, GDPR, PECR, or other applicable rules.

## Multi-factor entity matching (LeadForge v2)

The enrichment engine does not simply accept the first search result. It ranks multiple candidates using:

- normalized business-name token similarity
- address/location token similarity
- ZIP/postal-code and street-number evidence where available
- domain-to-business-name relevance
- directory-result penalties
- on-site evidence from the candidate website title and discovered address

The top five viable candidates can be inspected before one is accepted. Lower-confidence matches are retained but marked with `review_required=yes` rather than being silently treated as verified.

Candidate scores use graduated handling: scores of 75 or above are accepted without review, while scores from 15 through 74.9 are retained as plausible matches and marked for review. Candidates below 15 are rejected. The top five evaluated candidates are written to `candidate_1_*` through `candidate_5_*` audit columns so rejected or ambiguous results remain inspectable.

Additional output columns:

- `website_confidence`
- `website_source`
- `match_components`
- `match_reason`
- `candidate_count`
- `review_required`
- `candidate_1_url` through `candidate_5_url`
- `candidate_1_score` through `candidate_5_score`
- `candidate_1_reason` through `candidate_5_reason`

This creates a practical review queue for ambiguous businesses while allowing strong matches to flow through automatically.
