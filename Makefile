venv:
	if [ ! -d "venv" ]; then python3 -m venv venv; fi
	. venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

.PHONY: protos generated

protos:
	. venv/bin/activate && mkdir -p generated && \
		python -m grpc_tools.protoc \
		-I protos \
		--python_out=protos \
		--pyi_out=protos \
		--grpc_python_out=protos \
		protos/*.proto