all: venv

install:
	uv venv --python=3.12
	source .venv/bin/activate
    uv pip install -r requirements.txt

compile-requirements:
	uv pip compile requirements.in -o requirements.txt