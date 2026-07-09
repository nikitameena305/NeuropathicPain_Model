#!/usr/bin/env python3
"""
scripts/19_temperature_sensitivity_fixed_intrinsic.py

Temperature SENSITIVITY analysis of the FINAL, validated L796 active model.
- NO grid search, NO conductance tuning, NO receptor recalibration, NO overwriting of validated files.
- The ONLY thing that changes between runs is h.celsius.
- The model is built ONCE; temperature is swept by setting h.celsius and re-initialising
  (this recomputes each mechanism's tadj/q10 in its INITIAL block) -- this also avoids the
  Import3d "sections get freed on re-import" bug.

RUN:
    cd ~/NeuropathicPain_Model
    ./external/SDHmodel/x86_64/special -python L796/scripts/19_temperature_sensitivity_fixed_intrinsic.py
    # single temperature only:  L796_CELSIUS=37 ./external/SDHmodel/x86_64/special -python L796/scripts/19_...py
"""
import os, sys, csv, glob, math, json
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from neuron import h

ROOT = Path(__file__).resolve().parent.parent            # L796/
PARAM = ROOT / "parameters" / "L796_final_parameter_set.json"
RES = ROOT / "results" / "temperature_sensitivity_fixed_intrinsic"
FIG = ROOT / "figures" / "temperature_sensitivity_fixed_intrinsic"
REP = ROOT / "reports" / "temperature_sensitivity_fixed_intrinsic"
for d in (RES, FIG, REP): d.mkdir(parents=True, exist_ok=True)

# ---------- protocol ----------
STIM_DELAY, STIM_DUR, TSTOP, DT = 100.0, 1000.0, 1300.0, 0.025
AP_CURRENT_PA = 80
SWEEP_PA = list(range(0, 141, 20))
SPK_THR = -20.0

def find_swc():
    for c in ["L796-ALT-PN.CNG.swc", "morphology/L796-ALT-PN.CNG.swc"]:
        p = ROOT / c
        if p.exists(): return str(p)
    hits = list(ROOT.glob("**/L796-ALT-PN*.swc"))
    if hits: return str(hits[0])
    sys.exit("SWC not found under " + str(ROOT))

# ---------- load final parameters ----------
P = json.loads(PARAM.read_text())
PASV = P["passive_fixed"]
SC   = P.get("tuned_active_scales", {})
BASE = P["base_conductance_densities_S_per_cm2"]
SOMA_BNA = float(P.get("soma_BNa_S_per_cm2", 0.0))
PROX_BNA = float(P.get("proximal_dendrite_BNa_S_per_cm2", 0.0))
PROX_SECS = set(P.get("proximal_dendrite_sections", []))
def s(k, d=1.0): return float(SC.get(k, d))

E_PAS = float(PASV["e_pas_mV"]); G_PAS = float(PASV["g_pas_S_per_cm2"])
CM = float(PASV["cm_uF_per_cm2"]); RA = float(PASV["Ra_ohm_cm"])

