"""
Streaming mic dictation using Kyutai STT 1B.
Press Scroll Lock to start/stop dictation (global hotkey).
Transcribed text is typed into the focused window via xdotool.

Requirements: pip install moshi sounddevice pynput
              xdotool (apt install xdotool / pacman -S xdotool)
Usage: python mic_stt.py
"""

import subprocess
import sys
import queue
import numpy as np
import sounddevice as sd
import torch
from pynput import keyboard
from moshi.models import loaders, LMGen

HF_REPO = "kyutai/stt-1b-en_fr"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
TOGGLE_KEY = keyboard.Key.scroll_lock


def type_text(text):
    """Type text into focused window using xdotool."""
    if text:
        subprocess.run(
            ["xdotool", "type", "--clearmodifiers", "--delay", "0", text],
            check=False,
        )


def main():
    print(f"[*] Loading model on {DEVICE}...", file=sys.stderr)

    checkpoint_info = loaders.CheckpointInfo.from_hf_repo(HF_REPO)
    mimi = checkpoint_info.get_mimi(device=DEVICE)
    text_tokenizer = checkpoint_info.get_text_tokenizer()
    lm = checkpoint_info.get_moshi(device=DEVICE)
    stt_config = checkpoint_info.stt_config
    lm_gen = LMGen(lm, cfg_coef=1.0, **checkpoint_info.lm_gen_config)

    sample_rate = mimi.sample_rate
    frame_size = int(sample_rate / mimi.frame_rate)

    audio_q: queue.Queue[np.ndarray] = queue.Queue()
    active = False

    def on_press(key):
        nonlocal active
        if key == TOGGLE_KEY:
            active = not active
            if active:
                sys.stderr.write("\r[LISTENING]\n")
            else:
                sys.stderr.write("\r[PAUSED]\n")
            sys.stderr.flush()

    def mic_callback(indata, frames, time_info, status):
        if status:
            print(f"[mic] {status}", file=sys.stderr)
        audio_q.put(indata[:, 0].copy())

    flush_frames = int(stt_config.get("audio_delay_seconds", 0.5) * mimi.frame_rate) + 2

    def flush_pipeline():
        for _ in range(flush_frames):
            silence = torch.zeros(1, 1, frame_size, device=DEVICE)
            codes = mimi.encode(silence)
            tokens = lm_gen.step(codes)
            if tokens is None:
                continue
            text_token = tokens[0, 0].item()
            if text_token not in (0, 3):
                piece = text_tokenizer.id_to_piece(text_token)
                piece = piece.replace("▁", " ")
                type_text(piece)
                sys.stdout.write(piece)
                sys.stdout.flush()

    key_listener = keyboard.Listener(on_press=on_press)
    key_listener.start()

    print("[*] Model loaded. Press Scroll Lock to start/stop. Ctrl+C to quit.\n",
          file=sys.stderr)

    with torch.no_grad():
        mimi.streaming_forever(1)
        lm_gen.streaming_forever(1)

        pad_left_sec = stt_config.get("audio_silence_prefix_seconds", 0.0)
        pad_left_frames = int(pad_left_sec * mimi.frame_rate)
        for _ in range(pad_left_frames):
            silence = torch.zeros(1, 1, frame_size, device=DEVICE)
            codes = mimi.encode(silence)
            lm_gen.step(codes)

        first_real_frame = True
        was_active = False

        try:
            with sd.InputStream(
                samplerate=sample_rate,
                channels=1,
                blocksize=frame_size,
                callback=mic_callback,
            ):
                buf = np.zeros(0, dtype=np.float32)

                while True:
                    if not active:
                        if was_active:
                            flush_pipeline()
                            was_active = False
                        try:
                            audio_q.get(timeout=0.1)
                        except queue.Empty:
                            pass
                        continue

                    was_active = True

                    try:
                        chunk = audio_q.get(timeout=0.1)
                    except queue.Empty:
                        continue

                    buf = np.concatenate([buf, chunk])

                    while len(buf) >= frame_size:
                        frame_np = buf[:frame_size]
                        buf = buf[frame_size:]

                        frame = torch.from_numpy(frame_np).float().to(DEVICE)
                        frame = frame.view(1, 1, frame_size)

                        codes = mimi.encode(frame)

                        if first_real_frame:
                            lm_gen.step(codes)
                            first_real_frame = False

                        tokens = lm_gen.step(codes)
                        if tokens is None:
                            continue

                        text_token = tokens[0, 0].item()
                        if text_token not in (0, 3):
                            piece = text_tokenizer.id_to_piece(text_token)
                            piece = piece.replace("▁", " ")
                            type_text(piece)
                            sys.stdout.write(piece)
                            sys.stdout.flush()

        except KeyboardInterrupt:
            pass

    key_listener.stop()
    print("\n\n[*] Stopped.", file=sys.stderr)


if __name__ == "__main__":
    main()
