import time

import numpy as np
import scipy.signal
import pyaudio
from librosa.effects import pitch_shift
from scipy.interpolate import CubicSpline

from narrator import narrate

from wave_generator import Wave
from audio_utils import save_buffer_as_wave, no_alsa_error

with no_alsa_error():
    p = pyaudio.PyAudio()

stream = p.open(format=pyaudio.paFloat32,
                channels=1,
            rate=48000,
            output=True)

def main():
    buffer = []

    narrate("This is a 440 hertz sine wave.")
    w1 = Wave(hz=440, amp=1.0, duration=1).sine()
    buffer.append(w1)
    play_buffer(buffer)
    time.sleep(1)
    
    narrate("Now, let's resample it to a higher pitch. This basically squashes the waveform horizontally, making it shorter.")
    interval_ratio = 2**(4/12)  # Major third ratio
    int(len(w1) / interval_ratio)
    buffer.append(scipy.signal.resample(w1, int(len(w1) / interval_ratio)))
    play_buffer(buffer)
    time.sleep(1)

    narrate("This particular musical interval, or ratio between 2 frequencies, is called a major third.")
    narrate("Let's hear them together.")
    buffer.append(Wave(hz=440, amp=1.0, duration=1).sine())
    buffer.append(Wave(hz=440 * 2 ** (4/12), amp=1.0, duration=1).sine())
    play_buffer(buffer)
    time.sleep(1)

    interval_names = [
        "unison",
        "minor 2nd",
        "major 2nd",
        "minor 3rd",
        "major 3rd",
        "perfect 4th",
        "tritone",
        "perfect 5th",
        "minor 6th",
        "major 6th",
        "minor 7th",
        "major 7th",
        "octave"
    ]
    narrate(f"There are 12 of these intervals in an octave.")
    narrate("Let's hear them.")
    for i, interval_name in enumerate(interval_names):
        narrate(f"{interval_name}")
        buffer.append(Wave(hz=440, duration=.5).sine())
        buffer.append(np.zeros(int(100)))
        buffer.append(Wave(hz=int(440 * 2 ** (i/12)), duration=.5).sine())
        play_buffer(buffer)
        time.sleep(.1)

    narrate("Combining intervals in a sequence creates a melody.")
    narrate("Perhaps you will recognize this one.")

    buffer.append(Wave(hz=int(440* 2 ** (0/12)), amp=1.0, duration=0.30).triangle())
    buffer.append(np.zeros(int(500)))
    buffer.append(Wave(hz=int(440* 2 ** (0/12)), amp=1.0, duration=0.15).triangle())
    buffer.append(np.zeros(int(500)))
    buffer.append(Wave(hz=int(440 * 2 ** (5/12)), amp=1.0, duration=1.0).triangle())
    buffer.append(np.zeros(int(500)))
    buffer.append(Wave(hz=int(440 * 2 ** (12/12)), amp=1.0, duration=1.0).triangle())

    buffer.append(np.zeros(int(500)))
    buffer.append(Wave(hz=int(440 * 2 ** (10/12)), amp=1.0, duration=0.15).triangle())
    buffer.append(np.zeros(int(500)))
    buffer.append(Wave(hz=int(440 * 2 ** (9/12)), amp=1.0, duration=0.15).triangle())
    buffer.append(np.zeros(int(500)))
    buffer.append(Wave(hz=int(440 * 2 ** (7/12)), amp=1.0, duration=0.15).triangle())

    buffer.append(np.zeros(int(500)))
    buffer.append(Wave(hz=int(440 * 2 ** (17/12)), amp=1.0, duration=1.0).triangle())
    buffer.append(np.zeros(int(500)))
    buffer.append(Wave(hz=int(440 * 2 ** (12/12)), amp=1.0, duration=0.5).triangle())

    buffer.append(np.zeros(int(500)))
    buffer.append(Wave(hz=int(440 * 2 ** (10/12)), amp=1.0, duration=0.15).triangle())
    buffer.append(np.zeros(int(500)))
    buffer.append(Wave(hz=int(440 * 2 ** (9/12)), amp=1.0, duration=0.15).triangle())
    buffer.append(np.zeros(int(500)))
    buffer.append(Wave(hz=int(440 * 2 ** (7/12)), amp=1.0, duration=0.15).triangle())

    buffer.append(np.zeros(int(500)))
    buffer.append(Wave(hz=int(440 * 2 ** (17/12)), amp=1.0, duration=1.0).triangle())
    buffer.append(np.zeros(int(500)))
    buffer.append(Wave(hz=int(440 * 2 ** (12/12)), amp=1.0, duration=0.5).triangle())

    buffer.append(np.zeros(int(500)))
    buffer.append(Wave(hz=int(440 * 2 ** (10/12)), amp=1.0, duration=0.15).triangle())
    buffer.append(np.zeros(int(500)))
    buffer.append(Wave(hz=int(440 * 2 ** (9/12)), amp=1.0, duration=0.15).triangle())
    buffer.append(np.zeros(int(500)))
    buffer.append(Wave(hz=int(440 * 2 ** (10/12)), amp=1.0, duration=0.15).triangle())
    buffer.append(np.zeros(int(500)))
    buffer.append(Wave(hz=int(440 * 2 ** (7/12)), amp=1.0, duration=1.00).triangle())

    play_buffer(buffer)
    time.sleep(.5)

    time.sleep(.01) # prevent chirp
    stream.stop_stream()
    stream.close()
    p.terminate()


def play_buffer(buffer, clear=True):
    stream.write(np.concatenate(buffer).astype(np.float32).tobytes())
    if clear:
        buffer.clear()

if __name__ == "__main__":
    main()