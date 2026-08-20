#!/usr/bin/env python3
"""
neuromorpho_downloader.py  –  NeuroMorpho.Org bulk metadata extractor
======================================================================
Downloads neuron metadata from the NeuroMorpho REST API and writes CSV.

QUICK START
-----------
  pip install requests pandas tqdm
  python neuromorpho_downloader.py --mode count  --query "brain_region:dorsal horn"
  python neuromorpho_downloader.py --mode pain_regions
  python neuromorpho_downloader.py --mode custom  --query "brain_region:dorsal horn AND species:rat"
  python neuromorpho_downloader.py --mode all     --yes

NOTES
-----
  • The API blocks requests from non-browser server IPs (HTTP 403 "Host not in
    allowlist").  Run this script on your own machine or a lab workstation, not
    on a remote compute cluster without prior whitelisting.
  • Page size is capped at 500 by the API; this script always uses 500.
  • Polite delay between pages: 0.3 s (adjustable via --delay).
  • SWC download URLs and NeuroMorpho page URLs are appended automatically.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests
from tqdm import tqdm

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

BASE_URL   = "https://neuromorpho.org/api/neuron"
PAGE_SIZE  = 500
USER_AGENT = "neuromorpho-downloader/2.0 (research; contact: your@email.edu)"

# ── Pain-pathway preset queries ───────────────────────────────────────────────
PAIN_QUERIES = {
    "dorsal_horn":   "brain_region:dorsal horn",
    "spinal_cord":   "brain_region:spinal cord",
    "PAG":           "brain_region:periaqueductal gray",
    "RVM":           "brain_region:rostral ventromedial medulla",
    "medulla":       "brain_region:medulla",
    "thalamus":      "brain_region:thalamus",
    "somatosensory": "brain_region:somatosensory cortex",
}

# ── HTTP session ──────────────────────────────────────────────────────────────
def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    return s

SESSION = make_session()


# ── Core API calls ────────────────────────────────────────────────────────────
def fetch_page(query: str, page: int, size: int = PAGE_SIZE) -> dict:
    if query:
        url    = f"{BASE_URL}/select"
        params = {"q": query, "page": page, "size": size}
    else:
        url    = BASE_URL
        params = {"page": page, "size": size}
    resp = SESSION.get(url, params=params, timeout=30)
    if resp.status_code == 403:
        sys.exit(
            "\n✗  HTTP 403 – NeuroMorpho blocks this IP/host.\n"
            "   Run the script from your local machine or a whitelisted workstation.\n"
        )
    resp.raise_for_status()
    return resp.json()


def count_neurons(query: str) -> int:
    """Return total element count for a query without fetching all pages."""
    data = fetch_page(query, page=0, size=1)
    return data.get("page", {}).get("totalElements", 0)


def fetch_all(query: str, label: str = "query", delay: float = 0.3,
              max_pages: int = 0) -> list[dict]:
    """Paginate through all results; return list of neuron dicts."""
    print(f"\n[{label}] probing count...", end=" ", flush=True)
    first      = fetch_page(query, page=0)
    page_meta  = first.get("page", {})
    total      = page_meta.get("totalElements", 0)
    n_pages    = page_meta.get("totalPages", 1)
    if max_pages:
        n_pages = min(n_pages, max_pages)
    print(f"{total:,} neurons across {n_pages} pages.")

    if total == 0:
        return []

    def _extract(data: dict) -> list:
        return (data.get("neuronResources")
                or data.get("_embedded", {}).get("neuronResources", []))

    neurons = list(_extract(first))

    for p in tqdm(range(1, n_pages), desc=f"  {label}", unit="page"):
        for attempt in range(3):
            try:
                data = fetch_page(query, page=p)
                neurons.extend(_extract(data))
                time.sleep(delay)
                break
            except requests.RequestException as e:
                if attempt == 2:
                    print(f"\n  ✗ Skipping page {p} after 3 failures: {e}")
                else:
                    time.sleep(2 ** attempt)
    return neurons


# ── Data normalisation ────────────────────────────────────────────────────────
def _flatten(x):
    if isinstance(x, list):
        return "; ".join(str(i) for i in x)
    if isinstance(x, dict):
        return json.dumps(x)
    return x


def to_dataframe(neurons: list[dict]) -> "pd.DataFrame":
    if not HAS_PANDAS:
        raise RuntimeError("pandas not installed: pip install pandas")
    df = pd.DataFrame(neurons)
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].map(_flatten)
    if {"archive", "neuron_name"} <= set(df.columns):
        df["swc_source_url"] = (
            "https://neuromorpho.org/dableFiles/"
            + df["archive"].str.lower()
            + "/Source-Version/"
            + df["neuron_name"]
            + ".swc"
        )
        df["swc_standardized_url"] = (
            "https://neuromorpho.org/dableFiles/"
            + df["archive"].str.lower()
            + "/CNG%20version/"
            + df["neuron_name"]
            + ".swc"
        )
        df["neuron_page_url"] = (
            "https://neuromorpho.org/neuron_info.jsp?neuron_name="
            + df["neuron_name"]
        )
    return df


def to_csv_manual(neurons: list[dict], path: str):
    """Write CSV without pandas (fallback)."""
    if not neurons:
        print("No neurons to write.")
        return
    keys = list(neurons[0].keys())
    with open(path, "w", encoding="utf-8") as f:
        f.write(",".join(keys) + "\n")
        for n in neurons:
            row = [json.dumps(_flatten(n.get(k, ""))) for k in keys]
            f.write(",".join(row) + "\n")


def save(neurons: list[dict], path: str, query_label: str = ""):
    if not neurons:
        print(f"  No neurons for label '{query_label}', skipping save.")
        return
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if HAS_PANDAS:
        df = to_dataframe(neurons)
        if query_label:
            df.insert(0, "query_label", query_label)
        df.to_csv(path, index=False)
        print(f"  ✓ {len(df):,} neurons → {path}")
        print(df[["neuron_id","neuron_name","species","brain_region","cell_type"]]
              .head(5).to_string(index=False))
    else:
        to_csv_manual(neurons, path)
        print(f"  ✓ {len(neurons):,} neurons → {path}  (pandas-free mode)")


# ── SWC bulk download ─────────────────────────────────────────────────────────
def download_swc_bulk(csv_path: str, out_dir: str = "swc_files",
                      version: str = "source", limit: int = 0):
    """
    Download SWC files listed in a CSV produced by this script.
    version: 'source' | 'standardized'
    """
    if not HAS_PANDAS:
        sys.exit("pandas required for --mode swc_download")
    df  = pd.read_csv(csv_path)
    col = "swc_source_url" if version == "source" else "swc_standardized_url"
    if col not in df.columns:
        sys.exit(f"Column '{col}' not found in {csv_path}. Re-run metadata download first.")
    os.makedirs(out_dir, exist_ok=True)
    rows = df.itertuples()
    if limit:
        import itertools
        rows = itertools.islice(rows, limit)
    for row in tqdm(rows, desc="Downloading SWC", total=limit or len(df)):
        url  = getattr(row, col, "")
        name = getattr(row, "neuron_name", f"neuron_{row.Index}")
        dest = os.path.join(out_dir, f"{name}.swc")
        if os.path.exists(dest):
            continue
        try:
            r = SESSION.get(url, timeout=20)
            r.raise_for_status()
            with open(dest, "wb") as f:
                f.write(r.content)
            time.sleep(0.1)
        except Exception as e:
            print(f"\n  ✗ {name}: {e}")
    print(f"\n✓ SWC files → {out_dir}/")


# ── High-level run modes ──────────────────────────────────────────────────────
def mode_count(query: str):
    n = count_neurons(query)
    print(f"\n  Query : {query or '(all neurons)'}")
    print(f"  Count : {n:,} neurons")


def mode_custom(query: str, output: str, delay: float, max_pages: int):
    neurons = fetch_all(query, label="custom", delay=delay, max_pages=max_pages)
    save(neurons, output)


def mode_pain_regions(prefix: str, delay: float, separate: bool):
    all_neurons, frames = [], []
    for label, query in PAIN_QUERIES.items():
        neurons = fetch_all(query, label=label, delay=delay)
        if separate:
            save(neurons, f"{prefix}_{label}.csv", query_label=label)
        else:
            for n in neurons:
                n["query_label"] = label
            all_neurons.extend(neurons)
        time.sleep(0.5)

    if not separate:
        if not HAS_PANDAS:
            save(all_neurons, f"{prefix}_pain_pathway_neurons.csv")
            return
        df = to_dataframe(all_neurons)
        df.drop_duplicates(subset="neuron_id", keep="first", inplace=True)
        out = f"{prefix}_pain_pathway_neurons.csv"
        df.to_csv(out, index=False)
        print(f"\n✓ {len(df):,} unique neurons (deduped) → {out}")


def mode_all(prefix: str, delay: float, yes: bool):
    if not yes:
        print("WARNING: downloading all ~80 k+ neurons may take 15–30 min.")
        if input("Continue? [y/N] ").strip().lower() != "y":
            sys.exit("Aborted.")
    neurons = fetch_all("", label="all_neurons", delay=delay)
    save(neurons, f"{prefix}_all_neurons.csv")


def mode_fields():
    r = SESSION.get(f"{BASE_URL}/fields", timeout=15)
    r.raise_for_status()
    fields = r.json().get("Neuron Fields", [])
    print("Available neuron fields:")
    for f in fields:
        print(f"  {f}")


# ── CLI ───────────────────────────────────────────────────────────────────────
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="neuromorpho_downloader.py",
        description=(
            "Bulk-download neuron metadata from NeuroMorpho.Org.\n"
            "Requires direct browser-origin network access (run locally, not on\n"
            "cluster nodes whose IPs are not whitelisted by neuromorpho.org)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
MODES
  count          Print neuron count for a query (no download).
  fields         List all queryable neuron field names.
  custom         Download neurons matching an arbitrary query string.
  pain_regions   Download all preset pain-pathway regions (dorsal horn, spinal
                 cord, PAG, RVM, medulla, thalamus, somatosensory cortex).
  all            Download the entire database (~80 k neurons, 15–30 min).
  swc_download   Download SWC morphology files listed in an existing CSV.

QUERY SYNTAX
  Single field   brain_region:dorsal horn
  AND            brain_region:dorsal horn AND species:rat
  OR (comma)     species:rat,mouse
  Wildcard       neuron_name:cnic_*
  Combined       brain_region:spinal cord AND cell_type:interneuron AND species:rat

EXAMPLES
  python neuromorpho_downloader.py --mode count --query "brain_region:dorsal horn"
  python neuromorpho_downloader.py --mode custom \\
      --query "brain_region:dorsal horn AND species:rat" \\
      --output dorsal_horn_rat.csv
  python neuromorpho_downloader.py --mode pain_regions --separate
  python neuromorpho_downloader.py --mode all --yes --prefix my_project
  python neuromorpho_downloader.py --mode swc_download \\
      --csv dorsal_horn_rat.csv --swc-dir swc/ --swc-version source --limit 50
        """,
    )
    p.add_argument(
        "--mode", required=True,
        choices=["count","fields","custom","pain_regions","all","swc_download"],
        help="Execution mode (see MODES below)",
    )
    p.add_argument(
        "--query", default="",
        metavar="QUERY",
        help='Query string, e.g. "brain_region:dorsal horn AND species:rat"',
    )
    p.add_argument(
        "--output", default="neuromorpho_custom.csv",
        metavar="FILE",
        help="Output CSV path (mode=custom; default: neuromorpho_custom.csv)",
    )
    p.add_argument(
        "--prefix", default="neuromorpho",
        metavar="PREFIX",
        help="Filename prefix for pain_regions / all modes (default: neuromorpho)",
    )
    p.add_argument(
        "--separate", action="store_true",
        help="(pain_regions) Write one CSV per region instead of a merged file",
    )
    p.add_argument(
        "--yes", "-y", action="store_true",
        help="Skip confirmation prompt for mode=all",
    )
    p.add_argument(
        "--delay", type=float, default=0.3,
        metavar="SECONDS",
        help="Polite inter-page delay in seconds (default: 0.3)",
    )
    p.add_argument(
        "--max-pages", type=int, default=0,
        metavar="N",
        help="Stop after N pages per query (0 = fetch all; useful for testing)",
    )
    p.add_argument(
        "--csv", default="",
        metavar="FILE",
        help="Input CSV for mode=swc_download",
    )
    p.add_argument(
        "--swc-dir", default="swc_files",
        metavar="DIR",
        help="Output directory for SWC files (default: swc_files/)",
    )
    p.add_argument(
        "--swc-version", choices=["source","standardized"], default="source",
        help="SWC file version to download: source (original) or standardized CNG (default: source)",
    )
    p.add_argument(
        "--limit", type=int, default=0,
        metavar="N",
        help="For swc_download: download only first N neurons (0 = all)",
    )
    return p


def main():
    parser = build_parser()
    args   = parser.parse_args()

    if args.mode == "count":
        if not args.query:
            parser.error("--query is required for mode=count")
        mode_count(args.query)

    elif args.mode == "fields":
        mode_fields()

    elif args.mode == "custom":
        if not args.query:
            parser.error("--query is required for mode=custom")
        mode_custom(args.query, args.output, args.delay, args.max_pages)

    elif args.mode == "pain_regions":
        mode_pain_regions(args.prefix, args.delay, args.separate)

    elif args.mode == "all":
        mode_all(args.prefix, args.delay, args.yes)

    elif args.mode == "swc_download":
        if not args.csv:
            parser.error("--csv is required for mode=swc_download")
        download_swc_bulk(args.csv, args.swc_dir, args.swc_version, args.limit)


if __name__ == "__main__":
    main()