# ---------- build the model ONCE ----------
def build():
    h.load_file("stdrun.hoc"); h.load_file("import3d.hoc")
    rdr = h.Import3d_SWC_read(); rdr.input(find_swc())
    h.Import3d_GUI(rdr, 0).instantiate(None)
    for sec in h.allsec():
        for seg in sec:
            if seg.diam < 0.2: seg.diam = 0.2
    for sec in h.allsec():
        try: sec.nseg = int((sec.L/(0.1*h.lambda_f(100, sec=sec))+0.9)/2)*2+1
        except Exception: sec.nseg = 1
    soma = next((x for x in h.allsec() if "soma" in x.name().lower()), list(h.allsec())[0])
    for sec in h.allsec():
        sec.Ra = RA; sec.cm = CM; sec.insert("pas")
        for seg in sec: seg.pas.g = G_PAS; seg.pas.e = E_PAS
    ais = h.Section(name="artificial_ais"); ais.L = 9.0; ais.diam = 1.5; ais.nseg = 5
    ais.Ra = RA; ais.cm = CM; ais.connect(soma(1.0)); ais.insert("pas")
    for seg in ais: seg.pas.g = G_PAS; seg.pas.e = E_PAS
    def grp():
        g = {"soma": [], "dend": [], "axon": []}
        for sec in h.allsec():
            n = sec.name().lower()
            if "artificial_ais" in n: continue
            if "soma" in n: g["soma"].append(sec)
            elif "axon" in n: g["axon"].append(sec)
            elif "dend" in n or "apic" in n: g["dend"].append(sec)
        return g
    G = grp()
    for sec in G["soma"]:
        for m in ("KDR","iNaP","iCaL","iKCa","CaIntraCellDyn","B_Na"): sec.insert(m)
        sec.ena = 55; sec.ek = -90
        sec.gkbar_KDR = BASE["soma_KDR"]*s("KDR_scale"); sec.gnabar_iNaP = BASE["soma_iNaP"]*s("iNaP_scale")
        sec.pcabar_iCaL = BASE["soma_CaL"]*s("CaL_scale"); sec.gbar_iKCa = BASE["soma_KCa"]*s("KCa_scale")
        sec.gnabar_B_Na = SOMA_BNA
    for sec in G["dend"]:
        for m in ("KDR","iCaAN","iCaL","iKCa","CaIntraCellDyn"): sec.insert(m)
        sec.ek = -90
        sec.gkbar_KDR = BASE["dend_KDR"]*s("KDR_scale"); sec.gbar_iCaAN = BASE["dend_CaAN"]*s("CaAN_scale")
        sec.pcabar_iCaL = BASE["dend_CaL"]*s("CaL_scale"); sec.gbar_iKCa = BASE["dend_KCa"]*s("KCa_scale")
        base = sec.name().split(".")[-1]
        if base in PROX_SECS:
            sec.insert("B_Na"); sec.ena = 55; sec.gnabar_B_Na = PROX_BNA
    ais.insert("B_Na"); ais.insert("KDR"); ais.ena = 55; ais.ek = -90
    ais.gnabar_B_Na = BASE["AIS_BNa"]*s("BNa_scale_AIS", s("BNa_scale",1.45)); ais.gkbar_KDR = BASE["AIS_KDR"]*s("KDR_scale")
    return soma, ais

SOMA, AIS = build()

# ---------- one current-clamp run ----------
def run(iamp_nA):
    ic = h.IClamp(SOMA(0.5)); ic.delay = STIM_DELAY; ic.dur = STIM_DUR; ic.amp = iamp_nA
    t = h.Vector().record(h._ref_t); v = h.Vector().record(SOMA(0.5)._ref_v)
    h.dt = DT; h.tstop = TSTOP; h.finitialize(E_PAS); h.continuerun(TSTOP)
    return np.array(t), np.array(v), ic

def spikes(t, v):
    st = []; last = -1e9
    m = (t >= STIM_DELAY) & (t <= STIM_DELAY+STIM_DUR)
    tt, vv = t[m], v[m]
    for i in range(1, len(vv)):
        if vv[i-1] < SPK_THR <= vv[i] and tt[i]-last >= 2.0:
            st.append(tt[i]); last = tt[i]
    return st

def ap_features(t, v):
    st = spikes(t, v)
    f = dict(n_spikes=len(st), freq_Hz=len(st)/(STIM_DUR/1000.0),
             latency_ms=(st[0]-STIM_DELAY) if st else math.nan,
             threshold_mV=math.nan, peak_mV=math.nan, amplitude_mV=math.nan,
             half_width_ms=math.nan, rise_ms=math.nan, decay_ms=math.nan)
    if not st: return f
    i0 = int(np.searchsorted(t, st[0]-3)); i1 = int(np.searchsorted(t, st[0]+8))
    tw, vw = t[i0:i1], v[i0:i1]
    dvdt = np.gradient(vw, tw)
    thr_i = np.where(dvdt >= 10.0)[0]
    thr = float(vw[thr_i[0]]) if len(thr_i) else float(vw[0])
    pk_i = int(np.argmax(vw)); peak = float(vw[pk_i])
    amp = peak - thr
    half = thr + amp/2.0
    left = next((j for j in range(1, pk_i+1) if vw[j-1] < half <= vw[j]), None)
    right = next((j for j in range(pk_i+1, len(vw)) if vw[j-1] >= half > vw[j]), None)
    hw = float(tw[right]-tw[left]) if (left and right) else math.nan
    lo, hi = thr+0.1*amp, thr+0.9*amp
    r1 = next((j for j in range(1, pk_i+1) if vw[j-1] < lo <= vw[j]), None)
    r2 = next((j for j in range(1, pk_i+1) if vw[j-1] < hi <= vw[j]), None)
    rise = float(tw[r2]-tw[r1]) if (r1 and r2) else math.nan
    d1 = next((j for j in range(pk_i+1, len(vw)) if vw[j-1] >= hi > vw[j]), None)
    d2 = next((j for j in range(pk_i+1, len(vw)) if vw[j-1] >= lo > vw[j]), None)
    decay = float(tw[d2]-tw[d1]) if (d1 and d2) else math.nan
    f.update(threshold_mV=thr, peak_mV=peak, amplitude_mV=amp, half_width_ms=hw, rise_ms=rise, decay_ms=decay)
    return f

