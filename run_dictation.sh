script_path="$(realpath "$0")"
script_dir="$(dirname "$script_path")"
cd $script_dir
source venv/bin/activate
export LD_LIBRARY_PATH=`python3 -c 'import os; import nvidia.cublas.lib; import nvidia.cudnn.lib; print(os.path.dirname(nvidia.cublas.lib.__file__) + ":" + os.path.dirname(nvidia.cudnn.lib.__file__))'`
venv/bin/python3 dictation.py