install:
	sudo apt install fluidsynth
	uv venv --python=python3.11
	. .venv/bin/activate
	uv pip install -r requirements.txt

basic-pitch-inference:
	. .venv/bin/activate
	uv pip install -r requirements.txt
	uv python basic_pitch_inference.py $(FILE)

basic-pitch:
	. .venv/bin/activate
	uv pip install -r requirements.txt
	basic-pitch . $(FILE)

play-midi:
	. .venv/bin/activate
	uv pip install -r requirements.txt
	uv python play_midi.py $(FILE)