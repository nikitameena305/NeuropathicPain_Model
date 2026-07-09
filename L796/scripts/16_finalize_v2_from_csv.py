import csv
import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "closehw", str(Path(__file__).resolve().parent / "15_close_halfwidth_v2.py")
)
m2 = importlib.util.module_from_spec(spec)
sys.modules["closehw"] = m2
spec.loader.exec_module(m2)  # main() only runs under `if __name__=="__main__"`, false here


def load_rows():
    path = m2.RESULTS_DIR_V2 / "L796_final_v2_search_candidates.csv"
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            r["valid"] = (r["valid"] == "True")
            for k in ["BA_density", "KDR_scale", "soma_BNa", "RMP_mV", "Rin_GOhm",
                      "overshoot_mV", "half_width_ms", "amplitude_mV", "total_ap_error",
                      "overshoot_err", "half_width_err", "amplitude_err"]:
                r[k] = float(r[k]) if r[k] not in ("", None) else float("nan")
            r["n_ap_targets_failed"] = int(r["n_ap_targets_failed"])
            r["rheobase_pA"] = float(r["rheobase_pA"]) if r["rheobase_pA"] not in ("", None) else float("nan")
            rows.append(r)
    return rows


def pick_best(rows, label):
    valid_rows = [r for r in rows if r["valid"] and r["grid"] == label]
    if not valid_rows:
        return None
    best_row = min(valid_rows, key=lambda r: (r["n_ap_targets_failed"], r["total_ap_error"]))
    return {
        "BA_density": best_row["BA_density"],
        "KDR_scale": best_row["KDR_scale"],
        "soma_BNa": best_row["soma_BNa"],
        "n_ap_targets_failed": best_row["n_ap_targets_failed"],
        "total_ap_error": best_row["total_ap_error"],
    }


def main():
    print("Re-using existing search results from "
          f"{m2.RESULTS_DIR_V2 / 'L796_final_v2_search_candidates.csv'} "
          "(both approach grids) -- skipping the expensive grid search.")

    all_rows = load_rows()
    best_a = pick_best(all_rows, "approachA_full_axon")
    best_b = pick_best(all_rows, "approachB_reduced_axon")

    print("Best Approach A:", best_a)
    print("Best Approach B:", best_b)

    approach_used = None
    winner = None
    axon_info = None

    if best_a is not None and best_a["n_ap_targets_failed"] == 0:
        approach_used = "A"
        winner = best_a
    elif best_b is not None:
        approach_used = "B"
        winner = best_b
        if best_a is not None:
            key_a = (best_a["n_ap_targets_failed"], best_a["total_ap_error"])
            key_b = (best_b["n_ap_targets_failed"], best_b["total_ap_error"])
            if key_a < key_b:
                approach_used = "A"
                winner = best_a
    elif best_a is not None:
        approach_used = "A"
        winner = best_a

    if winner is None:
        raise RuntimeError("No valid candidate found in the existing search CSV.")

    print(f"\nWINNER: approach {approach_used}")
    print(f"  BA_density={winner['BA_density']}, KDR_scale={winner['KDR_scale']}, "
          f"soma_BNa={winner['soma_BNa']}")
    print(f"  n_ap_targets_failed={winner['n_ap_targets_failed']}, "
          f"total_ap_error={winner['total_ap_error']:.4f}")

    # Every mod.import_morphology() call invalidates Python references to sections from
    # any earlier build in this same process (HOC's array redeclaration frees the old
    # backing sections). So gather Approach-B evidence (its own separate import) BEFORE
    # building the actual winning model, so the winning model's references -- used by
    # finalize() right after -- are always the most recently built and therefore valid.
    axon_info_evidence = None
    approach_b_feat_evidence = None
    if approach_used == "A" and best_b is not None:
        print("\nGathering Approach-B evidence for the report (tau/half-width on its own "
              "best candidate), even though Approach A won overall...")
        axon_info_evidence, approach_b_feat_evidence = m2.evaluate_axon_reduction_evidence(best_b)

    print(f"\nBuilding a fresh copy of the winning ({approach_used}) model for the final sweep...")
    if approach_used == "A":
        soma, ais, groups, first_order_dend = m2.build_model_full_axon()
    else:
        soma, ais, groups, first_order_dend, axon_info = m2.build_model_reduced_axon()
        fitted_g_pas, fitted_rin = m2.fit_g_pas_for_target_rin(soma)
        axon_info["old_g_pas_S_per_cm2"] = m2.mod.G_PAS
        axon_info["new_g_pas_S_per_cm2"] = fitted_g_pas
        axon_info["refit_rin_GOhm"] = fitted_rin
        print(f"Re-fitted g_pas: {m2.mod.G_PAS:.6e} -> {fitted_g_pas:.6e} S/cm2 "
              f"(Rin now {fitted_rin:.4f} GOhm, target {m2.TARGET_RIN_GOHM})")

    m2.finalize(soma, ais, groups, first_order_dend, winner, approach_used, axon_info, all_rows,
                axon_info_evidence=axon_info_evidence,
                approach_b_feat_evidence=approach_b_feat_evidence)


if __name__ == "__main__":
    main()
