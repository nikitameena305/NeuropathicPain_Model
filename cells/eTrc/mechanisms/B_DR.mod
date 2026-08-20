TITLE HH k channel channel
: Hodgkin - Huxley k channel

: The model used in Safronov et al. 2000 

NEURON {
	SUFFIX B_DR
	USEION k READ ek WRITE ik
	RANGE gkbar, ik
	RANGE ninf, ntau
	RANGE tadj
}

UNITS {
	(mV) = (millivolt)
	(mA) = (milliamp)
}

INDEPENDENT {t FROM 0 TO 1 WITH 1 (ms)}

STATE {
	n
}

PARAMETER {
	ek = -84 (mV)
}

ASSIGNED {
	celsius (degC)
	v (mV)
	ik (mA/cm2)
:	ek (mV): -84 mV

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

DERIVATIVE states{
	rates(v)
	n' = (ninf-n)/ntau
}

:catch 0 in denominator
FUNCTION trap(x,y) {
    if (fabs(x/y) < 1e-6) {
            trap = y*(1 - x/y/2)
    }else{
            trap = x/(exp(x/y) - 1)
    }
}

PROCEDURE rates(v) {
	TABLE ninf, ntau DEPEND celsius FROM -100 TO 100 WITH 200
	nalpha = .0075*trap(-v - 30, 10)
	nbeta = .1*exp((-v - 46)/31)
	ninf = nalpha / (nalpha + nbeta)
	ntau = 1/(nalpha + nbeta)
}