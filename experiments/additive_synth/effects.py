from typing import Literal, Optional
import numpy as np

easing_types = Literal["linear"]

def amplitude_envelope(samples: np.ndarray, fade_in_ms: Optional[int] = 15, fade_out_ms: Optional[int] = 15, easing: easing_types = "linear"):
    """Applies an envelope to the samples."""
    envelope = np.ones(len(samples))
    
    if fade_in_ms:
        fade_in_samples = int(48000 * (fade_in_ms / 1000))
        if len(samples) >= fade_in_samples:
            if easing == "linear":
                envelope[:fade_in_samples] = np.linspace(0, 1, fade_in_samples)

    if fade_out_ms:
        fade_out_samples = int(48000 * (fade_out_ms / 1000))
        if len(samples) >= fade_out_samples:
            if easing == "linear":
                envelope[-fade_out_samples:] = np.linspace(1, 0, fade_out_samples)

    return samples * envelope
