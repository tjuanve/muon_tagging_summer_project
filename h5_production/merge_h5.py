#!/usr/bin/env python3
"""
Merge per-subrun HDF5 files into per-run, per-year, and all-years files.

Intermediate files are written next to the subrun files:
  <h5-dir>/IC86_{year}/{RunNNNNNN}.h5   — all subruns in a run merged
  <h5-dir>/IC86_{year}.h5               — all runs in a year merged
  <output>                               — all years merged

Usage:
    python merge_h5.py --years 2014 2015 -o merged.h5
"""

import argparse
import glob
import os
import shutil

import h5py


def merge_datasets(target, source):
    for name, item in source.items():
        if isinstance(item, h5py.Dataset):
            if name not in target:
                source.copy(name, target)
            else:
                dset_src = item[...]
                dset_dst = target[name]
                if dset_dst.shape[1:] != dset_src.shape[1:]:
                    raise ValueError(f"Shape mismatch in dataset '{name}'")
                new_size = dset_dst.shape[0] + dset_src.shape[0]
                dset_dst.resize((new_size,) + dset_dst.shape[1:])
                dset_dst[-dset_src.shape[0]:] = dset_src
        elif isinstance(item, h5py.Group):
            if name not in target:
                target.create_group(name)
            merge_datasets(target[name], item)


def merge_hdf5_files(output_file, input_files):
    if not input_files:
        raise ValueError("No input files provided.")
    shutil.copyfile(input_files[0], output_file)
    with h5py.File(output_file, 'a') as fout:
        for f in input_files[1:]:
            with h5py.File(f, 'r') as fin:
                merge_datasets(fout, fin)


def parse_args():
    p = argparse.ArgumentParser(description="Merge VHESelfVeto HDF5 files")
    p.add_argument("--years", nargs="+", type=int, required=True,
                   help="Year(s) to merge, e.g. --years 2014 2015")
    p.add_argument("--input-dir", default="/data/user/tvaneede/muon_tagging/h5",
                   help="Root directory of per-subrun HDF5 files")
    p.add_argument("-o", "--output", required=True,
                   help="Final merged output file")
    return p.parse_args()


def main():
    args = parse_args()

    year_files = []

    for year in sorted(args.years):
        year_dir = os.path.join(args.input_dir, f"IC86_{year}")
        if not os.path.isdir(year_dir):
            print(f"WARNING: {year_dir} not found, skipping")
            continue

        run_files = []

        for run_dir in sorted(glob.glob(os.path.join(year_dir, "Run*"))):
            run_name = os.path.basename(run_dir)
            subrun_files = sorted(glob.glob(os.path.join(run_dir, "*.h5")))
            if not subrun_files:
                print(f"  WARNING: no h5 files in {run_dir}")
                continue

            run_out = os.path.join(year_dir, f"{run_name}.h5")
            print(f"  {run_name}: merging {len(subrun_files)} subruns → {run_out}")
            merge_hdf5_files(run_out, subrun_files)
            run_files.append(run_out)

        if not run_files:
            print(f"  WARNING: no runs found for IC86_{year}")
            continue

        year_out = os.path.join(args.input_dir, f"IC86_{year}.h5")
        print(f"IC86_{year}: merging {len(run_files)} runs → {year_out}")
        merge_hdf5_files(year_out, run_files)
        year_files.append(year_out)

    if not year_files:
        print("No files to merge.")
        return

    print(f"Merging {len(year_files)} year(s) → {args.output}")
    merge_hdf5_files(args.output, year_files)
    print("Done.")


if __name__ == "__main__":
    main()
```
