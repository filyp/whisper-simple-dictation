#!/usr/bin/env bash
script_path="$(realpath "$0")"
script_dir="$(dirname "$script_path")"
cd $script_dir
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    source venv/bin/activate
fi
export LD_LIBRARY_PATH=`python3 -c 'import os; import nvidia.cublas.lib; import nvidia.cudnn.lib; print(os.path.dirname(nvidia.cublas.lib.__file__) + ":" + os.path.dirname(nvidia.cudnn.lib.__file__))'`
if [ -f ".venv/bin/python3" ]; then
    .venv/bin/python3 dictation_auto_off.py "$@"
else
    venv/bin/python3 dictation_auto_off.py "$@"
fi

