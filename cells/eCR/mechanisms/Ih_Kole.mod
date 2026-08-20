TITLE 'Deterministic Ih based on Kole et al. 2006'
: ModelDB 149100 Ih.mod; deterministic HCN candidate.
: Renamed suffix and guarded the removable singularity; no Q10 was added.

NEURON {
    SUFFIX Ih_Kole
    NONSPECIFIC_CURRENT ihcn
    RANGE gIhbar, gIh, ihcn, ehcn
}

UNITS {
    (S) = (siemens)
    (mV) = (millivolt)
    (mA) = (milliamp)
}

PARAMETER {
    gIhbar = 0.00001 (S/cm2)
    ehcn = -45 (mV)
}

ASSIGNED {
    v (mV)
    ihcn (mA/cm2)
    gIh (S/cm2)
    mInf
    mTau (ms)
    mAlpha (1/ms)
    mBeta (1/ms)
}

STATE { m }

BREAKPOINT {
    SOLVE states METHOD cnexp
    gIh = gIhbar*m
    ihcn = gIh*(v - ehcn)
}

DERIVATIVE states {
    rates(v)
    m' = (mInf - m)/mTau
}

INITIAL {
    rates(v)
    m = mInf
}

PROCEDURE rates(v (mV)) {
    UNITSOFF
    if (fabs(v + 154.9) < 1e-6) {
        mAlpha = 0.001*6.43*11.9
    } else {
        mAlpha = 0.001*6.43*(v + 154.9)/(exp((v + 154.9)/11.9) - 1)
    }
    mBeta = 0.001*193*exp(v/33.1)
    mInf = mAlpha/(mAlpha + mBeta)
    mTau = 1/(mAlpha + mBeta)
    UNITSON
}
