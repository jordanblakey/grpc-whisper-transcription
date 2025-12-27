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
    buffer.append(Wave(hz=440, amp=1.0, duration=1).sine())
    play_buffer(buffer)
    time.sleep(1)
    
    narrate("Now, let's try a square wave.")
    buffer.append(Wave(hz=440, amp=1.0, duration=1).square())
    play_buffer(buffer)
    time.sleep(1)

    narrate("We can also generate the samples for triangle and sawtooth waves with numpy.")
    buffer.append(Wave(hz=440, amp=1.0, duration=1).triangle())
    buffer.append(np.zeros(int(48000 / 2)))
    buffer.append(Wave(hz=440, amp=1.0, duration=1).sawtooth())
    play_buffer(buffer)
    time.sleep(1)

    narrate("Using simple math functions can create chirp effects, known as aliasing. Here's an example with a square wave.")
    buffer.append(Wave(hz=440).aliased_square())    
    play_buffer(buffer)
    time.sleep(1)
    
    narrate("To prevent aliasing, we can use a process called additive synthesis. Here's a square wave generated with additive synthesis.")
    
    buffer.append(Wave(hz=440, amp=1.0, duration=1).square())
    play_buffer(buffer)
    time.sleep(1)
    
    narrate("Notice how the square wave sounded much smoother?")

    stream.stop_stream()
    stream.close()
    p.terminate()


def play_buffer(buffer, clear=True):
    stream.write(np.concatenate(buffer).astype(np.float32).tobytes())
    if clear:
        buffer.clear()

if __name__ == "__main__":
    main()