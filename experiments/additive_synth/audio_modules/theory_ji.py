from audio_modules import Audio, Wave, utils, effects
from sympy import Rational

# Just Intonation Ratios (5-limit tuning)
# These represent the distance from the root (1/1)
JI_RATIOS = {
    0:  Rational(1, 1), # Unison
    1:  Rational(16, 15), # Minor Second
    2:  Rational(9, 8), # Major Second
    3:  Rational(6, 5), # Minor Third
    4:  Rational(5, 4), # Major Third
    5:  Rational(4, 3), # Perfect Fourth
    6:  Rational(45, 32), # Tritone (diatonic)
    7:  Rational(3, 2), # Perfect Fifth
    8:  Rational(8, 5), # Minor Sixth
    9:  Rational(5, 3), # Major Sixth
    10: Rational(9, 5), # Minor Seventh
    11: Rational(15, 8), # Major Seventh
    12: Rational(2, 1) # Octave
}

def interval(hz, semitones):
    """Returns JI frequency. Handles octaves by multiplying/dividing by 2."""
    octave_shift = semitones // 12
    key = semitones % 12
    freq_rational = Rational(hz) * JI_RATIOS[key] * (Rational(2) ** octave_shift)
    return freq_rational

# --- Chords (Now perfectly resonant) ---

def major_chord(hz):
    # Perfect 4:5:6 ratio
    return [hz, interval(hz, 4), interval(hz, 7)]

def minor_chord(hz):
    # Perfect 10:12:15 ratio
    return [hz, interval(hz, 3), interval(hz, 7)]

def diminished_chord(hz):
    # Perfect 9:10:12 ratio
    return [hz, interval(hz, 2), interval(hz, 6)]

def augmented_chord(hz):
    # Perfect 5:6:7 ratio
    return [hz, interval(hz, 4), interval(hz, 8)]

def power_chord(hz):
    # Perfect 2:3 ratio
    return [hz, interval(hz, 7), interval(hz, 12)]

def chord(hz, notes: list[str]):
    intervals = {
        'uni': interval(hz, 0),
        'mi2': interval(hz, 1),
        'ma2': interval(hz, 2),
        'mi3': interval(hz, 3),
        'ma3': interval(hz, 4),
        'p4': interval(hz, 5),
        'tri': interval(hz, 6),
        'p5': interval(hz, 7),
        'mi6': interval(hz, 8),
        'ma6': interval(hz, 9),
        'mi7': interval(hz, 10),
        'ma7': interval(hz, 11),
        'oct': interval(hz, 12),
        'mi9': interval(hz, 13),
        'ma9': interval(hz, 14),
        'mi10': interval(hz, 15),
        'ma10': interval(hz, 16),
        'p11': interval(hz, 17),
        'tri2': interval(hz, 18),
        'p12': interval(hz, 19),
        'mi13': interval(hz, 20),
        'ma13': interval(hz, 21),
        'mi14': interval(hz, 20),
        'ma14': interval(hz, 21),
        'oct2': interval(hz, 24),
    }
    return [intervals[n] for n in notes]


# --- Scales (The 'purer' versions) ---

def chromatic_scale(hz):
    """The JI Chromatic Scale."""
    return [interval(hz, s) for s in [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]]

def pentatonic_scale(hz):
    """The JI Pentatonic Scale."""
    return [interval(hz, s) for s in [0, 2, 4, 5, 7, 9]]

def ionian_scale(hz):
    """The JI Major Scale."""
    return [interval(hz, s) for s in [0, 2, 4, 5, 7, 9, 11]]

def dorian_scale(hz):
    """The JI Dorian Scale (Minor with a natural 6th)."""
    # 0, 2, 3, 5, 7, 9, 10
    return [interval(hz, s) for s in [0, 2, 3, 5, 7, 9, 10]]

def phrygian_scale(hz):
    """The JI Phrygian Scale (Minor with a flat 2nd)."""
    # 0, 1, 3, 5, 7, 8, 10
    return [interval(hz, s) for s in [0, 1, 3, 5, 7, 8, 10]]

def lydian_scale(hz):
    """The JI Lydian Scale (Major with a sharp 4th)."""
    # 0, 2, 4, 6, 7, 9, 11
    return [interval(hz, s) for s in [0, 2, 4, 6, 7, 9, 11]]

def mixolydian_scale(hz):
    """The JI Mixolydian Scale (Major with a flat 7th)."""
    # 0, 2, 4, 5, 7, 9, 10
    return [interval(hz, s) for s in [0, 2, 4, 5, 7, 9, 10]]

def aeolian_scale(hz):
    """The JI Natural Minor Scale."""
    return [interval(hz, s) for s in [0, 2, 3, 5, 7, 8, 10]]

def locrian_scale(hz):
    """The JI Locrian Scale (Diminished feel)."""
    # 0, 1, 3, 5, 6, 8, 10
    return [interval(hz, s) for s in [0, 1, 3, 5, 6, 8, 10]]

# --- Refactored Play Functions ---

def play_chord(chord_hz: list, roll_on: float = 0.0, amp: float = 1.0, duration: float = 1.0, wave_type: str = 'sine'):
    """Plays JI chords with normalization to prevent constructive interference artifacts."""
    with Audio() as a:
        waves = []
        for i, hz in enumerate(chord_hz):
            # Convert SymPy Rational to float here
            waves.append(Wave(hz=float(hz), amp=amp, duration=duration))
            waves[i].delay = i * roll_on
            waves[i].duration = duration - i * roll_on
            
        for i in range(len(waves)):
            if wave_type == 'sine': waves[i] = waves[i].sine()
            elif wave_type == 'square': waves[i] = waves[i].square()
            elif wave_type == 'sawtooth': waves[i] = waves[i].sawtooth()
            elif wave_type == 'triangle': waves[i] = waves[i].triangle()
            
        wave = utils.sum_waveforms(waves)
        wave = effects.normalize(wave)

        wave = effects.fade(wave, fade_in_ms=250, fade_out_ms=500, ease_in="sine", ease_out="easeInQuad")
        a.buffer.append(wave)
        a.play_buffer()

def play_scale(scale: list[int], amp: float = 1.0, duration: float = 1.0, wave_type: str = 'sine', ascending: bool = True):
    """Given a list of frequencies, play a scale."""
    with Audio() as a:
        waves = []
        if ascending:
            for hz in scale:
                waves.append(Wave(hz=hz, amp=amp, duration=duration))
            waves.append(Wave(hz=(scale[0] * 2), amp=amp, duration=duration))
        else:
            waves.append(Wave(hz=(scale[0] * 2), amp=amp, duration=duration))
            for hz in scale[::-1]:
                waves.append(Wave(hz=hz, amp=amp, duration=duration))

        for i in range(len(waves)):
            if wave_type == 'sine':
                waves[i] = waves[i].sine()
            elif wave_type == 'square':
                waves[i] = waves[i].square()
            elif wave_type == 'sawtooth':
                waves[i] = waves[i].sawtooth()
            elif wave_type == 'triangle':
                waves[i] = waves[i].triangle()
        for i in range(len(waves)):
            waves[i] = effects.fade(waves[i], fade_in_ms=5, fade_out_ms=300, ease_in="easeOutExpo", ease_out="easeInQuad")
            a.buffer.append(waves[i])
        a.play_buffer()
