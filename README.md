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

### Local
Then, if you want to run locally, run:
```
venv/bin/python -m pip install -r requirements_local.txt
sudo usermod -aG input __YOUR_USER_NAME__
```

Then log out and back in.

The local version supports both Wayland and X11.

(If you're using Wayland and don't want to add your user to the input group for security reasons, see instructions in `example_service_file.service`. On X11 it doesn't matter - devices are exposed anyway.)

### Remote
Or if you want to run remotely, run:
```
venv/bin/python -m pip install -r requirements_remote.txt
echo sk-... > ~/.config/openai.token
```
Where `sk-...` is your OpenAI API token.

Note: the remote version currently supports only X11, not Wayland.

## Running

```
bash run_dictation_auto_off.sh en
```
or to run remotely:
```
bash run_dictation_remote.sh en
```

Ctrl-c to stop.

By default the record key is *right* ctrl. You can change it in `dictation.py`, but it must be a modifier key (shift, alt, ...).

Note that the way we send text is by copying it to the clipboard and then sending Ctrl+Shift+V. That's because typing the text normally is complicated to do right, with all the special characters. 

To set up a service that will run whisper-simple-dictation, take a look at `example_service_file.service`.

## Options

- **Language.** First argument (in the example above `en`), sets the language. You can also not pass any language to detect it automatically, but that can have worse latency and accuracy.
- **Choosing model** Default is `large-v3`. You can also pass e.g. `--model medium` or `--model small`.

## Other systems

In case of local running `dictation_auto_off.py` uses evdev which only works on Linux. For Windows and Mac you can try `_lagacy_dictation_auto_off_pynput.py`, which uses pynput. (Modify `run_dictation_auto_off.sh`.)

If running remotely, `dictation_remote.py` uses pynput, so it should work on all systems (except for Linux with Wayland - evdev is needed for that, and that's not implemented).

## Other approaches

At first I wanted real-time dictation, similar to [nerd-dictation](https://github.com/ideasman42/nerd-dictation). There's [whisper_streaming](https://github.com/ufal/whisper_streaming) which implements something similar, a continuous transcription using whisper. But it has a 3.3 second time lag, and because it needs to run whisper on many overlapping time windows, it's more compute heavy. Also those transcribed time windows are sometimes merged incorrectly. It may be enough for creating captions, but not really for dictation.

With some clever engineering and a lot of compute maybe we could get that time lag to less than a second. But I found that reading what you said with a few hundred millisecond delay is very confusing, similar to hearing your voice delayed. So for now, I think the best and most reliable way is the one used here. This may change with future neural nets, with architecture other than whisper, aimed at real-time transcription.

There's also [whisper-writer](https://github.com/savbell/whisper-writer), which is more mature, but doesn't (as of Jan 2024) have push-to-talk, which I find more pleasant to use.

# TODO

- [ ] test if prompting works ok locally
- [ ] test if no lang actually increases latency/accuracy that much - it's useful to leave it blank
- [ ] maybe trigger with some key combo, but then still wait for the release of modifier to stop recording - in that case, I'd like to factor out the keyhandling class
---
probably won't do
- grabbing context everywhere except some list of windows? - not very reliable, a lot of tinkering, platform specific, and not even that useful?
    - now only terminal doesn't work
    - in vscode, I just disabled C-S-Home; Now I can dictate, but context won't be grabbed. 
- incremenal transcription? but no moving window, just larger and larger windows. but that makes sense only with local, and even then it may be so slow that the lag is confusing. it also complicates a lot of things
- on wayland, pynput doesn't detect ctrl_r (or any other keypresses) when in terminal (tested on manjaro plasma)
---
- [x] guard against too short audio - min length is 0.1 s
- [x] additional space is typed, but should be clipped (f.e. for vim compatibility with pasting in normal mode)
- [x] pass languages to bash
- [x] get context
- [x] maybe use clipboard pasting to pasty any special chars, as the last resort
- [x] pass all the possible options as args
- [x] document options
