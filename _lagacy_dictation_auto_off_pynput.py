# %%
# import os
# os.environ['LD_LIBRARY_PATH'] = "/home/filip/projects/whisper-rt/venv_faster/lib/python3.11/site-packages/nvidia/cublas/lib:/home/filip/projects/whisper-rt/venv_faster/lib/python3.11/site-packages/nvidia/cudnn/lib"
import argparse
import subprocess
import threading
import time

import numpy as np
import pynput
import pyperclip
import requests
import sounddevice as sd

# from dictation import get_context, type_using_clipboard

# ! you can change this rec_key value
rec_key = pynput.keyboard.Key.ctrl_r

whisper_samplerate = 16000  # sampling rate that whisper uses
recording_samplerate = 48000  # multiple of whisper_samplerate, widely supported

server_url = 'http://0.0.0.0:5900'

controller = pynput.keyboard.Controller()

# %% parse args
parser = argparse.ArgumentParser()
parser.add_argument("language", nargs="?", default=None)
parser.add_argument("--no-grab-context", action="store_true")
parser.add_argument("--no-type-using-clipboard", action="store_true")
parser.add_argument("--context-limit-chars", type=int, default=300)
# add a command to be run on after model load
parser.add_argument("--on-callback", type=str, default=None)
# add a command to be run on after model unload
parser.add_argument("--off-callback", type=str, default=None)
# turn off automatically after some time
parser.add_argument("--auto-off-time", type=int, default=None)
# add a command to be run on after model load
parser.add_argument("--model", type=str, default="large-v3")
args = parser.parse_args()


# start a server process
engine = subprocess.Popen(["python", "engine.py", args.model])
if args.on_callback is not None:
    subprocess.run(args.on_callback, shell=True)



# %%

def get_context():
    # use pynput to type ctrl+shift+home, and then ctrl+c, and then right arrow
    # fisrt clear the clipboard in case getting context fails
    pyperclip.copy("")
    # ctrl+shift+home
    controller.press(pynput.keyboard.Key.ctrl_l)
    controller.press(pynput.keyboard.Key.shift_l)
    controller.press(pynput.keyboard.Key.home)
    controller.release(pynput.keyboard.Key.home)
    controller.release(pynput.keyboard.Key.shift_l)
    controller.release(pynput.keyboard.Key.ctrl_l)
    # ctrl+c
    controller.press(pynput.keyboard.Key.ctrl_l)
    controller.press("c")
    controller.release("c")
    controller.release(pynput.keyboard.Key.ctrl_l)
    # right arrow
    controller.press(pynput.keyboard.Key.right)
    controller.release(pynput.keyboard.Key.right)
    # get clipboard
    clipboard = pyperclip.paste()
    if clipboard == "":
        print("Warning: context is empty")
    return clipboard


def type_using_clipboard(text):
    # use pynput to type ctrl+shift+v
    pyperclip.copy(text)
    controller.press(pynput.keyboard.Key.ctrl_l)
    controller.press(pynput.keyboard.Key.shift_l)
    controller.press("v")
    controller.release("v")
    controller.release(pynput.keyboard.Key.shift_l)
    controller.release(pynput.keyboard.Key.ctrl_l)


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

    # ! get context
    if not args.no_grab_context:
        context = get_context()
        # limit the length of context
        context = context[-args.context_limit_chars :]
    else:
        context = None
    # print(context)

    # # ! transcribe
    payload = {
        "audio": recorded_audio.tolist(),
        "context": context
    }
    
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
        print(f"Error transcribing audio: {response_data.get('error', 'Unknown error')}")

    # ! type that text
    text = text + " "
    if not args.no_type_using_clipboard:
        type_using_clipboard(text)
    else:
        controller.type(text)
        # subprocess.run(["ydotool", "type", "--key-delay=0", "--key-hold=0", text])
        # note: ydotool on x11 correctly outputs polish chars and types in terminal


def on_press(key):
    global rec_key_pressed
    # print("pressed", key)
    if key == rec_key:
        rec_key_pressed = True

        # start recording in a new thread
        t = threading.Thread(target=record_and_process)
        t.start()


def on_release(key):
    global rec_key_pressed, time_last_used
    # print("released", key)
    if key == rec_key:
        rec_key_pressed = False
        time_last_used = time.time()


# %%
if args.language is not None:
    print(f"Using language: {args.language}")
with pynput.keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
    print(f"Press {rec_key} to start recording")
    try:
        # listener.join()
        while listener.is_alive():
            if (
                args.auto_off_time is not None
                and time.time() - time_last_used > args.auto_off_time
                and rec_key_pressed is False
                and engine.poll() is None
            ):
                print("Auto off")
                # shut down the server
                engine.terminate()

                if args.off_callback is not None:
                    subprocess.run(args.off_callback, shell=True)

            time.sleep(1)
    except KeyboardInterrupt:
        if args.off_callback is not None:
            subprocess.run(args.off_callback, shell=True)
        print("\nExiting...")
