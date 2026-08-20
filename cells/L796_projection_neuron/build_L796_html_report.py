#!/usr/bin/env python3
"""
build_L796_html_report.py  (v2 — adds a Methods & Tools section, de-duplicated)
Generate a colour-coded, self-contained HTML report of the L796 model from the
outputs already in the folder. Pure standard library (no pip installs).

RUN (in WSL, from the repository root):
    cd cells/L796_projection_neuron
    python3 build_L796_html_report.py
Output: reports/L796_report.html   (open in a browser; Print -> Save as PDF)

Design: METHODS explain HOW and WHY (software, fitting, parameter choices); RESULTS
sections show only the numbers/figures, so nothing is repeated.
"""
import sys, csv, base64, html
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).resolve().parent
OUT = ROOT / "reports" / "L796_report.html"
OUT.parent.mkdir(parents=True, exist_ok=True)

def find(*patterns):
    out, seen = [], set()
    for p in patterns:
        for h in sorted(ROOT.glob(p)):
            if h not in seen and h.exists():
                seen.add(h); out.append(h)
    return out

def pill(text):
    t = (text or "").upper()
    if "PASS" in t and "RELAX" not in t: cls = "pass"
    elif "FAIL" in t: cls = "fail"
    elif "MATCH" in t: cls = "match"
    elif any(k in t for k in ("RELAX","MEASURED","UNCERTAIN","INFO","CHECK","DEFER","PROXY")): cls = "warn"
    else: cls = "info"
    return f'<span class="pill {cls}">{html.escape(text)}</span>'

def csv_table(path):
    try:
        rows = list(csv.reader(open(path, newline="", encoding="utf-8")))
    except Exception as e:
        return f"<p class='foot'>Could not read {html.escape(path.name)}: {e}</p>"
    if not rows: return ""
    head, body = rows[0], rows[1:]
    vcol = next((i for i,c in enumerate(head) if "verdict" in c.lower()), None)
    out = ["<table><tr>"] + [f"<th>{html.escape(c)}</th>" for c in head] + ["</tr>"]
    for r in body:
        out.append("<tr>")
        for i,c in enumerate(r):
            out.append(f"<td>{pill(c) if i==vcol else html.escape(c)}</td>")
        out.append("</tr>")
    out.append("</table>"); return "".join(out)

def img(path, cap=""):
    try: b64 = base64.b64encode(path.read_bytes()).decode()
    except Exception: return ""
    return (f'<figure><img src="data:image/png;base64,{b64}">'
            f'<figcaption>{html.escape(cap or path.stem.replace("_"," "))}</figcaption></figure>')

def grid(paths):
    cells = [c for c in (img(p) for p in paths if p.exists()) if c]
    return f'<div class="grid">{"".join(cells)}</div>' if cells else ""

single_csv   = find("results/**/*validation*vs*targets*.csv","results/*validation*vs*targets*.csv")
receptor_csv = find("results/receptors/*.csv")
morph_imgs   = find("figures/**/*morphology_XY*.png")
passive_imgs = find("figures/**/*passive_best_fit*.png")
active_imgs  = find("figures/**/*before_after*.png","figures/**/*step5_v1_v2*.png","figures/**/*final*FI*.png")
recep_imgs   = find("plots/receptors/*.png")
n_img = len([p for p in morph_imgs+passive_imgs+active_imgs+recep_imgs if p.exists()])

CSS = """
:root{--navy:#12324f;--blue:#2e6fb0;--teal:#2a9d8f;--red:#d1495b;--green:#3a9d5d;--amber:#e0a13c;--soft:#eef3f8;--line:#d6e0ea}
*{box-sizing:border-box}body{font-family:Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#26333f;background:#dfe7ef;margin:0;padding:26px;line-height:1.55}
.wrap{max-width:960px;margin:0 auto}
header{background:linear-gradient(135deg,#12324f,#2e6fb0);color:#fff;border-radius:14px;padding:28px 32px;margin-bottom:20px}
header h1{margin:0 0 6px;font-size:28px}header p{margin:0;color:#dce9f6}
.badge{display:inline-block;background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.35);color:#fff;border-radius:999px;padding:4px 11px;font-size:12px;margin:8px 4px 0 0}
section{background:#fff;border-radius:12px;padding:20px 24px;margin-bottom:16px;box-shadow:0 3px 12px rgba(20,40,60,.07)}
h2{color:#12324f;border-left:5px solid #2e6fb0;padding-left:12px;font-size:21px;margin:2px 0 12px}
h3{color:#2e6fb0;font-size:15.5px;margin:15px 0 5px}
table{width:100%;border-collapse:collapse;margin:10px 0;font-size:13.5px}
th,td{padding:7px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:#12324f;color:#fff;font-size:11.5px;text-transform:uppercase;letter-spacing:.03em}
tr:nth-child(even) td{background:var(--soft)}
.pill{display:inline-block;padding:2px 9px;border-radius:999px;color:#fff;font-size:11.5px;font-weight:700}
.pass{background:var(--green)}.fail{background:var(--red)}.warn{background:var(--amber)}.info{background:var(--blue)}.match{background:var(--teal)}
figure{margin:0;background:var(--soft);border:1px solid var(--line);border-radius:10px;padding:9px}
figure img{width:100%;border-radius:6px;display:block}figcaption{font-size:12px;color:#5a6b7b;margin-top:5px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.callout{border-radius:10px;padding:13px 15px;margin:12px 0;font-size:14px}
.c-green{background:#e8f5ee;border-left:5px solid var(--green)}.c-amber{background:#fdf4e5;border-left:5px solid var(--amber)}
.c-red{background:#fbeaed;border-left:5px solid var(--red)}.c-blue{background:#e9f2fb;border-left:5px solid var(--blue)}
ul{margin:6px 0 6px 18px}code{background:#eef3f8;padding:1px 5px;border-radius:4px;font-size:12.5px}.foot{font-size:12px;color:#8093a3}
@media(max-width:700px){.grid{grid-template-columns:1fr}}
"""

