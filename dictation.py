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
import sounddevice as sd

# ! you can change this rec_key value
rec_key = pynput.keyboard.Key.ctrl_r

whisper_samplerate = 16000  # sampling rate that whisper uses
recording_samplerate = 48000  # multiple of whisper_samplerate, widely supported

controller = pynput.keyboard.Controller()

# %% parse args
parser = argparse.ArgumentParser()
parser.add_argument("engine", choices=["local", "remote"])
parser.add_argument("language", nargs="?", default=None)
parser.add_argument("--no-type-using-clipboard", action="store_true")
# add a command to be run on after model load
parser.add_argument("--on-callback", type=str, default=None)
# turn off automatically after some time
parser.add_argument("--auto-off-time", type=int, default=None)
# add a command to be run on after model load
parser.add_argument("--model", type=str, default="large-v3")
args = parser.parse_args()

command_words = ["engage", "kurde", "kurda"]

# %% local or remote
if args.engine == "local":
    from faster_whisper import WhisperModel

    model = WhisperModel(args.model, device="cuda", compute_type="float16")
    # int8 is said to have worse accuracy and be slower
elif args.engine == "remote":
    import soundfile
    from openai import OpenAI

    client = OpenAI()
else:
    raise ValueError("Specify whether to use local or remote engine")

if args.on_callback is not None:
    subprocess.run(args.on_callback, shell=True)


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

    # # ! get context
    # if not args.no_grab_context:
    #     context = get_context()
    #     # limit the length of context
    #     context = context[-args.context_limit_chars :]
    context = None

    # ! transcribe
    if args.engine == "local":
        text = get_text_local(recorded_audio, context)
    elif args.engine == "remote":
        text = get_text_remote(recorded_audio, context)
    print(text)

    # ! check if it ends with a command word
    words = text.split(" ")
    use_command = False
    if words and any(cmd_word in words[-1].lower() for cmd_word in command_words):
        # last word was a command word
        use_command = True
        text = " ".join(words[:-1])

    # ! type that text
    text = text + " "
    if not args.no_type_using_clipboard:
        type_using_clipboard(text)
    else:
        controller.type(text)
        # subprocess.run(["ydotool", "type", "--key-delay=0", "--key-hold=0", text])
        # note: ydotool on x11 correctly outputs polish chars and types in terminal

    # ! use command
    if use_command:
        controller.press(pynput.keyboard.Key.enter)
        controller.release(pynput.keyboard.Key.enter)


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
            ):
                print("Auto off")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting...")

# %% play around with getting window titles
# # requires pip install python-xlib and I think xorg stuff
# # on wayland it fails for many windows (f.e. terminal, dolphin)
# # on x11 it works
# from Xlib import display


# def get_window_class():
#     d = display.Display()
#     window_id = d.get_input_focus().focus.id
#     window = d.create_resource_object("window", window_id)
#     return window.get_wm_class()[0]
