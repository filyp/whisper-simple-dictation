# Whisper simple dictation

- press a key to start recording
- release it to stop recording
- Whisper transcribes it
- the text is typed with simulated keypresses

You can either run Whisper locally or through OpenAI's API.

For local execution you need a CUDA device with at least 4GB VRAM. Uses whisper version `large-v3`, run with FasterWhisper.

With remote execution, OpenAI's API has about 1 second delay (as of Jan 2024), while local is near instant.


## Installation

```
git clone https://github.com/filyp/whisper-simple-dictation.git
cd whisper-simple-dictation
python3 -m venv venv --copies
```

Then, if you want to run locally, run:
```
venv/bin/python -m pip install -r requirements_local.txt
```

Or if you want to run remotely, run:
```
venv/bin/python -m pip install -r requirements_remote.txt
echo sk-... > ~/.config/openai.token
```
Where `sk-...` is your OpenAI API token.


## Running

```
bash run_dictation_local.sh en
```
or to run remotely:
```
bash run_dictation_remote.sh en
```

Ctrl-c to stop.

By default the record key is *right* ctrl. You can change it in `dictation.py`, but it must be a modifier key (shift, alt, ...).

Last argument (here `en`), sets the language. You can not pass any language to detect it automatically, but that can have worse latency and accuracy.

For languages with special chars like ó, д, etc. you'll also need to install ydotool to have them typed. (Although there are cases where ydotool also fails.)

## Other approaches

At first I wanted real-time dictation, similar to [nerd-dictation](https://github.com/ideasman42/nerd-dictation). There's [whisper_streaming](https://github.com/ufal/whisper_streaming) which implements something similar, a continuous transcription using whisper. But it has a 3.3 second time lag, and because it needs to run whisper on many overlapping time windows, it's more compute heavy. Also those transcribed time windows are sometimes merged incorrectly. It may be enough for creating captions, but not really for dictation.

With some clever engineering and a lot of compute maybe we could get that time lag to less than a second. But I found that reading what you said with a few hundred millisecond delay is very confusing, similar to hearing your voice delayed. So for now, I think the best and most reliable way is the one used here. This may change with future neural nets, with architecture other than whisper, aimed at real-time transcription.


# TODO

- [x] pass languages to bash
- [ ] get context with some accesibility tools
- [ ] incremenal transcription? but no moving window, just larger and larger windows
- [ ] maybe use clipboard pasting to pasty any special chars, as the last resort