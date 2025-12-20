import pyaudio
import wave

import signal
import sys

from audio_utils import no_alsa_err

CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
# RECORD_SECONDS = 5
WAVE_OUTPUT_FILENAME = "output.wav"

is_recording = True

def signal_handler(sig, frame):
    global is_recording
    print("\nInterrupt received, stopping recording...")
    is_recording = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

with no_alsa_err():
    p = pyaudio.PyAudio()

print("Recording...")

stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

frames = []

# for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
while is_recording:
    data = stream.read(CHUNK)
    frames.append(data)

print("Finished recording")

stream.stop_stream()
stream.close()
p.terminate()

wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
wf.setnchannels(CHANNELS)
wf.setsampwidth(p.get_sample_size(FORMAT))
wf.setframerate(RATE)
wf.writeframes(b''.join(frames))
wf.close()