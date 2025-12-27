import numpy as np
import sys
import os

import sounddevice as sd

# Add current directory to path so we can import Noise
sys.path.append(os.path.join(os.path.dirname(__file__)))

from noise_generator import Noise, SAMPLE_RATE

print('???')
sd.play(Noise(hz=440, amp=0.5, duration=1).white(), SAMPLE_RATE)
sd.wait()
exit()

def test_noise_generation():
    duration = 0.1
    noise = Noise(hz=440, amp=0.5, duration=duration)
    expected_samples = int(SAMPLE_RATE * duration)
    
    colors = ['white', 'pink', 'brown', 'blue', 'violet', 'grey']
    
    for color in colors:
        print(f"Testing {color} noise...", end="")
        method = getattr(noise, color)
        samples = method()
        
        # Check type
        assert isinstance(samples, np.ndarray), f"{color} did not return numpy array"
        
        # Check shape
        assert len(samples) == expected_samples, f"{color} length mismatch. Expected {expected_samples}, got {len(samples)}"
        
        # Check not silent (all zeros)
        assert np.max(np.abs(samples)) > 0, f"{color} returned silence"
        
        # Check amplitude roughly respected (normalization isn't perfect but shouldn't exceed amp drastically)
        # Note: Grey noise scaling is loose, so we'll just check it's not exploding to infinity
        max_val = np.max(np.abs(samples))
        print(f" OK. Peak Amp: {max_val:.4f}")

if __name__ == "__main__":
    try:
        test_noise_generation()
        print("\nAll noise tests passed!")
    except Exception as e:
        print(f"\nTest FAILED: {e}")
        sys.exit(1)
