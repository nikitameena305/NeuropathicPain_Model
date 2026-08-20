TITLE L571 delayed rectifier potassium current derived from Medlock KDRI

COMMENT
Minimal delayed-rectifier current for the L571 model. Rates and n^4*h gating
come from ModelDB 267056 KDRI.mod (Medlock et al. 2022). The source contains a
commented-out Q10=3 correction. This version exposes that correction explicitly
for the separately labelled 35 C translation. It is model-derived, not an
L571-specific experimental measurement.
ENDCOMMENT

NEURON {
    SUFFIX l571_kdr
    USEION k READ ek WRITE ik
    RANGE gkbar, ik, q10, tref, temperature_scaling
    RANGE n_inf, h_inf, tau_n, tau_h, tadj
}

UNITS {
    (mA) = (milliamp)
    (mV) = (millivolt)
}

PARAMETER {
    gkbar = 0 (mho/cm2) <0, 1e9>
    q10 = 3 <1, 10>
    tref = 23 (degC)
    temperature_scaling = 1 <0, 1>
}

STATE {
    n h
}

ASSIGNED {
    celsius (degC)
    v (mV)
    ek (mV)
    ik (mA/cm2)
    n_inf (1)
    h_inf (1)
    tau_n (ms)
    tau_h (ms)
    tadj (1)
}

INITIAL {
    rates(v)
    n = n_inf
    h = h_inf
}

BREAKPOINT {
    SOLVE states METHOD cnexp
    ik = gkbar*n*n*n*n*h*(v - ek)
}

DERIVATIVE states {
    rates(v)
    n' = (n_inf - n)/tau_n
    h' = (h_inf - h)/tau_h
}

PROCEDURE rates(v (mV)) {
    LOCAL an, bn, ah, bh
    if (temperature_scaling > 0.5) {
        tadj = q10^((celsius - tref)/10)
    } else {
        tadj = 1
    }
    an = 0.035*exp_m1(-v - 15, 9)
    bn = 0.014*exp((-v + 12)/46)
    ah = 0.0083*(1/(exp((v + 20)/10) + 1) + 1)
    bh = 0.0083/(exp((-v - 20)/10) + 1)
    n_inf = an/(an + bn)
    h_inf = ah/(ah + bh)
    tau_n = 1/(an + bn)/tadj
    tau_h = 1/(ah + bh)/tadj
}

FUNCTION exp_m1(x (mV), y (mV)) (mV) {
    if (fabs(x/y) < 1e-6) {
        exp_m1 = y*(1 - x/y/2)
    } else {
        exp_m1 = x/(exp(x/y) - 1)
    }
}
