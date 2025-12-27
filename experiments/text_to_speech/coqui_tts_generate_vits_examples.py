import time
import os

from TTS.api import TTS
import torch

print('generating audio samples with xtts_v2')

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f'using device: {device}')

# list available models
# print(TTS().list_models())

model = "tts_models/en/vctk/vits" 
print(f'using model: {model}')

tts = TTS(model).to(device)
speakers = ['ED\n', 'p225', 'p226', 'p227', 'p228', 'p229', 'p230', 'p231', 'p232', 'p233', 'p234', 'p236', 'p237', 'p238', 'p239', 'p240', 'p241', 'p243', 'p244', 'p245', 'p246', 'p247', 'p248', 'p249', 'p250', 'p251', 'p252', 'p253', 'p254', 'p255', 'p256', 'p257', 'p258', 'p259', 'p260', 'p261', 'p262', 'p263', 'p264', 'p265', 'p266', 'p267', 'p268', 'p269', 'p270', 'p271', 'p272', 'p273', 'p274', 'p275', 'p276', 'p277', 'p278', 'p279', 'p280', 'p281', 'p282', 'p283', 'p284', 'p285', 'p286', 'p287', 'p288', 'p292', 'p293', 'p294', 'p295', 'p297', 'p298', 'p299', 'p300', 'p301', 'p302', 'p303', 'p304', 'p305', 'p306', 'p307', 'p308', 'p310', 'p311', 'p312', 'p313', 'p314', 'p316', 'p317', 'p318', 'p323', 'p326', 'p329', 'p330', 'p333', 'p334', 'p335', 'p336', 'p339', 'p340', 'p341', 'p343', 'p345', 'p347', 'p351', 'p360', 'p361', 'p362', 'p363', 'p364', 'p374', 'p376']
samples = [
    {
        "title": "The Heteronym Trap",
        "text": "I need to present the present to the board, but they are not present at the moment.",
        "language": "en",
        "test": "Can the model distinguish between the verb /prɪˈzent/ and the nouns /ˈprezənt/ based on grammar?"
    },
    {
        "title": "The Semantic Shift (Stress)",
        "text": "I did not *steal* this car. I did not steal *this* car. I did not steal this *car*.",
        "language": "en",
        "test": "Does the model understand emphasis? Each sentence has a different meaning based on which word is stressed."
    },
    {
        "title": "The Punctuation & Breath Test",
        "text": "Wait—did you... actually... buy that? No. Way!",
        "language": "en",
        "test": "Testing the ability to handle pauses (ellipses), sudden stops (dashes), and emotional shifts (exclamations)."
    },
    {
        "title": "The Compound Word & Phonetics",
        "text": "The sixth sick sheik's sixth sheep's sick.",
        "language": "en",
        "test": "A classic tongue-twister. Checks if the model slurs phonemes or creates digital artifacts."
    },
    {
        "title": "Technical & Numerical Complexity",
        "text": "The server's IP is 192.168.1.1, and the temperature rose from -10°C to 105.5°F.",
        "language": "en",
        "test": "Does it say 'dot' or 'point'? How does it handle negative signs and scientific units?"
    },
    {
        "title": "The 'Lead' Dilemma",
        "text": "If you lead the way, we can find where the lead pipes are buried.",
        "language": "en",
        "test": "Another heteronym check (/liːd/ vs /led/) requiring contextual analysis."
    },
    {
        "title": "Syntactic Complexity",
        "text": "The complex houses married and single soldiers and their families.",
        "language": "en",
        "test": "A garden-path sentence where 'houses' is a verb. Tests if the model stumbles on phrasing."
    },
    {
        "title": "Acronyms & Casing",
        "text": "NASA and the FBI are looking into the UFO sighting in the USA.",
        "language": "en",
        "test": "Does it pronounce 'NASA' as a word but 'F-B-I' as individual letters?"
    },
    {
        "title": "Question vs. Statement Intonation",
        "text": "You're coming to the meeting? You're coming to the meeting.",
        "language": "en",
        "test": "Tests the 'uptick' in pitch for questions versus the flat/falling tone of a statement."
    },
    {
        "title": "The Foreign Word Integration",
        "text": "He ordered a pain au chocolat with his espresso at the café.",
        "language": "en",
        "test": "Checks how an English-trained model handles French or Italian loanwords."
    }
]

examples_dir = f"generated_audio/{model.split('/')[-1]}"
if not os.path.exists(examples_dir):
    os.makedirs(examples_dir)
for speaker in speakers:
    speaker_id_file_name = speaker.lower().replace(" ", "_")
    for sample in samples:
        t1 = time.time()
        sample_title = sample["title"].lower().replace(" ", "_")
        tts.tts_to_file(
            text=sample["text"],
            speaker_id=speaker,
            file_path=f"{examples_dir}/{sample_title}_{sample['language']}_{speaker_id_file_name}.wav",
        )
        t2 = time.time()
        print(f".wav file generated in {t2 - t1} seconds")

