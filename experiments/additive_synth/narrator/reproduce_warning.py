import os
import sys

# Add the directory to sys.path so we can import narrator
sys.path.append('/home/invisible/projects/grpc-whisper-transcription/experiments/additive_synth/kokoro')

print("Importing narrator...")
try:
    import narrator
    print("Import successful")
except Exception as e:
    print(f"Import failed: {e}")
