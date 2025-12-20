FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY client/requirements.txt requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Copy protos and generate gRPC code first (changes less frequently than client code)
COPY protos/ protos/
RUN python -m grpc_tools.protoc -I . --python_out=. --pyi_out=. --grpc_python_out=. protos/*.proto

# Copy client code last
COPY client/ client/

EXPOSE 8080

CMD ["python", "client/client.py"]
