TITLE HH k channel channel
: Hodgkin - Huxley k channel

: The model used in Safronov et al. 2000 
: move gkbar and ek from ASSIGNED to PARAMETER (K. Sekiguchi 16thMay20)

NEURON {
	SUFFIX B_A
	USEION k READ ek WRITE ik
	RANGE gkbar, ik
	RANGE ninf, ntau, hinf, htau
	RANGE tadj
}

UNITS {
	(mA) = (milliamp)
	(mV) = (millivolt)
}

INDEPENDENT {t FROM 0 TO 1 WITH 1 (ms)}

STATE {
	n h
}

PARAMETER {
	ek = -84 (mV)
	gkbar (mho/cm2)
}

ASSIGNED {
	celsius (degC)
	v (mV)
	ik (mA/cm2)
:	ek (mV): -84 mV

:	gkbar (mho/cm2)
	tadj (1)

	nalpha (1/ms)
	nbeta (1/ms)
	ninf (1)
	ntau (ms)

	halpha (1/ms)
	hbeta (1/ms)
	hinf (1)
	htau (ms)
}

INITIAL {
	tadj = 3 ^ ((celsius - 23) / 10)
	rates(v)
	n = ninf
	h = hinf
}

BREAKPOINT {
	SOLVE states METHOD cnexp
	ik = gkbar*n*n*n*n*h*(v - ek)
}

DERIVATIVE states{
	rates(v)
	n' = (ninf-n)/ntau
	h' = (hinf-h)/htau
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
	TABLE ninf, ntau, hinf, htau DEPEND tadj FROM -100 TO 100 WITH 200

	nalpha = 0.032 * trap(-v - 64 - 0 , 6)
	nbeta  = 0.203 * exp((-v - 40 - 0)/24)
	ninf = nalpha / (nalpha + nbeta)
	ntau = 1 / (nalpha + nbeta) / tadj

	halpha = 0.05/(exp((v + 86 + 0)/10)+1)
	hbeta = 0.05/(exp((-v - 86 - 0)/10)+1)
	hinf = halpha / (halpha + hbeta)
	htau = 1 / (halpha + hbeta) / tadj
}
