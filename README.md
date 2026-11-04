# Michigan Accountability Tracker

Evidence-first, nonpartisan tracker for Michigan legislative activity. **Prototype, not a verified live dataset.** Records are not endorsements or evidence of campaign-promise fulfillment.

## Run

Requires Python 3.10+; no third-party packages, keys or fees.

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m mi_tracker --per-page 10 --max-pages 1
python -m http.server 8000 --directory docs
```

Open http://localhost:8000. The trial run requests up to 10 bills and five subresources per bill from the [Bill Commons public API](https://billcommons.org/docs/api). Data is stored locally in SQLite and published in `docs/data/bills.json`.

## Limitations

- **Live ingestion is unverified** until the first GitHub Action succeeds and sample results are compared against [official Michigan legislative records](https://www.legislature.mi.gov/).
- The 10-bill sample is not a complete legislative inventory. Missing data is **unknown**, never evidence of no activity.
- Sponsorship, proposed bills and voting evidence are indexed without inferring motives, ideology or political promises.
- The workflow runs weekly and supports manual execution. Publish Pages from `main` / `docs` in repository Settings.
- Campaign statements, governors, budgets and nationwide elections remain future milestones.

Sources and methodology: [Bill Commons](https://billcommons.org/methodology), [Open States](https://open.pluralpolicy.com/data/), [Michigan Legislature](https://www.legislature.mi.gov/).

## Acceptance criteria

Run collector successfully in GitHub Actions, validate five distinct records against official Michigan source, verify bill sponsorship and versions, then expand coverage. Log source mismatches rather than silently treating a blank field as absent activity.

MIT licensed. No CAPTCHA bypass or rate-limit evasion.
