#!/usr/bin/env python3
"""
Run VHESelfVeto on IceCube level2 data, then DetectorShrinker + a second
VHESelfVeto on the shrunk geometry to estimate the nested-veto passing rate.

Usage:
    icetray-shell python run_vheselfveto.py -o output.i3.zst -g GCD.i3.zst datafile.i3.zst [...]
"""

import argparse

from icecube.icetray import I3Tray, I3Units
from icecube import icetray, dataio, dataclasses, VHESelfVeto, DomTools


def parse_args():
    p = argparse.ArgumentParser(description="Apply VHESelfVeto to IceCube data")
    p.add_argument("-o", "--output", required=True, help="Output .i3 file")
    p.add_argument("-g", "--gcd", required=True, help="GCD file")
    p.add_argument("inputfiles", nargs="+", help="Input .i3 data files")

    # ---- VHESelfVeto (first pass, full geometry) --------------------------------
    vv = p.add_argument_group("VHESelfVeto (full geometry)")
    vv.add_argument("--pulses", default="SplitInIcePulses",
                    help="Pulse series to use (default: SplitInIcePulses)")
    vv.add_argument("--geometry", default="I3Geometry",
                    help="Geometry object to use (default: I3Geometry)")
    vv.add_argument("--top-boundary-width", type=float, default=90.,
                    help="Distance from top/side edge with no hits [m] (default: 90)")
    vv.add_argument("--bottom-boundary-width", type=float, default=10.,
                    help="Distance from bottom edge with no hits [m] (default: 10)")
    vv.add_argument("--dust-layer", type=float, default=-135.,
                    help="Z coordinate of dust layer [m] (default: -135)")
    vv.add_argument("--dust-layer-width", type=float, default=80.,
                    help="Dust layer boundary width below the layer [m] (default: 80)")
    vv.add_argument("--time-window", type=float, default=3000.,
                    help="Sliding time window size [ns] (default: 3000)")
    vv.add_argument("--vertex-threshold", type=float, default=250.,
                    help="PE in sliding window to declare a vertex (default: 250)")
    vv.add_argument("--veto-threshold", type=float, default=3.,
                    help="Max PE in veto region before vertex time (default: 3)")
    vv.add_argument("--output-bool", default="VHESelfVeto",
                    help="Frame key for veto I3Bool; VertexTime and VertexPos are appended for the other outputs (default: VHESelfVeto)")
    vv.add_argument("--select-passing-inner", action="store_true", default=False,
                    help="Only write events that pass the outer veto but are vetoed by the shrunk-geometry veto (default: False)")

    # ---- DetectorShrinker -------------------------------------------------------
    ds = p.add_argument_group("DetectorShrinker")
    ds.add_argument("--ds-top-boundary-width", type=float, default=90.,
                    help="Top/side boundary width for DetectorShrinker [m] (default: 90)")
    ds.add_argument("--ds-bottom-boundary-width", type=float, default=10.,
                    help="Bottom boundary width for DetectorShrinker [m] (default: 10)")

    return p.parse_args()


STATUSES = ("passed", "vetoed", "no_vertex")


def make_counter():
    return {"total": 0, "passed": 0, "vetoed": 0, "no_vertex": 0}


def make_cross_counter():
    return {(s1, s2): 0 for s1 in STATUSES for s2 in STATUSES}


def get_status(frame, key):
    if key not in frame:
        return "no_vertex"
    return "vetoed" if frame[key].value else "passed"


