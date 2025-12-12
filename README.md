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
python3 -m venv .venv --copies
.venv/bin/pip install -e .
```

If using Wayland, you also need to install ydotool and enable ydotoold. (The script tries to use ydotool, and if it's not installed, it falls back to pynput. Ydotool unfortunately does not support typing special characters.)

### Remote
If you want to run remotely, run:
```
echo sk-... > ~/.config/openai.token
```
Where `sk-...` is your OpenAI API token.

### Local
Then, if you want to run locally, run:
```
.venv/bin/pip install -e ".[local]"
sudo usermod -aG input __YOUR_USER_NAME__
```

Then log out and back in.

(If you're using Wayland and don't want to add your user to the input group for security reasons, see instructions in `dictation_local.service`. On X11 it doesn't matter - devices are exposed anyway.)


## Running

To run remotely:
```
.venv/bin/python3 dictation.py remote en
```

To run locally:
```
bash run_dictation_local.sh en
```

Ctrl-c to stop.

By default the record key is *right* ctrl. You can change it in `dictation.py`, but it must be a modifier key (shift, alt, ...).

Note that the way we send text is by copying it to the clipboard and then sending Ctrl+Shift+V. That's because typing the text normally is complicated to do right, with all the special characters. 

To set up a service that will run whisper-simple-dictation, take a look at `example_service_file.service`.

## Options

- **Language.** First argument (in the example above `en`), sets the language. You can also not pass any language to detect it automatically, but that can have worse latency and accuracy.
- **Choosing model** Default is `large-v3`. You can also pass e.g. `--model medium` or `--model small`.

## Other approaches

At first I wanted real-time dictation, similar to [nerd-dictation](https://github.com/ideasman42/nerd-dictation). There's [whisper_streaming](https://github.com/ufal/whisper_streaming) which implements something similar, a continuous transcription using whisper. But it has a 3.3 second time lag, and because it needs to run whisper on many overlapping time windows, it's more compute heavy. Also those transcribed time windows are sometimes merged incorrectly. It may be enough for creating captions, but not really for dictation.

With some clever engineering and a lot of compute maybe we could get that time lag to less than a second. But I found that reading what you said with a few hundred millisecond delay is very confusing, similar to hearing your voice delayed. So for now, I think the best and most reliable way is the one used here. This may change with future neural nets, with architecture other than whisper, aimed at real-time transcription.

There's also [whisper-writer](https://github.com/savbell/whisper-writer), which is more mature, but doesn't (as of Jan 2024) have push-to-talk, which I find more pleasant to use.
