import os
from faster_whisper import WhisperModel

# model_size = "large-v3"
model_size = "base.en"

# Run on GPU with FP16
model = WhisperModel(model_size, device="cuda", compute_type="float16")

# or run on GPU with INT8
# model = WhisperModel(model_size, device="cuda", compute_type="int8_float16")

# model = WhisperModel(model_size, device="cpu", compute_type="int8")
# segments, info = model.transcribe(file_path, beam_size=5)

folder_path = os.path.abspath("../small-stt-eval-audio-dataset")
files = os.listdir("../small-stt-eval-audio-dataset")

for file in files:
    if not file.endswith(".wav") and not file.endswith(".mp3"):
        continue
    file_path = os.path.abspath(folder_path + "/" + file)
    segments, info = model.transcribe(file_path, beam_size=5)
    # exit()
    print("Detected language '%s' with probability %f" % (info.language, info.language_probability))
    # print(info)
    for segment in segments:
        print("[%.2fs -> %.2fs] %s" % (segment.start, segment.end, segment.text))





