#!/usr/bin/env python3
"""
Create a HTCondor DAG to run VHESelfVeto over IceCube level2pass2a data.

One job is created per subrun file for each good run in the given year(s).
Runs that do not meet the active string requirement are skipped by default.

Must be run inside icetray-shell (needed to read GCD files for the active
string check).

Usage:
    icetray-shell python create_dag.py --years 2014 2015
"""

import argparse
import glob
import os
import subprocess

from icecube import dataio


# Outer-layer strings (from makedag.py, tyuan)
OUTER_LAYER = frozenset([
    1, 2, 3, 4, 5, 6, 7, 13, 14, 21, 22, 30, 31,
    40, 41, 50, 51, 59, 60, 67, 68, 72, 73, 74, 75, 76, 77, 78,
])

# IceTop OM numbers — excluded from the in-ice active string count
ICETOP_OMS = frozenset([61, 62, 63, 64, 65, 66])


def data_base(year):
    level = "level2pass2a" if year <= 2016 else "level2"
    return f"/data/exp/IceCube/{year}/filtered/{level}"


def good_run_info_path(year):
    return f"{data_base(year)}/IC86_{year}_GoodRunInfo.txt"

DAG_BASE = "/scratch/tvaneede/muon_tagging"
WORK_DIR = "/data/user/tvaneede/muon_tagging"


def parse_args():
    p = argparse.ArgumentParser(description="Create DAG for VHESelfVeto processing")
    p.add_argument("--years", nargs="+", type=int, required=True,
                   help="Year(s) to process, e.g. --years 2014 2015")
    p.add_argument("--output-dir", default="/data/user/tvaneede/muon_tagging/output",
                   help="Root directory for output .i3 files")
    p.add_argument("--dag-dir", default=DAG_BASE,
                   help=f"Root directory for DAG files and logs (default: {DAG_BASE})")
    p.add_argument("--dag-name", default="vheselfveto",
                   help="DAG name (default: vheselfveto)")
    p.add_argument("--submit", action="store_true",
                   help="Submit the DAG after creating it")
    p.add_argument("--no-burn-sample", action="store_true",
                   help="Process all good runs instead of only the burn sample (runs ending in 0)")
    p.add_argument("--no-active-string-check", action="store_true",
                   help="Skip the active string requirement check (not recommended)")
    p.add_argument("--max-runs", type=int, default=None,
                   help="Maximum number of runs to process per year (default: all)")
    return p.parse_args()


