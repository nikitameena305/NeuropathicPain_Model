# Repository audit before cleanup

This manifest captures the untouched tracked state of `origin/main` before any file move or deletion.
The cleanup branch was created first. SHA-256 values are file-content hashes; the one broken Git-link
entry is the SHA-256 of its unavailable Git object ID and is labelled explicitly.

- Tracked entries: 525
- Total regular-file bytes: 225279520
- External uncommitted model work is audited separately before import.

## Planned decisions

- `delete`: 3
- `delete if canonical source retained`: 2
- `delete/replace with provenance note`: 1
- `keep/update`: 2
- `move`: 290
- `move/archive`: 227

## Important safeguards

- L796 scientific outputs and failed/diagnostic experiments are retained and moved as a unit.
- Early circuit, ModelDB, morphology-screening, and submission work is archived, not discarded.
- Zero-byte junk and editor backups are the only ordinary-file deletion candidates at this stage.
- L292-E1-LCN, L571-LCN, the separate GRP morphology set, and the Medlock scaffold are imported only after a separate source audit.

## Complete manifest

The complete per-file audit is in `repository_audit_before_cleanup.csv`.
