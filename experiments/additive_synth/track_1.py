import time

import numpy as np
import pyaudio

from wave_generator import Wave
from audio_utils import save_buffer_as_wave, no_alsa_error

with no_alsa_error():
    p = pyaudio.PyAudio()

stream = p.open(format=pyaudio.paFloat32,
                channels=1,
                rate=48000,
                output=True)

buffer = []

buffer.append(Wave(hz=110, amp=1.0, duration=0.1).sine())
buffer.append(Wave(hz=220, amp=1.0, duration=0.1).sine())
buffer.append(Wave(hz=440, amp=1.0, duration=0.1).sine())

buffer.append(Wave(hz=110, amp=1.0, duration=0.2).square())
buffer.append(Wave(hz=220, amp=1.0, duration=0.2).square())
buffer.append(Wave(hz=440, amp=1.0, duration=0.2).square())

buffer.append(Wave(hz=110, amp=1.0, duration=0.3).triangle())
buffer.append(Wave(hz=220, amp=1.0, duration=0.3).triangle())
buffer.append(Wave(hz=440, amp=1.0, duration=0.3).triangle())

buffer.append(Wave(hz=110, amp=1.0, duration=0.4).sawtooth())
buffer.append(Wave(hz=220, amp=1.0, duration=0.4).sawtooth())
buffer.append(Wave(hz=440, amp=1.0, duration=0.4).sawtooth())

# play audio immediately
stream.write(np.concatenate(buffer).astype(np.float32).tobytes())

# save audio to .wav file
save_buffer_as_wave(buffer, "recordings/track_1.wav")

time.sleep(.01) # prevent chirp
stream.stop_stream()
stream.close()
p.terminate()