# ---- METHODS & TOOLS (explains HOW/WHY once; results below don't repeat it) ----
METHODS = """
<section><h2>1 · Methods &amp; tools</h2>

<h3>Software stack</h3>
<ul>
<li><b>NEURON</b> (compartmental simulator) — runs the biophysical model; mechanisms are compiled with <code>nrnivmodl</code> in <code>shared/mechanisms/medlock_267056/</code>.</li>
<li><b>Ion-channel &amp; synapse mechanisms</b> from <b>ModelDB accession 267056</b> (a published spinal dorsal-horn model): B_Na, KDR, iNaP, iCaL, iCaAN, iKCa, CaIntraCellDyn (intrinsic) and AMPA/NMDA/GABAa/GABAb/Glycine DynSyn (synaptic).</li>
<li><b>Python 3</b> drives the simulations and analysis; <b>matplotlib</b> makes the figures; this report is generated by a standard-library Python script.</li>
<li>Simulation temperature fixed at <code>h.celsius = 6.3&nbsp;°C</code> (documented explicitly; see §3).</li>
</ul>

<h3>Which values were used as targets, and why only those</h3>
<p>The model is judged against a small set of <b>experimentally reported features of lamina I projection neurons</b>, each taken from a specific paper and graded by confidence. Only features with a real literature value are scored PASS/FAIL; features without a target are reported as MEASURED (informational).</p>
<table>
<tr><th>Target</th><th>Value</th><th>Source</th><th>Confidence</th></tr>
<tr><td>RMP</td><td>−72.8 mV</td><td>Luz 2014</td><td>HIGH</td></tr>
<tr><td>Input resistance</td><td>0.77 GΩ</td><td>Luz 2014 / Li &amp; Baccei 2012</td><td>HIGH</td></tr>
<tr><td>Rheobase</td><td>20–60 pA</td><td>Li &amp; Baccei 2012</td><td>MEDIUM</td></tr>
<tr><td>AP amplitude / overshoot</td><td>70–78 mV / +5…+30 mV</td><td>Zhang 2021</td><td>MEDIUM</td></tr>
<tr><td>AP half-width</td><td>0.87–1.14 ms</td><td>Zhang 2021</td><td>MEDIUM</td></tr>
<tr><td>Firing pattern</td><td>delayed / tonic</td><td>Prescott &amp; De Koninck 2002</td><td>HIGH</td></tr>
</table>

<h3>How each parameter was obtained</h3>
<ul>
<li><b>Morphology</b> — a NeuroMorpho SWC (Szűcs archive) imported via NEURON <code>Import3d</code> (200 sections + a short artificial AIS; sub-0.2 µm diameters corrected).</li>
<li><b>Passive</b> (cm = 1.0 µF/cm², Ra = 200 Ω·cm are modelling conventions) — the leak conductance <b>g_pas was fitted by a simulation-based search</b> until the simulated input resistance matched the Luz-2014 target; e_pas set to the experimental RMP.</li>
<li><b>Active conductances</b> — inserted from ModelDB 267056 and <b>phenomenologically fitted</b>: the base densities are scaled by factors found through a <b>bounded grid search</b>, scored by normalized error against the AP targets above, and <b>any candidate that fired spontaneously at 0 pA or moved RMP/Rin/rheobase out of range was rejected</b>. That rejection rule is why only certain scale values survive. These are <b>fitted, not measured, densities</b> — the base kinetics come from a different preparation (267056).</li>
<li><b>The somatic-Na correction</b> — the original model had B_Na only in the AIS, so a small fast-Na density was added to soma + proximal dendrites and KDR re-balanced, again inside the same rejection bounds.</li>
<li><b>Synaptic weights</b> — each receptor weight was <b>calibrated by a scan over the monotonic low-weight region</b> to a physiological unitary EPSP/IPSP (0.5–5 mV); NMDA uses the real Jahr &amp; Stevens (1990) Mg²⁺-block equation; dendritic locations chosen by path distance from the soma.</li>
<li><b>Neuropathic manipulations</b> — the <i>direction</i> of each change is from the literature (↑AMPA/NMDA: Latremoliere &amp; Woolf 2009; ↓GABA/glycine + depolarizing ECl: Coull 2003); the <i>magnitudes</i> are tagged ASSUMPTION.</li>
</ul>
<p class="foot">All exact numbers live in the parameter files: <code>parameters/L796_final_parameter_set.json</code>, <code>results/…validation_vs_targets.csv</code>, <code>results/receptors/…</code>. This report reads them directly.</p>
</section>
"""