def main():
    args = parse_args()

    hlc_key         = args.pulses + "HLC"
    hlc_key_trimmed = hlc_key + "Trimmed"

    c1 = make_counter()
    c2 = make_counter()
    cross = make_cross_counter()

    def count_results(frame, key, counter):
        counter["total"] += 1
        counter[get_status(frame, key)] += 1

    def count_comparison(frame, key_full, key_shrunk):
        cross[get_status(frame, key_full), get_status(frame, key_shrunk)] += 1

    tray = I3Tray()

    tray.AddModule(
        "I3Reader", "reader",
        FilenameList=[args.gcd] + args.inputfiles,
    )

    # ---- LC pulse cleaning (once) -----------------------------------------------
    tray.AddModule(
        "I3LCPulseCleaning", "lc_cleaning",
        Input=args.pulses,
        OutputHLC=hlc_key,
        OutputSLC="",
    )

    # ---- Full geometry ----------------------------------------------------------
    tray.AddModule(
        "HomogenizedQTot", "qtot_full",
        Pulses=args.pulses,
        Output="HomogenizedQTot",
    )

    tray.AddModule(
        "VHESelfVeto", "vheselfveto",
        Pulses=hlc_key,
        Geometry=args.geometry,
        TopBoundaryWidth=args.top_boundary_width * I3Units.m,
        BottomBoundaryWidth=args.bottom_boundary_width * I3Units.m,
        DustLayer=args.dust_layer * I3Units.m,
        DustLayerWidth=args.dust_layer_width * I3Units.m,
        TimeWindow=args.time_window * I3Units.ns,
        VertexThreshold=args.vertex_threshold,
        VetoThreshold=args.veto_threshold,
        OutputBool=args.output_bool,
        OutputVertexTime=args.output_bool + "VertexTime",
        OutputVertexPos=args.output_bool + "VertexPos",
    )

    tray.AddModule(
        "HomogenizedQTot", "qtot_causal_full",
        Pulses=args.pulses,
        Output="CausalQTot",
        VertexTime=args.output_bool + "VertexTime",
    )

    tray.AddModule(count_results, "count_full", key=args.output_bool, counter=c1,
                   Streams=[icetray.I3Frame.Physics])

    # ---- DetectorShrinker -------------------------------------------------------
    # Run twice with the same geometry boundary settings: once to trim the original
    # pulse series (used by HomogenizedQTot), once to trim the HLC series (used by
    # VHESelfVeto). Both calls produce the same I3GeometryTrimmed.
    ds_kwargs = dict(
        InGeometry=args.geometry,
        TopBoundaryWidth=args.ds_top_boundary_width * I3Units.m,
        BottomBoundaryWidth=args.ds_bottom_boundary_width * I3Units.m,
    )

    tray.AddModule(
        "DetectorShrinker", "detector_shrinker",
        Pulses=args.pulses,
        OutPulses=args.pulses + "Trimmed",
        OutGeometry=args.geometry + "Trimmed",
        **ds_kwargs,
    )

    tray.AddModule(
        "DetectorShrinker", "detector_shrinker_hlc",
        Pulses=hlc_key,
        OutPulses=hlc_key_trimmed,
        OutGeometry=args.geometry + "TrimmedHLC",
        **ds_kwargs,
    )

    # ---- Shrunk geometry --------------------------------------------------------
    tray.AddModule(
        "HomogenizedQTot", "qtot_shrunk",
        Pulses=args.pulses + "Trimmed",
        Output="HomogenizedQTotShrunk",
    )

    tray.AddModule(
        "VHESelfVeto", "vheselfveto_shrunk",
        Pulses=hlc_key_trimmed,
        Geometry=args.geometry + "Trimmed",
        TopBoundaryWidth=args.top_boundary_width * I3Units.m,
        BottomBoundaryWidth=args.bottom_boundary_width * I3Units.m,
        DustLayer=args.dust_layer * I3Units.m,
        DustLayerWidth=args.dust_layer_width * I3Units.m,
        TimeWindow=args.time_window * I3Units.ns,
        VertexThreshold=args.vertex_threshold,
        VetoThreshold=args.veto_threshold,
        OutputBool=args.output_bool + "Shrunk",
        OutputVertexTime=args.output_bool + "ShrunkVertexTime",
        OutputVertexPos=args.output_bool + "ShrunkVertexPos",
    )

    tray.AddModule(
        "HomogenizedQTot", "qtot_causal_shrunk",
        Pulses=args.pulses + "Trimmed",
        Output="CausalQTotShrunk",
        VertexTime=args.output_bool + "ShrunkVertexTime",
    )

    tray.AddModule(count_results, "count_shrunk", key=args.output_bool + "Shrunk", counter=c2,
                   Streams=[icetray.I3Frame.Physics])

    tray.AddModule(count_comparison, "count_comparison",
                   key_full=args.output_bool, key_shrunk=args.output_bool + "Shrunk",
                   Streams=[icetray.I3Frame.Physics])

    if args.select_passing_inner:
        def select_passing_inner(frame):
            return (get_status(frame, args.output_bool) == "passed" and
                    get_status(frame, args.output_bool + "Shrunk") == "vetoed")

        tray.AddModule(select_passing_inner, "select_passing_inner",
                       Streams=[icetray.I3Frame.Physics])

    tray.AddModule(
        "I3Writer", "writer",
        Filename=args.output,
        DropOrphanStreams=[icetray.I3Frame.DAQ],
    )

    tray.Execute(10000)
    tray.Finish()

    def print_results(label, c):
        print(f"\n=== {label} ===")
        print(f"  Total physics frames : {c['total']}")
        print(f"  Passed veto          : {c['passed']}")
        print(f"  Vetoed               : {c['vetoed']}")
        print(f"  No vertex found      : {c['no_vertex']}")

    def print_comparison():
        print("\n=== Cross-comparison: full vs shrunk geometry ===")
        for full_status in STATUSES:
            row_total = sum(cross[full_status, s] for s in STATUSES)
            if row_total == 0:
                continue
            print(f"\n  Full geometry: {full_status} ({row_total} events)")
            for shrunk_status in STATUSES:
                n = cross[full_status, shrunk_status]
                pct = 100.0 * n / row_total
                print(f"    Shrunk {shrunk_status:<12}: {n:6d}  ({pct:5.1f}%)")

    print_results("VHESelfVeto (full geometry)", c1)
    print_results("VHESelfVeto (shrunk geometry)", c2)
    print_comparison()


if __name__ == "__main__":
    main()
