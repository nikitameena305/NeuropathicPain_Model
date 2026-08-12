TITLE L571 fast sodium current derived from Medlock B_Na

COMMENT
Minimal fast sodium current for the L571 model. Voltage-dependent rates are
from ModelDB 267056 B_NA.mod (Medlock et al. 2022), which cites the dorsal-horn
model of Melnick et al. The source computes a Q10 term but does not apply it.
This version makes the temperature factor explicit and configuration-driven.
It is a model-derived assumption, not an L571-specific measurement.
ENDCOMMENT

NEURON {
    SUFFIX l571_na
    USEION na READ ena WRITE ina
    RANGE gnabar, ina, alpha_shift, beta_shift, tau_factor
    RANGE q10, tref, temperature_scaling, m_inf, h_inf, tau_m, tau_h, tadj
}

UNITS {
    (mA) = (milliamp)
    (mV) = (millivolt)
}

PARAMETER {
    gnabar = 0 (mho/cm2) <0, 1e9>
    alpha_shift = 0 (mV)
    beta_shift = 0 (mV)
    tau_factor = 1 <1e-9, 1e9>
    q10 = 3 <1, 10>
    tref = 23 (degC)
    temperature_scaling = 1 <0, 1>
}

STATE {
    m h
}

ASSIGNED {
    celsius (degC)
    v (mV)
    ena (mV)
    ina (mA/cm2)
    m_inf (1)
    h_inf (1)
    tau_m (ms)
    tau_h (ms)
    tadj (1)
}

INITIAL {
    rates(v)
    m = m_inf
    h = h_inf
}

BREAKPOINT {
    SOLVE states METHOD cnexp
    ina = gnabar*m*m*m*h*(v - ena)
}

DERIVATIVE states {
    rates(v)
    m' = (m_inf - m)/tau_m
    h' = (h_inf - h)/tau_h
}

PROCEDURE rates(v (mV)) {
    LOCAL am, bm, ah, bh
    if (temperature_scaling > 0.5) {
        tadj = q10^((celsius - tref)/10)
    } else {
        tadj = 1
    }
    am = 0.182*trap(-v + 7 - 35 + alpha_shift, 9)
    bm = 0.124*trap(v - 7 + 35 + beta_shift, 9)
    ah = 0.061*trap(-v + 13 - 48 + alpha_shift, 3) + 0.0166
    bh = 0.0018*trap(v - 13 + 84 + beta_shift, 18)
    m_inf = am/(am + bm)
    h_inf = 1/(1 + exp((v + 75 - 11)/9))
    tau_m = 1/(am + bm)/(tadj*tau_factor)
    tau_h = 1/(ah + bh)/(tadj*tau_factor)
}

FUNCTION trap(x (mV), y (mV)) (mV) {
    if (fabs(x/y) < 1e-6) {
        trap = y*(1 - x/y/2)
    } else {
        trap = x/(exp(x/y) - 1)
    }
}
