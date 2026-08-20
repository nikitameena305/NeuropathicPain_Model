TITLE 'Medlock B_DR delayed-rectifier potassium channel'
: ModelDB 267056; Safronov et al. 2000 kinetics.
: Copied without kinetic or temperature-behaviour changes for NMO_260150.

NEURON {
    SUFFIX B_DR
    USEION k READ ek WRITE ik
    RANGE gkbar, ik
    RANGE ninf, ntau, tadj
}

UNITS {
    (mV) = (millivolt)
    (mA) = (milliamp)
}

INDEPENDENT {t FROM 0 TO 1 WITH 1 (ms)}

STATE { n }

ASSIGNED {
    celsius (degC)
    v (mV)
    ek (mV)
    ik (mA/cm2)
    gkbar (mho/cm2)
    tadj (1)
    nalpha (1/ms)
    nbeta (1/ms)
    ninf (1)
    ntau (ms)
}

INITIAL {
    rates(v)
    tadj = 3^((celsius - 23)/10)
    n = ninf
}

BREAKPOINT {
    SOLVE states METHOD cnexp
    ik = gkbar*n*n*n*n*(v - ek)
}

DERIVATIVE states {
    rates(v)
    n' = (ninf - n)/ntau
}

FUNCTION trap(x, y) {
    if (fabs(x/y) < 1e-6) {
        trap = y*(1 - x/y/2)
    } else {
        trap = x/(exp(x/y) - 1)
    }
}

PROCEDURE rates(v (mV)) {
    TABLE ninf, ntau DEPEND celsius FROM -100 TO 100 WITH 200
    nalpha = 0.0075*trap(-v - 30, 10)
    nbeta = 0.1*exp((-v - 46)/31)
    ninf = nalpha/(nalpha + nbeta)
    ntau = 1/(nalpha + nbeta)
}
