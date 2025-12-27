import time
import os
import soundfile as sf
from kokoro import KPipeline

print('Generating audio samples with Kokoro-82M')

# 1. Initialize the Kokoro Pipeline (Language 'a' for American English, 'b' for British)
pipeline = KPipeline(lang_code='a') 

# 2. Kokoro Voice List (Mix of American & British, Male & Female)
# You can add more from: af_bella, af_sarah, am_adam, am_michael, bf_emma, bm_lewis, etc.
speakers = ['af_bella', 'af_sarah', 'am_adam', 'am_michael', 'bf_emma', 'bm_lewis']

samples = [
    {"title": "The Heteronym Trap", "text": "I need to present the present to the board, but they are not present at the moment."},
    {"title": "The Semantic Shift", "text": "I did not steal this car. I did not steal this car. I did not steal this car."},
    {"title": "The Punctuation Test", "text": "Wait—did you... actually... buy that? No. Way!"},
    {"title": "The Tongue Twister", "text": "The sixth sick sheik's sixth sheep's sick."},
    {"title": "Technical Complexity", "text": "The server's IP is 192.168.1.1, and the temperature rose from -10°C to 105.5°F."},
    {"title": "The Lead Dilemma", "text": "If you lead the way, we can find where the lead pipes are buried."},
    {"title": "Syntactic Complexity", "text": "The complex houses married and single soldiers and their families."},
    {"title": "Acronyms", "text": "NASA and the FBI are looking into the UFO sighting in the USA."},
    {"title": "Intonation", "text": "You're coming to the meeting? You're coming to the meeting."},
    {"title": "Foreign Words", "text": "He ordered a pain au chocolat with his espresso at the café."}
]

# Create output directory
output_dir = "generated_audio/kokoro_82m"
os.makedirs(output_dir, exist_ok=True)

for speaker in speakers:
    print(f"Processing speaker: {speaker}")
    speaker_id_clean = speaker.lower()
    
    for sample in samples:
        t1 = time.time()
        sample_title = sample["title"].lower().replace(" ", "_")
        file_path = f"{output_dir}/{sample_title}_{speaker_id_clean}.wav"

        # 3. Kokoro Generation
        # Kokoro returns a generator of (graphemes, phonemes, audio_tensor)
        generator = pipeline(
            sample["text"], 
            voice=speaker, 
            speed=1, 
            split_pattern=r'\n+'
        )

        # Collect and save audio
        for i, (gs, ps, audio) in enumerate(generator):
            # We save the first (usually only) segment
            sf.write(file_path, audio, 24000) # Kokoro native rate is 24kHz
            
        t2 = time.time()
        print(f"Generated {file_path} in {t2 - t1:.2f} seconds")