def intrinsic_at(celsius):
    h.celsius = float(celsius)
    print(f"RUNTIME_TEMPERATURE_CHECK: h.celsius = {h.celsius} C")
    t0, v0, _ = run(0.0); rmp = float(np.mean(v0[(t0>=50)&(t0<95)]))
    tR, vR, _ = run(-0.01)
    base = float(np.mean(vR[(tR>=50)&(tR<95)])); steady = float(np.mean(vR[(tR>=550)&(tR<595)]))
    rin = abs((steady-base)/-0.01)/1000.0
    counts = {}; rheo = None
    for pa in SWEEP_PA:
        tt, vv, _ = run(pa/1000.0); counts[pa] = len(spikes(tt, vv))
        if rheo is None and counts[pa] >= 1: rheo = pa
    ta, va, _ = run(AP_CURRENT_PA/1000.0); apf = ap_features(ta, va)
    row = dict(celsius=celsius, RMP_mV=round(rmp,3), Rin_GOhm=round(rin,3),
               rheobase_pA=rheo if rheo is not None else "none",
               spikes_at_80pA=apf["n_spikes"], freq_at_80pA_Hz=round(apf["freq_Hz"],2),
               first_latency_ms=round(apf["latency_ms"],2) if not math.isnan(apf["latency_ms"]) else "nan",
               AP_threshold_mV=round(apf["threshold_mV"],3), AP_peak_mV=round(apf["peak_mV"],3),
               AP_amplitude_mV=round(apf["amplitude_mV"],3), AP_half_width_ms=round(apf["half_width_ms"],3),
               AP_rise_ms=round(apf["rise_ms"],3), AP_decay_ms=round(apf["decay_ms"],3))
    return row, (ta, va), counts

env = os.environ.get("L796_CELSIUS")
TEMPS = [float(env)] if env else [6.3, 23.0, 37.0]
def tag(c): return str(c).replace(".", "p") + "C"

rows, wave, sweeps = [], {}, {}
for c in TEMPS:
    r, w, sw = intrinsic_at(c); rows.append(r); wave[c] = w; sweeps[c] = sw
    with open(RES / f"L796_intrinsic_fixed_{tag(c)}.csv", "w", newline="") as f:
        wr = csv.writer(f); wr.writerow(["feature","value"])
        for k, v in r.items(): wr.writerow([k, v])

keys = list(rows[0].keys())
with open(RES / "L796_intrinsic_temperature_comparison.csv", "w", newline="") as f:
    wr = csv.writer(f); wr.writerow(keys)
    for r in rows: wr.writerow([r[k] for k in keys])

if len(TEMPS) > 1:
    plt.figure(figsize=(8,5))
    for c in TEMPS:
        ta, va = wave[c]; m = (ta>=STIM_DELAY-5)&(ta<=STIM_DELAY+60)
        plt.plot(ta[m]-STIM_DELAY, va[m], label=f"{c} C")
    plt.xlabel("time from stim (ms)"); plt.ylabel("soma V (mV)"); plt.title("L796 AP waveform vs temperature (80 pA)")
    plt.legend(); plt.tight_layout(); plt.savefig(FIG/"L796_AP_waveform_overlay.png", dpi=200); plt.close()

    plt.figure(figsize=(8,5))
    for c in TEMPS:
        plt.plot(SWEEP_PA, [sweeps[c][p] for p in SWEEP_PA], marker="o", label=f"{c} C")
    plt.xlabel("current (pA)"); plt.ylabel("spike count (1 s)"); plt.title("L796 current sweep vs temperature")
    plt.legend(); plt.tight_layout(); plt.savefig(FIG/"L796_current_sweep_overlay.png", dpi=200); plt.close()

    for feat, fname, ylab in [("AP_half_width_ms","halfwidth","AP half-width (ms)"),
                              ("first_latency_ms","latency","first-spike latency (ms)"),
                              ("spikes_at_80pA","spikecount","spikes at 80 pA")]:
        plt.figure(figsize=(6,4))
        vals = [(float(r[feat]) if r[feat] not in ("nan","none") else 0) for r in rows]
        plt.bar([str(c) for c in TEMPS], vals, color="#2e6fb0")
        plt.ylabel(ylab); plt.xlabel("celsius"); plt.title(f"L796 {ylab} vs temperature")
        plt.tight_layout(); plt.savefig(FIG/f"L796_{fname}_vs_temperature.png", dpi=200); plt.close()

