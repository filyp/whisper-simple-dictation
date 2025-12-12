#!/usr/bin/env bash
script_path="$(realpath "$0")"
script_dir="$(dirname "$script_path")"
cd $script_dir

source .venv/bin/activate
export LD_LIBRARY_PATH="$VIRTUAL_ENV/lib/python3.13/site-packages/nvidia/cublas/lib:$VIRTUAL_ENV/lib/python3.13/site-packages/nvidia/cudnn/lib"
.venv/bin/python3 dictation.py local "$@"