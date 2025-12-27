
import os
import subprocess
import time
import sys

args = sys.argv
if len(args) > 1:
    directory = args[1]
else:
    directory = "generated_audio"

def play_audio_files(directory):
    if not os.path.exists(directory):
        print(f"Directory '{directory}' does not exist.")
        return

    files = [f for f in os.listdir(directory) if f.endswith(".wav")]
    files.sort()  # Play in alphabetical order

    if not files:
        print(f"No .wav files found in '{directory}'.")
        return

    print(f"Found {len(files)} audio files. Playing...")

    for filename in files:
        filepath = os.path.join(directory, filename)
        print(f"Playing: {filename}")
        
        try:
            # Using aplay (ALSA player) since it was found on the system
            subprocess.run(["aplay", filepath], check=True)
            time.sleep(0.5) # Short pause between files
        except subprocess.CalledProcessError as e:
            print(f"Error playing {filename}: {e}")
        except FileNotFoundError:
            print("Error: 'aplay' command not found. Please ensure ALSA utils are installed.")
            break
        except KeyboardInterrupt:
            print("\nPlayback stopped by user.")
            sys.exit(0)

if __name__ == "__main__":
    play_audio_files(directory)
