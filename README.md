# Michigan Accountability Tracker

Evidence-first, nonpartisan tracker for Michigan legislative activity. **Prototype, not a verified live dataset.** Legislative acts and sponsorships are not proof of campaign promise fulfillment or political intent.

## Run locally

Python 3.10+; no third-party dependencies, payment or API keys.

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m mi_tracker --per-page 10 --max-pages 1
python -m http.server 8000 --directory docs
```

Open http://localhost:8000. A sample sweep requests up to 10 bills plus five categories of subresources from [Bill Commons](https://billcommons.org/docs/api). Results are persisted locally in SQLite, with a static export at `docs/data/bills.json`.

## GitHub Actions and Pages

The workflow runs Mondays 09:21 UTC and supports manual dispatch. To publish the website, go to **Settings → Pages → Deploy from a branch → main → /docs**. The job requires `contents: write` to commit new public JSON snapshots. Review the first workflow run for API compatibility and sample quality.

## Evidence principles

- Record introduced bills even when they never pass.
- Distinguish sponsor, cosponsor, vote, bill text and legislative action.
- Show original citations and ingestion health.
- Treat absence of a record as unknown coverage.
- Avoid assigning intent, ideological labels or promise scores without independently validated evidence.
- Respect public sources' access restrictions, rate limits and robots rules.

## Current limitations

- **Live API ingestion and Michigan completeness are not yet verified.** The sample workflow is an experiment, not a production pipeline.
- Actual endpoint shapes and fields may differ from the collector assumptions. Errors should be surfaced and corrected, never silently interpreted as no evidence.
- Only the first 10 bills are sampled; this is not an inventory of legislators or legislative activity.
- Governors, budgets, directed-spending disclosures, amendments, campaign quotes and federal races are future work.
- Cross-check at least five bills against [official Michigan legislative records](https://www.legislature.mi.gov/) before reporting validated coverage.

Resources: [Bill Commons](https://billcommons.org/methodology), [Open States](https://open.pluralpolicy.com/data/), [Michigan Legislature](https://www.legislature.mi.gov/).

MIT licensed.
