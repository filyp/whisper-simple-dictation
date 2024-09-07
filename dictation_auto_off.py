# %%
# import os
# os.environ['LD_LIBRARY_PATH'] = "/home/filip/projects/whisper-rt/venv_faster/lib/python3.11/site-packages/nvidia/cublas/lib:/home/filip/projects/whisper-rt/venv_faster/lib/python3.11/site-packages/nvidia/cudnn/lib"
import argparse
import subprocess
import threading
import time

import numpy as np
import pyperclip
import requests
import sounddevice as sd

# from dictation import get_context, type_using_clipboard

import evdev
from evdev import UInput, ecodes as e
from select import select

# ! you can change this rec_key value
rec_key = "KEY_RIGHTCTRL"

whisper_samplerate = 16000  # sampling rate that whisper uses
recording_samplerate = 48000  # multiple of whisper_samplerate, widely supported

server_url = "http://0.0.0.0:5900"

devices = [evdev.InputDevice(fn) for fn in evdev.list_devices()]
keyboards = [d for d in devices if rec_key in str(d.capabilities(verbose=True))]

writer = UInput()
time.sleep(1)

# %% parse args
parser = argparse.ArgumentParser()
parser.add_argument("language", nargs="?", default=None)
# add a command to be run on after model load
parser.add_argument("--on-callback", type=str, default=None)
# add a command to be run on after model unload
parser.add_argument("--off-callback", type=str, default=None)
# turn off automatically after some time
parser.add_argument("--auto-off-time", type=int, default=None)
# add a command to be run on after model load
parser.add_argument("--model", type=str, default="large-v3")
# name of the recording device to use as returned by sd.query_devices()
parser.add_argument("--recording-device", type=str, default=None)
args = parser.parse_args()

if args.recording_device is None:
    device_index = None
else:
    device_info = sd.query_devices()
    device_index = None
    for device in device_info:
        if args.recording_device in device['name'] and device['max_input_channels'] > 0:
            device_index = device["index"]
            break
    assert device_index is not None, "Couldn't find specified sound device"

# mock engine process
engine = subprocess.Popen(["echo", "mock engine"])

# %%

# def get_context():
#     # use pynput to type ctrl+shift+home, and then ctrl+c, and then right arrow
#     # fisrt clear the clipboard in case getting context fails
#     pyperclip.copy("")
#     # ctrl+shift+home
#     controller.press(pynput.keyboard.Key.ctrl_l)
#     controller.press(pynput.keyboard.Key.shift_l)
#     controller.press(pynput.keyboard.Key.home)
#     controller.release(pynput.keyboard.Key.home)
#     controller.release(pynput.keyboard.Key.shift_l)
#     controller.release(pynput.keyboard.Key.ctrl_l)
#     # ctrl+c
#     controller.press(pynput.keyboard.Key.ctrl_l)
#     controller.press("c")
#     controller.release("c")
#     controller.release(pynput.keyboard.Key.ctrl_l)
#     # right arrow
#     controller.press(pynput.keyboard.Key.right)
#     controller.release(pynput.keyboard.Key.right)
#     # get clipboard
#     clipboard = pyperclip.paste()
#     if clipboard == "":
#         print("Warning: context is empty")
#     return clipboard


def type_using_clipboard(text):
    pyperclip.copy(text)
    # use evdev to type ctrl+shift+v
    time.sleep(0.01)
    writer.write(e.EV_KEY, e.KEY_LEFTCTRL, 1)
    writer.write(e.EV_KEY, e.KEY_LEFTSHIFT, 1)
    writer.write(e.EV_KEY, e.KEY_V, 1)
    writer.write(e.EV_KEY, e.KEY_V, 0)
    writer.write(e.EV_KEY, e.KEY_LEFTSHIFT, 0)
    writer.write(e.EV_KEY, e.KEY_LEFTCTRL, 0)
    writer.syn()


# %%
rec_key_pressed = False
time_last_used = time.time()


def record_and_process():
    global engine

    # ! start the engine if not running
    if engine.poll() is not None:
        # clean up the old process
        print("Starting engine")
        engine = subprocess.Popen(["python", "engine.py", args.model])
        if args.on_callback is not None:
            subprocess.run(args.on_callback, shell=True)

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
        device=device_index,
    )
    stream.start()
    while rec_key_pressed:
        time.sleep(0.005)
    stream.stop()
    stream.close()
    recorded_audio = np.concatenate(audio_chunks)[:, 0]

    # ! check if not too short
    duration = len(recorded_audio) / recording_samplerate
    if duration <= 0.1:
        print("Recording too short, skipping")
        return

    # ! downsample
    # scipy resampling was much too slow (hundreds of ms)
    # leave in only every 3rd sample, using numpy
    recorded_audio = recorded_audio[::3]

    # # ! get context
    # if not args.no_grab_context:
    # context = get_context()
    # # limit the length of context
    # context = context[-args.context_limit_chars :]
    context = None

    # ! transcribe
    payload = {"audio": recorded_audio.tolist(), "context": context}

    # note that the server can be intializing, so have the post try until it works
    while True:
        try:
            response = requests.post(server_url + "/transcribe", json=payload)
            break
        except requests.exceptions.ConnectionError:
            time.sleep(0.1)
            print("Connection error, retrying...")

    response_data = response.json()

    if response.status_code == 200:
        text = response_data.get("text", "")
        print(text)
    else:
        print(
            f"Error transcribing audio: {response_data.get('error', 'Unknown error')}"
        )
        return

    # ! type that text
    text = text + " "
    type_using_clipboard(text)
    # print(text)


# %%

# read any keypress
try:
    while True:
        r, _, _ = select(keyboards, [], [], 1)
        for event in (event for dev in r for event in dev.read()):
            # check if rec_key
            if event.code != evdev.ecodes.ecodes[rec_key]:
                continue
            if event.value == 1:
                rec_key_pressed = True
                # start recording in a new thread
                t = threading.Thread(target=record_and_process)
                t.start()

            elif event.value == 0:
                rec_key_pressed = False
                time_last_used = time.time()

        # check if we should shut down the engine
        if (
            engine.poll() is None
            and args.auto_off_time is not None
            and time.time() - time_last_used > args.auto_off_time
            and rec_key_pressed is False
        ):
            print("Auto off")
            # shut down the server
            engine.terminate()

            if args.off_callback is not None:
                subprocess.run(args.off_callback, shell=True)

except KeyboardInterrupt:
    print("\nExiting...")
    engine.terminate()
    writer.close()

    if args.off_callback is not None:
        subprocess.run(args.off_callback, shell=True)
