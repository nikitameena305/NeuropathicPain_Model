# Shared mechanisms

`medlock_267056/` is the canonical ModelDB-derived mechanism source set used by L796 and L292-E1. The shared `HH2.mod` includes the documented analytic `vtrap` correction for removable rate singularities; kinetics away from the singular points are unchanged.

Compile from inside the canonical directory:

```bash
cd shared/mechanisms/medlock_267056
nrnivmodl
```

L571's `l571_na.mod` and `l571_kdr.mod` are intentionally separate, renamed, fitted variants and remain in the L571 cell package. The six source MOD files in `external/medlock_267056_excitatory_scaffold/mods/` are intentionally retained as an isolated upstream-reproduction snapshot; its uncorrected HH2 variant must not silently replace the canonical corrected file.

See `MANIFEST.txt` for file-level roles and provenance, and `docs/duplicate_file_audit.csv` for justified retained duplicates.

