
    # buffer.append(Wave(hz=440).sine())
    # play_buffer(buffer)
    # buffer.append(Wave(hz=int(440 * 2 ** (4/12))).sine())
    # play_buffer(buffer)
    # exit()

    # for i in range(1, 3):
    #     buffer.append(Wave(hz=440).sine())
    #     buffer.append(np.zeros(int(1000)))
    #     buffer.append(Wave(hz=int(440 * 2 ** (i/12))).sine())
    #     play_buffer(buffer)
    # exit()
    # time.sleep(1)




    # interval_ratio = 2**(5/12)  # Perfect fourth ratio
    # int(len(w1) / interval_ratio)
    # buffer.append(scipy.signal.resample(w1, int(len(w1) / interval_ratio)))

    # interval_ratio = 2**(7/12)  # Perfect fifth ratio
    # int(len(w1) / interval_ratio)
    # buffer.append(scipy.signal.resample(w1, int(len(w1) / interval_ratio)))

    # play_buffer(buffer)
    exit()


    # this will make each note shorter
    for i in range(12):
        interval_ratio = 2**(i/12)  # Major third ratio
        buffer.append(scipy.signal.resample(w1, int(len(w1) / interval_ratio)))


    def studio_pitch_shift(samples, fs, n_steps=4):
        # 1. Shift
        ratio = 2**(n_steps/12)
        shifted = scipy.signal.resample_poly(samples, 1000, int(1000 * ratio))
        
        # 2. Match Duration (Tiling)
        repeats = int(np.ceil(len(samples) / len(shifted)))
        extended = np.tile(shifted, repeats)[:len(samples)]
        
        # 3. Smooth the edges (The "Anti-Chirp")
        fade_samples = int(fs * 0.01) # 5ms
        # Use a Hanning half-window for an even smoother curve than linear
        envelope = np.ones(len(extended))
        envelope[:fade_samples] = np.hanning(fade_samples * 2)[:fade_samples]
        envelope[-fade_samples:] = np.hanning(fade_samples * 2)[fade_samples:]
        
        return extended * envelope

    # buffer.append(w1)
    # buffer.append(studio_pitch_shift(w1, 44100, 1))
    # buffer.append(studio_pitch_shift(w1, 44100, 2))
    # buffer.append(studio_pitch_shift(w1, 44100, 3))
    # buffer.append(studio_pitch_shift(w1, 44100, 4))
    # buffer.append(studio_pitch_shift(w1, 44100, 5))
    # buffer.append(studio_pitch_shift(w1, 44100, 6))
    # buffer.append(studio_pitch_shift(w1, 44100, 7))
    # buffer.append(studio_pitch_shift(w1, 44100, 8))
    # buffer.append(studio_pitch_shift(w1, 44100, 9))
    # buffer.append(studio_pitch_shift(w1, 44100, 10))
    # buffer.append(studio_pitch_shift(w1, 44100, 11))




    # Shift to Major Third (Equal Temperament)
    # buffer.append(clean_pitch_shift(w1, 4))
    # shifted_samples = shift_sine_fixed_duration(w1, 44100, 4)
    # buffer.append(shifted_samples)

    # buffer.append(clean_pitch_shift(w1, 9))

    # time.sleep(1)
    # for i in range(12):
    #     interval_ratio = 2**(i/12)  # Major third ratio
    #     buffer.append(np.zeros(4400)) # tiny gap between notes
    #     buffer.append(pitch_shift(w1, sr=440, n_steps=i)) # introduces aliasing


    # w1 = Wave(hz=261, amp=1.0, duration=1).sine()
    # w2 = Wave(hz=329, amp=1.0, duration=1).sine()
    # w3 = Wave(hz=261 * 2, amp=1.0, duration=1).sine()

    # buffer.append(w1 + w2 + w3)

    # play audio immediately


    # play_buffer(buffer)

    # save audio to .wav file
    # save_buffer_as_wave(buffer, "recordings/track2.wav")
