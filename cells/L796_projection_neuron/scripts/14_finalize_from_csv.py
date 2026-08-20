import csv
import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "finish13", str(Path(__file__).resolve().parent / "13_finish_L796.py")
)
mod = importlib.util.module_from_spec(spec)
sys.modules["finish13"] = mod
# exec_module runs the whole file, but main() only runs under `if __name__ == "__main__"`,
# which is False here since this module's name is "finish13", not "__main__".
spec.loader.exec_module(mod)


def load_rows():
    path = mod.RESULTS_DIR / "L796_final_search_candidates.csv"
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            r["valid"] = (r["valid"] == "True")
            for k in ["soma_BNa", "KDR_scale", "RMP_mV", "Rin_GOhm", "overshoot_mV",
                      "half_width_ms", "amplitude_mV", "total_ap_error",
                      "overshoot_err", "half_width_err", "amplitude_err"]:
                r[k] = float(r[k]) if r[k] not in ("", None) else float("nan")
            r["rheobase_pA"] = float(r["rheobase_pA"]) if r["rheobase_pA"] not in ("", None) else float("nan")
            rows.append(r)
    return rows


def main():
    print("Re-using existing search results from "
          f"{mod.RESULTS_DIR / 'L796_final_search_candidates.csv'} "
          "(both primary and refinement grids) -- skipping the expensive grid search.")

    all_rows = load_rows()
    best = mod.select_best(all_rows)
    if best is None:
        raise RuntimeError("No valid candidate found in the existing search CSV.")

    print("Building model to run the final/before feature-extraction sweeps...")
    soma, ais, groups, first_order_dend = mod.build_model()
    print(f"Soma: {soma.name()}, AIS: {ais.name()}")

    mod.finalize(soma, ais, groups, first_order_dend, best, all_rows)


if __name__ == "__main__":
    main()
