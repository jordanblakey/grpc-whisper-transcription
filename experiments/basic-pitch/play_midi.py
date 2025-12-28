from midi2audio import FluidSynth
import time
import sys

# Instantiate the FluidSynth player (it handles a default sound font)
fs = FluidSynth()

args = sys.argv

if len(args) != 2:
    print("Usage: python play_midi.py <midi_file>")
    sys.exit(1)

# Play the MIDI file directly
print("Playing input.mid...")
fs.play_midi(args[1])

# Note: play_midi() blocks the process while playing.
# For background playback or more control, you would use 
# midi_to_audio() to create a WAV file and play that instead.
