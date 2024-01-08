# %%
# import os
# os.environ['LD_LIBRARY_PATH'] = "/home/filip/projects/whisper-rt/venv_faster/lib/python3.11/site-packages/nvidia/cublas/lib:/home/filip/projects/whisper-rt/venv_faster/lib/python3.11/site-packages/nvidia/cudnn/lib"
import sys
import threading
import time

import numpy as np
import pynput
import sounddevice as sd
from faster_whisper import WhisperModel

# ! tweak these values
rec_key = pynput.keyboard.Key.ctrl_r
language = sys.argv[1] if len(sys.argv) > 1 else "en"


model = WhisperModel("large-v3", device="cuda", compute_type="float16")
# int8 is said to have worse accuracy and be slower
fs = 16000  # what whisper uses

controller = pynput.keyboard.Controller()


# %%
def get_text(audio):
    segments, info = model.transcribe(audio, beam_size=5, language=language)
    segments = list(segments)
    text = " ".join([segment.text.strip() for segment in segments])
    return text


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
        samplerate=fs,
        channels=1,
        blocksize=256,
        callback=audio_callback,
    )
    stream.start()
    while rec_key_pressed:
        time.sleep(0.005)
    stream.stop()

    recorded_audio = np.concatenate(audio_chunks)[:, 0]

    # ! transcribe
    text = get_text(recorded_audio)
    print(text)

    # ! type that text
    controller.type(text + " ")


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


with pynput.keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    print(f"Press {rec_key} to start recording")
    try:
        listener.join()
    except KeyboardInterrupt:
        print("\nExiting...")


# %%
# sd.play(audio_to_process, fs)
