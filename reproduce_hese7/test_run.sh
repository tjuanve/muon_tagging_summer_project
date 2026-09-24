#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ICETRAY_SHELL=/cvmfs/icecube.opensciencegrid.org/py3-v4.4.1/RHEL_7_x86_64_v2/metaprojects/icetray/v1.14.0/bin/icetray-shell
PYTHON=/cvmfs/icecube.opensciencegrid.org/users/tvaneede/venv/py3-v4.4.1_reco-v1.1.0/bin/python

RUN_DIR=/data/exp/IceCube/2015/filtered/level2pass2a/1021/Run00127009
GCD=${RUN_DIR}/Level2pass2_IC86.2015_data_Run00127009_1021_3_205_GCD.i3.gz
INPUT="${RUN_DIR}/Level2pass2_IC86.2015_data_Run00127009_Subrun00000000_0000000*.i3.zst"

"${ICETRAY_SHELL}" "${PYTHON}" "${SCRIPT_DIR}/shrinkydink.py" \
    --input  "${INPUT}" \
    --max-files 100 \
    --output-prefix Run00127009 \
    --output-dir    "${SCRIPT_DIR}/output" \
    2>&1 | tee "${SCRIPT_DIR}/test_run.log"


    # --gcd    "${GCD}" \
