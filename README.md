# Whisper simple dictation

- press a key to start recording
- release it to stop recording
- whisper transcribes it
- the text is typed with simulated keypresses

You need a CUDA device with at least 4GB VRAM.

Uses whisper version `large-v3`, run with FasterWhisper.


## Installation

```
python3 -m venv venv --copies
venv/bin/python3 -m pip install -r requirements.txt
```

## Running

```
bash run_dictation.sh
```

Ctrl-c to stop.

By default the record key is *right* ctrl. You can change it in `dictation.py`, but it must be a modifier key (shift, alt, ...).