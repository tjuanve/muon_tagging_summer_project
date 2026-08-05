#!/usr/bin/env python3
"""
Plot XY (top) and ZX (side) projections of the IceCube detector from a GCD file.

Requires the IceTray environment (source setenv.sh first).

Usage:
    icetray-shell python plot_detector.py
    icetray-shell python plot_detector.py -g <GCD.i3.gz> -o detector.pdf
"""

import argparse
from collections import defaultdict

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from icecube import dataio

# Standard IC86 GCD on CVMFS
DEFAULT_GCD = "/cvmfs/icecube.opensciencegrid.org/data/GCD/GeoCalibDetectorStatus_2014.56784_V0.i3.gz"

DEEPCORE_STRINGS = frozenset(range(79, 87))   # strings 79-86
OUTER_STRINGS = frozenset([
    1, 2, 3, 4, 5, 6, 7, 13, 14, 21, 22, 30, 31,
    40, 41, 50, 51, 59, 60, 67, 68, 72, 73, 74, 75, 76, 77, 78,
])
ICETOP_OMS = frozenset(range(61, 67))


def load_geometry(gcd_path):
    """Return dict of string -> list of (x, y, z) for in-ice DOMs."""
    f = dataio.I3File(gcd_path)
    while f.more():
        frame = f.pop_frame()
        if frame.Has("I3Geometry"):
            geo = frame["I3Geometry"]
            break

    strings = defaultdict(list)
    for omkey, omgeo in geo.omgeo.items():
        if omkey.om in ICETOP_OMS:
            continue
        p = omgeo.position
        strings[omkey.string].append((p.x, p.y, p.z))
    return strings


def string_center(doms):
    xs, ys, _ = zip(*doms)
    return np.mean(xs), np.mean(ys)


def parse_args():
    p = argparse.ArgumentParser(description="Plot IceCube detector geometry")
    p.add_argument("-g", "--gcd", default=DEFAULT_GCD, help="GCD file")
    p.add_argument("-o", "--output", default="detector.pdf", help="Output file")
    return p.parse_args()


def main():
    args = parse_args()
    print(f"Reading geometry from {args.gcd}")
    strings = load_geometry(args.gcd)

    # Categorise strings
    def color(s):
        if s in DEEPCORE_STRINGS:
            return "tomato"
        if s in OUTER_STRINGS:
            return "steelblue"
        return "C0"

    fig, (ax_xy, ax_zx) = plt.subplots(1, 2, figsize=(14, 6))

    # --- XY: top view, one dot per string ---
    for s, doms in strings.items():
        cx, cy = string_center(doms)
        ax_xy.scatter(cx, cy, s=30, c=color(s), zorder=2, linewidths=0)

    ax_xy.set_xlabel("x [m]")
    ax_xy.set_ylabel("y [m]")
    ax_xy.set_title("Top view (XY)")
    ax_xy.set_aspect("equal")
    ax_xy.grid(True, alpha=0.3)

    # --- ZX: side view, one dot per DOM ---
    for s, doms in strings.items():
        xs, _, zs = zip(*doms)
        ax_zx.scatter(xs, zs, s=2, c=color(s), alpha=0.6, linewidths=0)

    ax_zx.set_xlabel("x [m]")
    ax_zx.set_ylabel("z [m]")
    ax_zx.set_title("Side view (ZX)")
    ax_zx.grid(True, alpha=0.3)

    # Legend
    legend = [
        mpatches.Patch(color="C0",        label="IceCube"),
        mpatches.Patch(color="steelblue",  label="Outer layer"),
        mpatches.Patch(color="tomato",     label="DeepCore"),
    ]
    for ax in (ax_xy, ax_zx):
        ax.legend(handles=legend, fontsize=8)

    plt.tight_layout()
    plt.savefig(args.output, dpi=150)
    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()
