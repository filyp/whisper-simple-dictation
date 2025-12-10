#!/usr/bin/env bash
script_path="$(realpath "$0")"
script_dir="$(dirname "$script_path")"
cd $script_dir
export OPENAI_API_KEY=$(cat ~/.config/openai.token)
.venv/bin/python3 dictation.py remote --use-ydotool "$@"
