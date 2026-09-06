# Capital Flow → Career Capital Intelligence — v5 Zero-Cost

A zero-recurring-cost architecture for the capital-flow/career intelligence dashboard.

## Design constraint

**No paid database, no paid server, no paid scheduler, no required API subscription.**

The project owns its canonical data as append-only JSON/JSONL files in the repository. A local SQLite database is rebuilt deterministically from those files for analysis, validation and backup. The browser reads generated static JSON. GitHub Actions performs scheduled refreshes and GitHub Pages can host `docs/` for free when the repository is public.

## Architecture

```text
Official/public sources
        ↓
GitHub Actions scheduled Python collector
        ↓
append-only owned evidence files (JSONL)
        ↓
rebuildable SQLite database
        ↓
validated static JSON projections
        ↓
GitHub Pages static dashboard
```

There is no runtime backend. Opening the dashboard does not execute a server function and does not incur per-request database costs.

## What persists

- `data/observations/*.jsonl` — immutable structured observations and revisions
- `data/discoveries/*.jsonl` — discovered report links
- `data/source_state.json` — fetch fingerprints, ETags, last success/error
- `data/reviews.json` — review lifecycle
- `data/run_log.jsonl` — ingestion audit log
- `data/snapshots/*.json` — validated recommendation snapshots
- `config/sources.json` — source registry

`build/intelligence.sqlite` is generated from these canonical files. It is intentionally not the persistence mechanism, so the project remains portable and Git-friendly.

## Local use

```bash
python scripts/build_site.py
python scripts/build_standalone.py
python -m unittest discover -s tests -v
python scripts/local_server.py
```

Open `http://127.0.0.1:8000`.

## Free deployment

1. Use a public GitHub repository.
2. In **Settings → Pages**, set **Source = GitHub Actions**.
3. The `Deploy dashboard` workflow builds, tests and deploys the static site on `main`.
4. The daily `Refresh intelligence data` workflow checks sources whose cadence is due, updates owned evidence files, rebuilds/tests the projections, commits the audit trail, and deploys the current site.

No domain purchase is required; GitHub Pages provides a `github.io` URL.

## Privacy

The tracked evidence is public market/labor information. Do not put personal profile data or private credentials into the repository. Personal-fit controls remain browser-local. If a future free API needs a token, use GitHub encrypted repository secrets and never write the token into files or logs.

## Why text files + SQLite instead of a hosted DB?

A committed SQLite file is easy initially but produces poor Git history as the binary changes repeatedly. The canonical append-only text store is diffable, auditable and portable. SQLite remains available as a real relational database, but it is regenerated from the source-of-truth files whenever required.
