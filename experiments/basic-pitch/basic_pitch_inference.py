# basic-pitch . audio_sample.mp3


import sys
from basic_pitch.inference import predict, predict_and_save
from basic_pitch import ICASSP_2022_MODEL_PATH

args = sys.argv

if len(args) != 2:
    print("Usage: python basic_pitch_inference.py <audio_file>")
    sys.exit(1)

# model_output, midi_data, note_events = predict(args[1])
# print(model_output)
# print(midi_data)
# print(note_events)


predict_and_save(
    audio_path_list=[args[1]],
    output_directory='.',
    save_midi=True, 
    sonify_midi=True, 
    save_model_outputs=True, 
    save_notes=True, 
    sonification_samplerate=44100, 
    model_or_model_path=ICASSP_2022_MODEL_PATH)
