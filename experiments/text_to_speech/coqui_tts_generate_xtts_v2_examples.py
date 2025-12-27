import time

from TTS.api import TTS
import torch

print('generating audio samples with xtts_v2')

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f'using device: {device}')

# list available models
# print(TTS().list_models())

model = "tts_models/multilingual/multi-dataset/xtts_v2"
print(f'using model: {model}')

tts = TTS(model).to(device)
speakers = [
    "Marcos Rudaski",
    "Tanja Adelina",
]

samples = [
    {"language": "en", "text": "Hello, how are you doing today?"},
    {"language": "es", "text": "Hola, ¿cómo estás hoy?"},
    {"language": "fr", "text": "Bonjour, comment allez-vous aujourd'hui ?"},
    {"language": "de", "text": "Hallo, wie geht es dir heute?"},
    {"language": "it", "text": "Ciao, come stai oggi?"},
    {"language": "pt", "text": "Olá, como você está hoje?"},
    {"language": "pl", "text": "Cześć, jak się dzisiaj masz?"},
    {"language": "tr", "text": "Merhaba, bugün nasilsin?"},
    {"language": "ru", "text": "Привет, как твои дела сегодня?"},
    {"language": "nl", "text": "Hallo, hoe gaat het vandaag met je?"},
    {"language": "cs", "text": "Ahoj, jak se dnes máš?"},
    {"language": "ar", "text": "مرحباً، كيف حالك اليوم؟"},
    {"language": "zh-cn", "text": "你好，你今天怎么样？"},
    {"language": "hu", "text": "Szia, hogy vagy ma?"},
    {"language": "ko", "text": "안녕하세요, 오늘 하루 어떠세요?"},
    {"language": "ja", "text": "こんにちは、今日の調子はいかがですか？"},
    {"language": "hi", "text": "नमस्ते, आज आप कैसे हैं?"},
]

# generate raw audio samples (mp3)
# wav = tts.tts(text="Hello world!", speaker_id="Marcos Rudaski", language="en")

for speaker in speakers:
    speaker_id_file_name = speaker.lower().replace(" ", "_")
    for sample in samples:
        t1 = time.time()
        tts.tts_to_file(
            text=sample["text"],
            speaker_id=speaker,
            language=sample["language"],
            file_path=f"generated_audio/{model.split('/')[-1]}/output_{sample['language']}_{speaker_id_file_name}.wav",
        )
        t2 = time.time()
        print(f"generated audio for {speaker} {sample['language']} in {t2 - t1} seconds")