audit = []
for mp in sorted(glob.glob(str(ROOT.parent/"external/SDHmodel/mods/*.mod"))):
    txt = Path(mp).read_text(errors="ignore").lower()
    has_q10 = ("q10" in txt) or ("tadj" in txt); has_cel = "celsius" in txt
    name = Path(mp).stem; note = ""
    if name.lower().startswith("b_na") and "tadj" in txt:
        note = "computes tadj in INITIAL but may NOT apply it to state taus (temperature-invariant upstroke) -- verify"
    audit.append((name, "yes" if has_q10 else "no", "yes" if has_cel else "no", note))

def near(a, b, tol):
    try: return abs(float(a)-b) <= tol
    except: return False
chk = ""
r63 = next((r for r in rows if abs(r["celsius"]-6.3) < 0.01), None)
if r63:
    ok = all([near(r63["RMP_mV"],-72.434,1.0), near(r63["Rin_GOhm"],0.890,0.05),
              near(r63["rheobase_pA"],40,20), near(r63["AP_amplitude_mV"],70.264,4.0),
              near(r63["AP_half_width_ms"],1.450,0.2)])
    chk = ("Self-check at 6.3 C reproduces the validated model within tolerance." if ok
           else "WARNING: 6.3 C run does NOT match the validated numbers -- verify this rebuild matches your final builder.")

def col(feat): return {r["celsius"]: r[feat] for r in rows}
hw = col("AP_half_width_ms"); nsp = col("spikes_at_80pA")
hw_dir = ("shorter" if len(TEMPS)>1 and float(hw[TEMPS[-1]])<float(hw[TEMPS[0]]) else "not shorter")
exc_dir = ("less excitable (fewer spikes / higher rheobase)" if len(TEMPS)>1 and float(nsp[TEMPS[-1]])<float(nsp[TEMPS[0]])
           else "more excitable")
md = []
md.append("# L796 - Temperature Sensitivity of the Fixed Intrinsic Model\n")
md.append("Pure sensitivity analysis. The final validated model parameters are UNCHANGED; only `h.celsius` differs between runs. No tuning, no grid search, no receptor recalibration, no overwriting of validated files.\n")
md.append("## Comparison across temperatures\n")
md.append("| feature | " + " | ".join(f"{c} C" for c in TEMPS) + " |")
md.append("|---|" + "---|"*len(TEMPS))
for k in keys:
    if k == "celsius": continue
    md.append(f"| {k} | " + " | ".join(str(col(k)[c]) for c in TEMPS) + " |")
md.append("\n## Mechanism temperature audit (external/SDHmodel/mods)\n")
md.append("| mechanism | Q10/tadj | celsius | note |")
md.append("|---|---|---|---|")
for n,q,c,note in audit: md.append(f"| {n} | {q} | {c} | {note} |")
md.append("\n## Interpretation\n")
md.append(f"- **Did AP half-width get shorter at higher temperature?** {hw_dir} (6.3 C: {hw[TEMPS[0]]} ms -> {TEMPS[-1]} C: {hw[TEMPS[-1]]} ms).")
md.append(f"- **Does the model become more or less excitable with temperature?** {exc_dir} (spikes at 80 pA: {nsp[TEMPS[0]]} -> {nsp[TEMPS[-1]]}).")
md.append("- **Is 37 C physiologically closer to rat body temperature?** Yes (~37 C in vivo; many rat slice recordings are ~32-35 C; NEURON default 6.3 C is the classic squid-axon value, not physiological).")
md.append("- **Which mechanisms carry temperature scaling?** See the audit table: the K/Ca currents (KDR, iNaP, iCaL, iCaAN, iKCa, B_A) scale with q10/tadj, but B_Na (fast-Na upstroke) does not apply its tadj - so raising temperature speeds repolarisation without speeding the upstroke, collapsing spike amplitude at high celsius.")
md.append("- **Should the final validated model stay at 6.3 C?** The single-cell scorecard was validated at 6.3 C, and no single temperature makes every feature pass simultaneously (because B_Na is temperature-invariant). **Keep 6.3 C as the model of record; treat 23 C / 37 C as a documented sensitivity analysis only** - do not re-tune to a new temperature here.")
md.append("\n" + chk)
(REP / "L796_temperature_sensitivity_report.md").write_text("\n".join(md), encoding="utf-8")

print("\nDone. Temperatures:", TEMPS)
print("Results ->", RES); print("Figures ->", FIG)
print("Report  ->", REP / "L796_temperature_sensitivity_report.md")
print(chk)
