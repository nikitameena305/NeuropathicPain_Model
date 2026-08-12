TITLE HH sodium channel
: Hodgkin - Huxley squid sodium channel

: The model used in Melnick et al. 2004 Adapt 5 and 11 mV
: moved alpha/beta_shift from RANGE to GLOBAL (15thMay20, Kazutaka)
: implemented tau_factor to RANGE and used it insted of tadj (15thMay20, Kazutaka)
: (should set alpha/beta_shift as GLOBAL variable when use test_EXinitial)

NEURON {
	SUFFIX B_Na
	USEION na READ ena WRITE ina
	RANGE gnabar, ina
	RANGE inf, tau
	RANGE tadj, tau_factor, alpha_shift, beta_shift
	: GLOBAL alpha_shift, beta_shift
}

UNITS {
	(mA) = (milliamp)
	(mV) = (millivolt)
}

INDEPENDENT {t FROM 0 TO 1 WITH 1 (ms)}
PARAMETER {
	ena = 53 (mV)
	alpha_shift = 0 (mV)
	beta_shift = 0 (mV)
	tau_factor = 1
}

STATE {
	m h
}

ASSIGNED {
	celsius (degC)
	v (mV)
	ina (mA/cm2)

	gnabar (mho/cm2)
	tadj (1)

	inf[2] (1)
	tau[2] (ms)
	a[2] (1/ms)
	b[2] (1/ms)	
}

INITIAL {
	tadj = 3^((celsius - 23) / 10)
	rates(v)
	m = inf[0]
	h = inf[1]
}

BREAKPOINT {
	SOLVE states METHOD cnexp
	ina = gnabar*m*m*m*h*(v - ena)
}

DERIVATIVE states{
	rates(v)
	m' = (inf[0] - m) / tau[0]
	h' = (inf[1] - h) / tau[1]
}

FUNCTION alpha(v(mV),i) {
	if       (i==0){
		alpha = 0.182*trap(-v + 7 - 35 + alpha_shift, 9)
	}else if (i==1){
		alpha = 0.061*trap(-v + 13 - 48 + alpha_shift, 3) + 0.0166
	}
}

FUNCTION beta(v,i) {
	if       (i==0){
		beta = 0.124 * trap(v - 7 + 35 + beta_shift, 9)
	}else if (i==1){
		beta = 0.0018 * trap(v - 13 + 84 + beta_shift, 18)
	}
}

FUNCTION trap(x,y) {
	if (fabs(x/y) < 1e-6) {
		trap = y*(1 - x/y/2)
	}else{
		trap = x/(exp(x/y) - 1)
	}
}

PROCEDURE rates(v) {
	TABLE inf, tau DEPEND tadj FROM -100 TO 100 WITH 200
	FROM i=0 TO 1 {
		a[i] = alpha(v,i) b[i]=beta(v,i)
		tau[i] = 1 / (a[i] + b[i]) / tau_factor
	}
	inf[0] = a[0] / (a[0] + b[0])
	inf[1] = 1 / (1 + exp((v + 75 - 11) / 9))
}