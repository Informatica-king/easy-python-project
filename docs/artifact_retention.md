# Artifact retention (PDF / Releases)

## Why

Analysis PDFs were being **double-stored**:

1. Force-committed into git (`assets/` + `reports/`)
2. Uploaded to GitHub Releases

Binary PDFs bloat git history permanently. The owner also **saves each PDF to phone local storage**, so GitHub is only a convenience re-download channel — not the archive of record.

## Policy

| Artifact | Git | GitHub Release | Phone |
|----------|-----|----------------|-------|
| PDF (anal / deep / econ / rev) | ❌ do not commit | ✅ upload; then retention prune | ✅ owner keeps local |
| Generator `.py` | ✅ | — | — |
| `chase_rr_*.json`, `ta_*.csv` | ✅ (small) | optional | — |
| HTML / chart PNG | ❌ (regenerate) | — | — |

Retention numbers live in `config/artifact_retention.yaml`.

## Agent rules

After generating a PDF:

1. Copy to `/opt/cursor/artifacts` (Cursor UI)
2. `sepa.artifacts.publish_github_release_asset(...)` (or `gh release create/upload`)
3. Paste the **release download URL** in chat
4. **Do not** `git add -f` any `*.pdf`

## Cleanup CLI

```bash
# dry-run (default)
.venv/bin/python -m sepa.cleanup_artifacts
.venv/bin/python -m sepa.cleanup_artifacts releases
.venv/bin/python -m sepa.cleanup_artifacts git-index
.venv/bin/python -m sepa.cleanup_artifacts dupes

# apply (destructive for releases / git index only)
.venv/bin/python -m sepa.cleanup_artifacts releases --apply --yes
.venv/bin/python -m sepa.cleanup_artifacts git-index --apply --yes
```

`git-index --apply` runs `git rm --cached` (files stay on disk).  
History rewrite (`git filter-repo`) is **out of scope** until the repo is much larger.

## Related

- `src/sepa/artifacts.py` — publish helpers
- `docs/korean_commands.md` — command contract + artifact note
