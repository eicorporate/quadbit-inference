# Handoff Notes (Crash Recovery)

Use this file to quickly brief any AI/helper after a crash so you can resume work immediately.

## Current Workspace
- Path: `/home/ubuntu/jeffrey-torus-inference`
- Active file of interest: `config/master_ingestion_urls.txt` (canonical deduped ingestion seed list)
- Manifesto file: `master_manifesto.md` (consolidated description + seed list)

## Recent Actions
- Reviewed `config/master_ingestion_urls.txt` (lines 1-319) — categorized seed URLs for ingestion.
- Created `master_manifesto.md` consolidating the same list with guidance and next steps.
- No code changes beyond documentation; no pending unstaged edits noted (check `git status` to confirm).

## Known Commands Run Recently
- Checked GitHub Actions run status for `eicorporate/quadbit-inference` (run id 22598162477).
- Verified `avatar_warp.html` size with `wc -c`.
- Misc curl latency check to `aliknows.com` (outside repo path).

## What To Do Next (you can pick any)
1) If continuing ingestion curation: edit `config/master_ingestion_urls.txt` and keep it deduped and categorized.
2) If sharing sources: use `master_manifesto.md` as the handoff artifact; convert to CSV/JSON if needed.
3) If running checks: perform reachability/latency on listed hosts (respect robots.txt and rate limits).
4) If syncing: confirm `git status`; commit `HANDOFF.md` and `master_manifesto.md` if desired.

## Quick Commands (optional)
- Show git status: `git status`
- View seed list head: `head -n 60 config/master_ingestion_urls.txt`
- View manifesto: `less master_manifesto.md`

## System Context
- OS: Linux (per environment info)
- CWD typically: `/home/ubuntu/jeffrey-torus-inference`
- Terminals present: multiple bash sessions.

## Contact Points
- If another AI picks up: read this file first, then inspect `config/master_ingestion_urls.txt` and `master_manifesto.md`.

(Add any new actions you take below to keep the chain of custody clear.)
