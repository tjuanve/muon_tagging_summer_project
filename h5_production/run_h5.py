#!/usr/bin/env python3
"""
Convert VHESelfVeto i3 output to HDF5.

Usage:
    icetray-shell python run_h5.py -o output.h5 input.i3.zst [...]
"""

import argparse

from icecube.icetray import I3Tray
from icecube import dataio, hdfwriter


KEYS = [
    "I3EventHeader",
    "HomogenizedQTot",
    "CausalQTot",
    "VHESelfVeto",
    "VHESelfVetoVertexTime",
    "VHESelfVetoVertexPos",
    "HomogenizedQTotShrunk",
    "CausalQTotShrunk",
    "VHESelfVetoShrunk",
    "VHESelfVetoShrunkVertexTime",
    "VHESelfVetoShrunkVertexPos",
]


def parse_args():
    p = argparse.ArgumentParser(description="Convert VHESelfVeto i3 output to HDF5")
    p.add_argument("-o", "--output", required=True, help="Output .h5 file")
    p.add_argument("inputfiles", nargs="+", help="Input .i3 files")
    return p.parse_args()


def main():
    args = parse_args()

    tray = I3Tray()

    tray.AddModule("I3Reader", "reader", FilenameList=args.inputfiles)

    tray.AddSegment(
        hdfwriter.I3HDFWriter, "writer",
        Output=args.output,
        Keys=KEYS,
        SubEventStreams=["InIceSplit"],
    )

    tray.Execute()
    tray.Finish()


if __name__ == "__main__":
    main()
