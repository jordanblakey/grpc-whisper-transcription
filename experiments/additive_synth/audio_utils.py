import contextlib
import os
import sys
import wave
import numpy as np

@contextlib.contextmanager
def no_alsa_error():
    # Suppress warnings from pyaudio startup
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        old_stderr = os.dup(2)
        sys.stderr.flush()
        os.dup2(devnull, 2)
        os.close(devnull)
        yield
    finally:
        os.dup2(old_stderr, 2)
        os.close(old_stderr)

def save_buffer_as_wave(buffer, filename="recordings/output.wav"):
    # Convert to 16-bit integer PCM for standard WAV compatibility
    data = np.concatenate(buffer)
    data = np.clip(data, -1.0, 1.0)
    samples = (data * 32767).astype(np.int16)
    
    with wave.open(filename, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(48000)
        f.writeframes(samples.tobytes())

