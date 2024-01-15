# %%
# import os
# os.environ['LD_LIBRARY_PATH'] = "/home/filip/projects/whisper-rt/venv_faster/lib/python3.11/site-packages/nvidia/cublas/lib:/home/filip/projects/whisper-rt/venv_faster/lib/python3.11/site-packages/nvidia/cudnn/lib"
import sys
import threading
import time
import subprocess

import numpy as np
import pynput
import sounddevice as sd

# ! tweak these values
rec_key = pynput.keyboard.Key.ctrl_r

whisper_samplerate = 16000  # sampling rate that whisper uses
recording_samplerate = 48000  # multiple of whisper_samplerate, widely supported

# %% choose typing method
ydotool_is_installed = (
    subprocess.run(["ydotool"], stdout=subprocess.DEVNULL).returncode == 0
)
ydotool_is_installed = False
if ydotool_is_installed:
    print("Using ydotool for typing")
else:
    controller = pynput.keyboard.Controller()
    print("Using pynput for typing")

# %% parse args
engine = sys.argv[1]
language = sys.argv[2] if len(sys.argv) > 2 else None
# note: supplying language improves accuracy and latency

# %% local or remote
if engine == "local":
    from faster_whisper import WhisperModel

    model = WhisperModel("large-v3", device="cuda", compute_type="float16")
    # int8 is said to have worse accuracy and be slower
elif engine == "remote":
    import soundfile
    from openai import OpenAI

    client = OpenAI()
else:
    raise ValueError("Specify whether to use local or remote engine")


# %%
def get_text_local(audio):
    segments, info = model.transcribe(audio, beam_size=5, language=language)
    segments = list(segments)
    text = " ".join([segment.text.strip() for segment in segments])
    return text


def get_text_remote(audio):
    tmp_audio_filename = "tmp.wav"
    soundfile.write(tmp_audio_filename, audio, whisper_samplerate, format="wav")
    # print(time.time())
    api_response = client.audio.transcriptions.create(
        model="whisper-1",
        file=open(tmp_audio_filename, "rb"),
        language=language,
    )
    # print(time.time())
    return api_response.text


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

    # ! transcribe
    if engine == "local":
        text = get_text_local(recorded_audio)
    elif engine == "remote":
        text = get_text_remote(recorded_audio)
    print(text)

    # ! type that text
    text = text + " "
    if ydotool_is_installed:
        subprocess.run(["ydotool", "type", "--key-delay=0", "--key-hold=0", text])
    else:
        controller.type(text)


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
if language is not None:
    print(f"Using language: {language}")
with pynput.keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    print(f"Press {rec_key} to start recording")
    try:
        listener.join()
    except KeyboardInterrupt:
        print("\nExiting...")


# %%
# sd.play(recorded_audio, recording_samplerate)


# from pynput.keyboard import KeyCode


# controller = pynput.keyboard.Controller()
# controller.press(KeyCode.from_char('\u0105'))
# controller.release(KeyCode.from_char('\u0105'))

# %%
