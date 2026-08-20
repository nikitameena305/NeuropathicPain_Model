# Mechanism manifest

No MOD file is duplicated in this cell directory.

The active model reuses the already-audited project mechanisms:

- `cells/L571_inhibitory_interneuron/mechanisms/l571_na.mod`
- `cells/L571_inhibitory_interneuron/mechanisms/l571_kdr.mod`

These mechanisms preserve rate equations adapted from Medlock et al. ModelDB accession 267056 while exposing reference temperature and Q10 controls. Reuse is limited to kinetic equations. NMO_170087 densities and compartment distributions are independently fitted and are not inherited from L571.

The Cell 1 model records this cross-cell code dependency in its final parameter JSON and report. NMODL build products (`x86_64/`) are ignored and are not committed.
