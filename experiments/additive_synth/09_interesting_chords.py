from audio_modules import Wave, Audio, utils, narrate
from audio_modules.theory_ji import chord, interval, play_chord

import time

with Audio() as a:

    narrate("Let's mess around with some chords in Just Intonation.")
    time.sleep(1)

    narrate("Here's a super turbo major chord.")
    c2 = chord(440, ['uni', 'ma3', 'p5', 'oct', 'ma10', 'p12', 'oct2'])
    play_chord(c2, wave_type='sine', roll_on=0.1, duration=2.5)
    time.sleep(1)

    narrate("Here's an interesting lydian chord progression with a minor triad stacked on top of a major triad.")
    root_hz = 440
    notes = ['uni', 'ma3', 'p5', 'ma7', 'ma9', 'tri2']
    positions = [0, -5, -4, -3, 0]
    for pos in positions:
        c = chord(interval(root_hz, pos), notes)
        play_chord(c, wave_type='sine', roll_on=0.1, duration=2.5)
    
    narrate("Here's the same chord, but moving down one semitone at a time.")
    root_hz = 440
    notes = ['uni', 'ma3', 'p5', 'ma7', 'ma9', 'tri2']
    positions = [0, -1, -2, -3, -4]
    
    for pos in positions:
        c = chord(interval(root_hz, pos), notes)
        print(f'frequencies: {c}')
        duration = 1 if pos != -4 else 2
        play_chord(c, wave_type='sine', roll_on=0.01, duration=duration)    

    narrate(f'Side note: our Just Intonation library has been updated to use SymPy.')
    narrate(f'SymPy lets us represent intervals as rational numbers as long as possible.')
    time.sleep(1)
