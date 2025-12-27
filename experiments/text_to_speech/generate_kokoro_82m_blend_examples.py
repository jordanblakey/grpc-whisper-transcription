import time
import os
import soundfile as sf
from kokoro import KPipeline

pipeline = KPipeline(lang_code='a') 

# --- UPDATED REMIX LIST ---
# Using comma-separated voices (Library typically averages these 50/50 or equally)
remix_speakers = {
    "Mid_Atlantic": "af_sarah,bf_emma",
    "Deep_Radio": "am_michael,bm_george",
    "Whispering_Scholar": "af_nicole,bf_isabella",
    "Transatlantic": "am_adam,bm_lewis",
    "Global_AI": "af_bella,af_sky,bf_emma"
}

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

output_dir = "generated_audio/kokoro_82m_weighted_blends"
os.makedirs(output_dir, exist_ok=True)

for custom_name, voice_mix in remix_speakers.items():
    print(f"🎤 Generating: {custom_name}")
    
    for sample in samples:
        t1 = time.time()
        sample_title = sample["title"].lower().replace(" ", "_")
        file_path = f"{output_dir}/{sample_title}_{custom_name}.wav"

        # Pass the comma-separated string
        generator = pipeline(
            sample["text"], 
            voice=voice_mix, 
            speed=1.0
        )

        for gs, ps, audio in generator:
            sf.write(file_path, audio, 24000)
            
        print(f"   - Saved {sample_title}.wav")