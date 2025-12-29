import numpy as np
from audio_modules.effects import fade

SAMPLE_RATE = 48000

class Wave:
    def __init__(self, hz: int, amp: float = 1.0, duration: float = 1.0, delay: float = 0.0):
        self.hz = hz
        self.amp = amp
        self.nyquist = SAMPLE_RATE / 2
        self.t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
        self.phase = (self.t * self.hz) % 1.0
        self.delay = delay

    def __str__(self):
        return f"Wave(hz={self.hz}, amp={self.amp}, duration={self.t.shape[0] / SAMPLE_RATE}, delay={self.delay})"

    @property
    def duration(self):
        return self.t.shape[0] / SAMPLE_RATE

    @duration.setter
    def duration(self, value):
        self.t = np.linspace(0, value, int(SAMPLE_RATE * value), endpoint=False)
        self.phase = (self.t * self.hz) % 1.0

    def sine(self):
        samples = self.amp * np.sin(2 * np.pi * (self.t * self.hz))
        samples = fade(samples, ease_in="easeOutExpo", ease_out="easeOutExpo")
        samples = np.concatenate((np.zeros(int(self.delay * SAMPLE_RATE)), samples))
        return samples

    def triangle(self):
        samples = np.zeros_like(self.t)
        n = 1
        while (self.hz * n) < self.nyquist:
            harmonic_gain = ((-1)**((n-1)//2)) / (n**2)
            samples += harmonic_gain * np.sin(2 * np.pi * n * self.phase)
            n += 2
        gain = 10 ** (2 / 20)
        samples = samples * (8 / np.pi**2) * self.amp * gain
        samples = fade(samples, ease_in="easeOutExpo", ease_out="easeOutExpo")
        samples = np.concatenate((np.zeros(int(self.delay * SAMPLE_RATE)), samples))
        return samples

    def square(self):
        samples = np.zeros_like(self.t)
        n = 1
        while (self.hz * n) < self.nyquist:
            samples += (1 / n) * np.sin(2 * np.pi * n * self.phase)
            n += 2
        gain = 10 ** (-15 / 20)
        samples = samples * (4 / np.pi) * self.amp * gain
        samples = fade(samples, ease_in="easeOutExpo", ease_out="easeOutExpo")
        samples = np.concatenate((np.zeros(int(self.delay * SAMPLE_RATE)), samples))
        return samples

    def sawtooth(self):
        samples = np.zeros_like(self.t)
        n = 1
        while (self.hz * n) < self.nyquist:
            samples += (1 / n) * np.sin(2 * np.pi * n * self.phase)
            n += 1 
        gain = 10 ** (-12 / 20)
        samples = samples * (2 / np.pi) * self.amp * gain
        samples = fade(samples, ease_in="easeOutExpo", ease_out="easeOutExpo")
        samples = np.concatenate((np.zeros(int(self.delay * SAMPLE_RATE)), samples))
        return samples

    def aliased_square(self):
        samples = np.sign(np.sin(2 * np.pi * self.hz * self.t)).astype(np.float32)
        samples = np.concatenate((np.zeros(int(self.delay * SAMPLE_RATE)), samples))
        return samples