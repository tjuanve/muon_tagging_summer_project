#!/usr/bin/env python3
"""
Create an HTCondor DAG to convert VHESelfVeto i3 output to HDF5.

One job is created per i3 file, mirroring the input directory structure
under the output directory.

Usage:
    python create_h5_dag.py --years 2014 2015
"""

import argparse
import glob
import os
import subprocess

WORK_DIR = "/data/user/tvaneede/muon_tagging/h5_production"
DAG_BASE = "/scratch/tvaneede/muon_tagging"


def parse_args():
    p = argparse.ArgumentParser(description="Create DAG for HDF5 production")
    p.add_argument("--years", nargs="+", type=int, required=True,
                   help="Year(s) to process, e.g. --years 2014 2015")
    p.add_argument("--input-dir", default="/data/user/tvaneede/muon_tagging/output",
                   help="Root directory of VHESelfVeto i3 output")
    p.add_argument("--output-dir", default="/data/user/tvaneede/muon_tagging/h5",
                   help="Root directory for output HDF5 files")
    p.add_argument("--dag-dir", default=DAG_BASE,
                   help=f"Root directory for DAG files and logs (default: {DAG_BASE})")
    p.add_argument("--dag-name", default="h5",
                   help="DAG name prefix (default: h5)")
    p.add_argument("--submit", action="store_true",
                   help="Submit the DAG after creating it")
    return p.parse_args()


def main():
    args = parse_args()

    years_tag = "_".join(str(y) for y in sorted(args.years))
    dag_name = f"{args.dag_name}_{years_tag}"
    dag_dir = os.path.join(args.dag_dir, dag_name)
    log_dir = os.path.join(dag_dir, "logs")

    os.makedirs(dag_dir, exist_ok=True)
    os.makedirs(log_dir, exist_ok=True)

    sub_src = os.path.join(WORK_DIR, "h5.sub")
    sub_dst = os.path.join(dag_dir, "h5.sub")
    os.system(f"cp {sub_src} {sub_dst}")

    dag_path = os.path.join(dag_dir, "submit.dag")
    jobs = []

    with open(dag_path, "w") as dag:
        for year in sorted(args.years):
            in_year_dir = os.path.join(args.input_dir, f"IC86_{year}")
            out_year_dir = os.path.join(args.output_dir, f"IC86_{year}")

            if not os.path.isdir(in_year_dir):
                print(f"WARNING: input directory not found: {in_year_dir}")
                continue

            i3_files = sorted(glob.glob(
                os.path.join(in_year_dir, "*", "*_VHESelfVeto.i3.zst")
            ))
            print(f"IC86_{year}: {len(i3_files)} i3 files")

            for i3_file in i3_files:
                run_name = os.path.basename(os.path.dirname(i3_file))
                stem = os.path.basename(i3_file).replace(".i3.zst", "")

                out_run_dir = os.path.join(out_year_dir, run_name)
                os.makedirs(out_run_dir, exist_ok=True)

                outfile = os.path.join(out_run_dir, stem + ".h5")
                job_id = f"h5_IC86_{year}_{run_name}_{stem}".replace(".", "_")

                dag.write(f"JOB {job_id} h5.sub\n")
                dag.write(f'VARS {job_id} LOGDIR="{log_dir}"\n')
                dag.write(f'VARS {job_id} JOBID="{job_id}"\n')
                dag.write(f'VARS {job_id} INFILE="{i3_file}"\n')
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
