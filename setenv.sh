#!/bin/bash
# Source this file to set up the IceTray environment:
#   source setenv.sh

ICETRAY_BASE=/cvmfs/icecube.opensciencegrid.org/py3-v4.4.1/RHEL_7_x86_64_v2/metaprojects/icetray/v1.14.0

export ICETRAY_SHELL="${ICETRAY_BASE}/bin/icetray-shell"
export PYTHON=/cvmfs/icecube.opensciencegrid.org/users/tvaneede/venv/py3-v4.4.1_reco-v1.1.0/bin/python

export PYTHONPATH="${ICETRAY_BASE}/lib${PYTHONPATH:+:${PYTHONPATH}}"
export LD_LIBRARY_PATH="${ICETRAY_BASE}/lib:${ICETRAY_BASE}/lib/tools${LD_LIBRARY_PATH:+:${LD_LIBRARY_PATH}}"
export PATH="${ICETRAY_BASE}/bin:${PYTHON%/bin/python}/bin${PATH:+:${PATH}}"
