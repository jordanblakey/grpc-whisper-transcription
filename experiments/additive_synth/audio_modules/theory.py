from audio_modules import Audio, Wave, utils, effects

# Equal Temperament version

def interval(hz, semitones):
    """Given a base frequency and a number of semitones, return the frequency of the note."""
    return hz * 2 ** (semitones / 12)


# chords

def play_chord(chord_hz: list[int], amp: float = 1.0, duration: float = 1.0, wave_type: str = 'sine', roll_on: float = 0.0):
    """Given a list of frequencies, play a chord."""
    with Audio() as a:
        waves = []
        for i, hz in enumerate(chord_hz):
            waves.append(Wave(hz=hz, amp=amp, duration=duration))
            waves[i].delay = i * roll_on
            waves[i].duration = duration - i * roll_on
        for i in range(len(waves)):
            if wave_type == 'sine':
                waves[i] = waves[i].sine()
            elif wave_type == 'square':
                waves[i] = waves[i].square()
            elif wave_type == 'sawtooth':
                waves[i] = waves[i].sawtooth()
            elif wave_type == 'triangle':
                waves[i] = waves[i].triangle()
        wave = utils.sum_waveforms(waves)
        wave = effects.fade(wave, fade_in_ms=250, fade_out_ms=500, ease_in="sine", ease_out="easeInQuad")

        a.buffer.append(wave)
        a.play_buffer()

def major_chord(hz):
    """Given a base frequency, return the frequencies of the notes in a major chord."""
    return [hz, interval(hz, 4), interval(hz, 7)]

def minor_chord(hz):
    """Given a base frequency, return the frequencies of the notes in a minor chord."""
    return [hz, interval(hz, 3), interval(hz, 7)]

def diminished_chord(hz):
    """Given a base frequency, return the frequencies of the notes in a diminished chord."""
    return [hz, interval(hz, 3), interval(hz, 6)]

def augmented_chord(hz):
    """Given a base frequency, return the frequencies of the notes in an augmented chord."""
    return [hz, interval(hz, 4), interval(hz, 8)]

def power_chord(hz):
    """Given a base frequency, return the frequencies of the notes in a power chord."""
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


# scales

def play_scale(scale: list[int], amp: float = 1.0, duration: float = 1.0, wave_type: str = 'sine', ascending: bool = True):
    """Given a list of frequencies, play a scale."""
    with Audio() as a:
        waves = []
        if ascending:
            for hz in scale:
                waves.append(Wave(hz=hz, amp=amp, duration=duration))
            waves.append(Wave(hz=(scale[0] * 2 ** (12 / 12)), amp=amp, duration=duration))
        else:
            waves.append(Wave(hz=(scale[0] * 2 ** (12 / 12)), amp=amp, duration=duration))
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

# common 

def chromatic_scale(hz):
    """Given a base frequency, return the frequencies of the notes in a chromatic scale."""
    return [hz, interval(hz, 1), interval(hz, 2), interval(hz, 3), interval(hz, 4), interval(hz, 5), interval(hz, 6), interval(hz, 7), interval(hz, 8), interval(hz, 9), interval(hz, 10), interval(hz, 11)]

def pentatonic_scale(hz):
    """Given a base frequency, return the frequencies of the notes in a pentatonic scale."""
    return [hz, interval(hz, 2), interval(hz, 4), interval(hz, 5), interval(hz, 7), interval(hz, 9)]

# modes

def ionian_scale(hz):
    """Given a base frequency, return the frequencies of the notes in an ionian (major) scale."""
    return [hz, interval(hz, 2), interval(hz, 4), interval(hz, 5), interval(hz, 7), interval(hz, 9), interval(hz, 11)]

def dorian_scale(hz):
    """Given a base frequency, return the frequencies of the notes in a dorian scale."""
    return [hz, interval(hz, 2), interval(hz, 3), interval(hz, 5), interval(hz, 7), interval(hz, 9), interval(hz, 10)]

def phrygian_scale(hz):
    """Given a base frequency, return the frequencies of the notes in a phrygian scale."""
    return [hz, interval(hz, 1), interval(hz, 3), interval(hz, 5), interval(hz, 7), interval(hz, 8), interval(hz, 10)]

def lydian_scale(hz):
    """Given a base frequency, return the frequencies of the notes in a lydian scale."""
    return [hz, interval(hz, 2), interval(hz, 4), interval(hz, 6), interval(hz, 7), interval(hz, 9), interval(hz, 11)]

def mixolydian_scale(hz):
    """Given a base frequency, return the frequencies of the notes in a mixolydian scale."""
    return [hz, interval(hz, 2), interval(hz, 4), interval(hz, 5), interval(hz, 7), interval(hz, 9), interval(hz, 10)]

def aeolian_scale(hz):
    """Given a base frequency, return the frequencies of the notes in an aeolian (natural minor) scale."""
    return [hz, interval(hz, 2), interval(hz, 3), interval(hz, 5), interval(hz, 7), interval(hz, 8), interval(hz, 10)]

def locrian_scale(hz):
    """Given a base frequency, return the frequencies of the notes in a locrian scale."""
    return [hz, interval(hz, 1), interval(hz, 3), interval(hz, 5), interval(hz, 6), interval(hz, 8), interval(hz, 10)]
