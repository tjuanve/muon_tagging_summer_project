#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ICETRAY_SHELL=/cvmfs/icecube.opensciencegrid.org/py3-v4.4.1/RHEL_7_x86_64_v2/metaprojects/icetray/v1.14.0/bin/icetray-shell
PYTHON=/cvmfs/icecube.opensciencegrid.org/users/tvaneede/venv/py3-v4.4.1_reco-v1.1.0/bin/python

RUN_DIR=/data/exp/IceCube/2014/filtered/level2pass2a/0410/Run00124550
GCD=${RUN_DIR}/Level2pass2_IC86.2014_data_Run00124550_0410_1_89_GCD.i3.zst
DATA=${RUN_DIR}/Level2pass2_IC86.2014_data_Run00124550_Subrun00000000_00000000.i3.zst
OUTPUT=${SCRIPT_DIR}/output_Run00124550_sub00.i3.zst

echo "GCD  : ${GCD}"
echo "Data : ${DATA}"
echo "Out  : ${OUTPUT}"
echo ""

"${ICETRAY_SHELL}" "${PYTHON}" "${SCRIPT_DIR}/run_vheselfveto.py" \
    -g "${GCD}" \
    -o "${OUTPUT}" \
    "${DATA}" \
    2>&1 | tee "${SCRIPT_DIR}/test_run.log"
