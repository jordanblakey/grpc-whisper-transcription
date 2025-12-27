import time
import numpy as np
from wave_generator import Wave
from narrator import narrate
from audio_utils import no_alsa_error

from effects import amplitude_envelope

import pyaudio

with no_alsa_error():
    p = pyaudio.PyAudio()

stream = p.open(format=pyaudio.paFloat32,
                channels=1,
            rate=48000,
            output=True)

def play_buffer(buffer, clear=True):
    stream.write(np.concatenate(buffer).astype(np.float32).tobytes())
    if clear:
        buffer.clear()

def main():
    buffer = []
    
    narrate("An amplitude envelope is a filter that creates smooth transitions between amplitudes over time.")
    narrate("We can use it to manipulate the attack, sustain, release and decay characteristics of a sound.")

    narrate("For reference, here is an unmodified 440 hertz sine wave.")
    wave = Wave(hz=440, amp=1.0, duration=3.0).sine()
    buffer.append(wave)
    play_buffer(buffer)
    time.sleep(.5)

    narrate("Now, let's add an amplitude envelope, with a 1000 millisecond fade in and fade out.")
    envelope_wave = amplitude_envelope(wave, fade_in_ms=1000, fade_out_ms=1000)
    buffer.append(envelope_wave)
    play_buffer(buffer)
    narrate("As you can hear, the sound now smoothly transitions between silence and full amplitude.")
    time.sleep(.5)

    narrate("Let's try a 200 millisecond fade in, and a longer, 2000 millisecond fade out.")
    wave = Wave(hz=440, amp=1.0, duration=3.0).sine()
    envelope_wave = amplitude_envelope(wave, fade_in_ms=200, fade_out_ms=2000)
    buffer.append(envelope_wave)
    play_buffer(buffer)
    narrate("Basically, we can use the envelope to shape the attack and release of a sound.")
    time.sleep(.5)


if __name__ == "__main__":
    main()
    stream.stop_stream()
    stream.close()
    p.terminate()
