# %%
# import os
# os.environ['LD_LIBRARY_PATH'] = "/home/filip/projects/whisper-rt/venv_faster/lib/python3.11/site-packages/nvidia/cublas/lib:/home/filip/projects/whisper-rt/venv_faster/lib/python3.11/site-packages/nvidia/cudnn/lib"
import argparse
import sys
import threading
import time

import numpy as np
import pynput
import pyperclip
import sounddevice as sd

# ! tweak these values
rec_key = pynput.keyboard.Key.ctrl_r

whisper_samplerate = 16000  # sampling rate that whisper uses
recording_samplerate = 48000  # multiple of whisper_samplerate, widely supported

# %% choose typing method
controller = pynput.keyboard.Controller()

# %% parse args
parser = argparse.ArgumentParser()
parser.add_argument("engine", choices=["local", "remote"])
parser.add_argument("language", nargs="?", default=None)
parser.add_argument("--no-grab-context", action="store_true")
parser.add_argument("--no-type-using-clipboard", action="store_true")
parser.add_argument("--context-limit-chars", type=int, default=500)
args = parser.parse_args()

# %% local or remote
if args.engine == "local":
    from faster_whisper import WhisperModel

    model = WhisperModel("large-v3", device="cuda", compute_type="float16")
    # int8 is said to have worse accuracy and be slower
elif args.engine == "remote":
    import soundfile
    from openai import OpenAI

    client = OpenAI()
else:
    raise ValueError("Specify whether to use local or remote engine")


# %%
def get_text_local(audio, context=None):
    segments, info = model.transcribe(
        audio, beam_size=5, language=args.language, initial_prompt=context
    )
    segments = list(segments)
    text = " ".join([segment.text.strip() for segment in segments])
    return text


def get_text_remote(audio, context=None):
    tmp_audio_filename = "tmp.wav"
    soundfile.write(tmp_audio_filename, audio, whisper_samplerate, format="wav")
    # print(time.time())
    api_response = client.audio.transcriptions.create(
        model="whisper-1",
        file=open(tmp_audio_filename, "rb"),
        language=args.language,
        prompt=context,
    )
    # print(time.time())
    return api_response.text


def get_context():
    # use pynput to type ctrl+shift+home, and then ctrl+c, and then right arrow
    controller.press(pynput.keyboard.Key.ctrl_l)
    controller.press(pynput.keyboard.Key.shift_l)
    controller.press(pynput.keyboard.Key.home)
    controller.release(pynput.keyboard.Key.home)
    controller.release(pynput.keyboard.Key.shift_l)
    controller.release(pynput.keyboard.Key.ctrl_l)

    controller.press(pynput.keyboard.Key.ctrl_l)
    controller.press("c")
    controller.release("c")
    controller.release(pynput.keyboard.Key.ctrl_l)

    controller.press(pynput.keyboard.Key.right)
    controller.release(pynput.keyboard.Key.right)

    return pyperclip.paste()


def type_using_clipboard(text):
    pyperclip.copy(text)
    controller.press(pynput.keyboard.Key.ctrl_l)
    controller.press("v")
    controller.release("v")
    controller.release(pynput.keyboard.Key.ctrl_l)


# %%
rec_key_pressed = False


def record_and_process():
    # ! record
    # while is pressed, record audio
    audio_chunks = []

    def audio_callback(indata, frames, time, status):
        if status:
            print("WARNING:", status)
        audio_chunks.append(indata.copy())

    stream = sd.InputStream(
        samplerate=recording_samplerate,
        channels=1,
        blocksize=256,
        callback=audio_callback,
    )
    stream.start()
    while rec_key_pressed:
        time.sleep(0.005)
    stream.stop()
    stream.close()
    recorded_audio = np.concatenate(audio_chunks)[:, 0]

    # ! downsample
    # scipy resampling was much too slow (hundreds of ms)
    # leave in only every 3rd sample, using numpy
    recorded_audio = recorded_audio[::3]

    # ! get context
    if not args.no_grab_context:
        context = get_context()
        # limit the length of context
        context = context[-args.context_limit_chars :]
    else:
        context = None
    # print(context)

    # ! transcribe
    if args.engine == "local":
        text = get_text_local(recorded_audio, context)
    elif args.engine == "remote":
        text = get_text_remote(recorded_audio, context)
    print(text)

    # ! type that text
    if not args.no_type_using_clipboard:
        type_using_clipboard(text)
    else:
        controller.type(text)
    controller.type(" ")


def on_press(key):
    global rec_key_pressed
    if key == rec_key:
        rec_key_pressed = True

        # start recording in a new thread
        t = threading.Thread(target=record_and_process)
        t.start()


def on_release(key):
    global rec_key_pressed
    if key == rec_key:
        rec_key_pressed = False


# %%
if args.language is not None:
    print(f"Using language: {args.language}")
with pynput.keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    print(f"Press {rec_key} to start recording")
    try:
        listener.join()
    except KeyboardInterrupt:
        print("\nExiting...")