def parse_good_runs(good_run_info_path, burn_sample_only=True):
    """Return a list of (run_num, OutDir) tuples for runs with Good_i3 == 1.

    If burn_sample_only is True, only runs whose run number ends in 0 are
    returned (the standard IceCube burn sample, ~10% of the data).
    """
    good_runs = []
    with open(good_run_info_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("RunNum") or line.startswith("("):
                continue
            parts = line.split()
            if len(parts) < 8:
                continue
            run_num = int(parts[0])
            good_i3 = int(parts[1])
            out_dir = parts[7]
            if good_i3 == 1:
                if burn_sample_only and run_num % 10 != 0:
                    continue
                good_runs.append(out_dir)
    return good_runs


def check_active_strings(gcd_path):
    """Return True if the run meets the active string requirement.

    Requires:
      - At least 83 strings with ≥1 working in-ice DOM
      - No inactive strings in the outer layer
    """
    det = {s: set(range(1, 67)) for s in range(1, 87)}
    f = dataio.I3File(gcd_path)
    while f.more():
        frame = f.pop_frame()
        if frame.Has("BadDomsList"):
            for bad in frame["BadDomsList"]:
                if 1 <= bad.string <= 86:
                    det[bad.string].discard(bad.om)
            break

    active = {s for s, doms in det.items() if doms - ICETOP_OMS}
    inactive = set(range(1, 87)) - active
    n_inactive_outer = len(OUTER_LAYER & inactive)
    return len(active) >= 83 and n_inactive_outer == 0


def find_gcd(run_dir):
    """Return the GCD file in a run directory."""
    matches = glob.glob(os.path.join(run_dir, "*GCD*.i3.zst"))
    if not matches:
        raise FileNotFoundError(f"No GCD file found in {run_dir}")
    return matches[0]


def find_subruns(run_dir):
    """Return sorted list of subrun data files in a run directory."""
    return sorted(glob.glob(os.path.join(run_dir, "*Subrun*.i3.zst")))


def main():
    args = parse_args()

    years_tag = "_".join(str(y) for y in sorted(args.years))
    dag_name = f"{args.dag_name}_{years_tag}"
    dag_dir = os.path.join(args.dag_dir, dag_name)
    log_dir = os.path.join(dag_dir, "logs")

    os.makedirs(dag_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    # Copy the submit file next to the DAG
    sub_src = os.path.join(WORK_DIR, "vheselfveto.sub")
    sub_dst = os.path.join(dag_dir, "vheselfveto.sub")
    os.system(f"cp {sub_src} {sub_dst}")

    dag_path = os.path.join(dag_dir, "submit.dag")
    jobs = []

    with open(dag_path, "w") as dag:
        for year in sorted(args.years):
            good_run_info = good_run_info_path(year)
            if not os.path.exists(good_run_info):
                print(f"WARNING: GoodRunInfo not found for {year}: {good_run_info}")
                continue

            burn_sample_only = not args.no_burn_sample
            run_dirs = parse_good_runs(good_run_info, burn_sample_only=burn_sample_only)
            if args.max_runs is not None:
                run_dirs = run_dirs[:args.max_runs]
            sample_label = "burn sample runs" if burn_sample_only else "good runs"
            max_label = f" (capped at {args.max_runs})" if args.max_runs is not None else ""
            print(f"IC86_{year}: {len(run_dirs)} {sample_label}{max_label}")

            out_year_dir = os.path.join(args.output_dir, f"IC86_{year}")
            os.makedirs(out_year_dir, exist_ok=True)

            for run_dir in run_dirs:
                if not os.path.isdir(run_dir):
                    print(f"  WARNING: run directory not found: {run_dir}")
                    continue

                run_name = os.path.basename(os.path.normpath(run_dir))  # e.g. Run00124550

                try:
                    gcd = find_gcd(run_dir)
                except FileNotFoundError as e:
                    print(f"  WARNING: {e}")
                    continue

                if not args.no_active_string_check:
                    if not check_active_strings(gcd):
                        print(f"  SKIP {run_name}: failed active string requirement")
                        continue

                subruns = find_subruns(run_dir)
                if not subruns:
                    print(f"  WARNING: no subrun files in {run_dir}")
                    continue

                out_run_dir = os.path.join(out_year_dir, run_name)
                os.makedirs(out_run_dir, exist_ok=True)

                outfile = os.path.join(out_run_dir, f"{run_name}_VHESelfVeto.i3.zst")
                infiles = " ".join(subruns)
                job_id = f"IC86_{year}_{run_name}"

                dag.write(f"JOB {job_id} vheselfveto.sub\n")
                dag.write(f'VARS {job_id} LOGDIR="{log_dir}"\n')
                dag.write(f'VARS {job_id} JOBID="{job_id}"\n')
                dag.write(f'VARS {job_id} GCD="{gcd}"\n')
                dag.write(f'VARS {job_id} INFILE="{infiles}"\n')
                dag.write(f'VARS {job_id} OUTFILE="{outfile}"\n')
                dag.write("\n")

                jobs.append(job_id)

    print(f"\nDAG written to: {dag_path}")
    print(f"Total jobs    : {len(jobs)}")

    if args.submit:
        os.chdir(dag_dir)
        process = subprocess.run(
            "condor_submit_dag submit.dag",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        print("STDOUT:", process.stdout)
        print("STDERR:", process.stderr)
        print("Exit code:", process.returncode)


if __name__ == "__main__":
    main()