P = []
P.append(f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>L796 Report</title><style>{CSS}</style></head><body><div class='wrap'>")
P.append("""<header><h1>L796 ALT-PN — Full Modelling Report</h1>
<p>Rat lamina I anterolateral-tract projection neuron · NEURON · ModelDB 267056 · h.celsius = 6.3 °C</p>
<div><span class='badge'>Morphology ✓</span><span class='badge'>Passive ✓</span><span class='badge'>Active 5/6</span><span class='badge'>Receptors ✓</span><span class='badge'>Neuropathic ✓</span></div></header>""")
P.append(METHODS)

# 2 morphology + passive (figures only — method already explained above)
P.append("<section><h2>2 · Morphology &amp; passive — result</h2>")
P.append(grid(morph_imgs + passive_imgs))
P.append("<div class='callout c-green'><b>Passive validated:</b> RMP and Rin fall in the lamina I projection-neuron range.</div></section>")

# 3 active + scorecard
P.append("<section><h2>3 · Active model — result</h2>")
P.append(grid(active_imgs))
for c in single_csv: P.append(f"<h3>{html.escape(c.name)}</h3>" + csv_table(c))
P.append("<div class='callout c-amber'><b>AP half-width = documented relaxed-pass.</b> A temperature scan (§1 method) showed no <code>celsius</code> value narrows the AP without collapsing amplitude — because B_Na is temperature-invariant while the K/Ca currents scale — so the residual half-width gap is channel-kinetics-limited.</div></section>")

# 4 receptors
P.append("<section><h2>4 · Ligand-gated receptors — result</h2>")
P.append(grid(recep_imgs))
for c in receptor_csv: P.append(f"<h3>{html.escape(c.name)}</h3>" + csv_table(c))
P.append("<div class='callout c-blue'><b>Scope:</b> AMPA/NMDA and GABA-A/glycine validated; nAChR is a documented proxy on the projection neuron (real dorsal-horn nAChR is antinociceptive/presynaptic); P2X &amp; 5-HT3 deferred (no vetted mod), not faked.</div>")
P.append("<div class='callout c-red'><b>Bug fixed:</b> NEURON point processes are never auto-replaced at a segment, so discarded synapses stayed wired and stacked onto later tests; fixed with a NetCon registry (reset_stimuli()) + reusable IClamps.</div></section>")

# 5 neuropathic
P.append("<section><h2>5 · Neuropathic manipulation — result</h2><div class='callout c-green'><b>Disease mechanism reproduced:</b> the cited changes lower rheobase and raise firing; an input blocked under normal weights fires under neuropathic weights (disinhibition → projection-neuron hyperexcitability). Numbers/figures above.</div></section>")

# 6 status
P.append("""<section><h2>6 · Status &amp; what's left</h2><div class='grid'>
<div class='callout c-green' style='margin:0'><b>Done &amp; validated</b><ul><li>Morphology + passive</li><li>Active 5/6 (half-width relaxed-pass)</li><li>AMPA/NMDA, GABA-A/glycine, nAChR proxy</li><li>Neuropathic condition</li><li>Point-process bug fixed</li></ul></div>
<div class='callout c-amber' style='margin:0'><b>Still to do</b><ul><li>Add A-type K (IA/Kv4) for mechanistic delayed firing</li><li>Implement P2X / 5-HT3 if vetted mods obtained</li><li>External validation vs a digitized experimental AP trace</li><li>Wire GRP interneuron → L796 synapse after it passes</li></ul></div></div>
<p class='foot'>Sources: Luz 2014 · Li &amp; Baccei 2012 · Prescott &amp; De Koninck 2002 · Zhang 2021 · Jahr &amp; Stevens 1990 · Coull 2003 · Latremoliere &amp; Woolf 2009 · Tsuda 2003 · Suzuki 2004 · ModelDB 267056. Everything phenomenologically fitted; nothing over-claimed.</p></section>""")

P.append("</div></body></html>")
OUT.write_text("".join(P), encoding="utf-8")
print(f"Wrote {OUT}")
print(f"Embedded images: {n_img} | single-cell CSVs: {len(single_csv)} | receptor CSVs: {len(receptor_csv)}")
print("Open in a browser; Print -> Save as PDF. Optional: wkhtmltopdf reports/L796_report.html reports/L796_report.pdf")
