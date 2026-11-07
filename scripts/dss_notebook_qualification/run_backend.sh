#!/bin/bash
# Run the DSS example notebooks on one backend (java, native or shadow).
# Usage: PY=<python> RUN_ROOT=<dir> bash run_backend.sh <backend> [notebook-stems...]
# JAVA_HOME must point at a JDK for the java and shadow backends. Each notebook runs in
# $RUN_ROOT/<backend>/<stem>/ (14b runs in 14a's folder, because it uses 14a's outputs).
set -u
B=$1; shift
HERE=$(cd "$(dirname "$0")" && pwd)
EX=${EXAMPLES:-$HERE/../../examples}
PY=${PY:-python}
ROOT=${RUN_ROOT:?set RUN_ROOT to a scratch folder outside the repository}
NBS=${@:-01_basic_workflow 05_clone_workflow 06_results_dss 101_guide_basic_model_setup 102_guide_meteorologic_methods 104_guide_basin_methods_loss_transform 105_guide_calibration_validation 106_guide_advanced_analysis 14a_aorc_download 14b_aorc_grid_setup 14c_aorc_hms_execution}
for nb in $NBS; do
  shared=""; [ "$nb" = "14b_aorc_grid_setup" ] && shared=14a_aorc_download
  "$PY" "$HERE/run_nb.py" "$EX/$nb.ipynb" "$B" "$ROOT" 3600 $shared 2>/dev/null | tail -1
done
