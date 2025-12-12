This folder contains the script which aims to disable the local model when it is not active for some time. And then on demand load it back.

---------

In case of local running `dictation_auto_off.py` uses evdev which only works on Linux. For Windows and Mac you can try `_lagacy_dictation_auto_off_pynput.py`, which uses pynput. (Modify `run_dictation_auto_off.sh`.)


Pynput works on all systems, but does not work on Wayland.

Evdev works with both Wayland and X11, supports special characters, but only works on Linux.

Ydotool works with both Wayland and X11, but does not support special characters. Maybe it would be possible to make ydotool trigger pasting.