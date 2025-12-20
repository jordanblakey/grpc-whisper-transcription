FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

COPY server/requirements.txt requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Copy protos and generate gRPC code first (changes less frequently than server code)
COPY protos/ protos/
RUN python -m grpc_tools.protoc -I . --python_out=. --pyi_out=. --grpc_python_out=. protos/*.proto

# Copy server code last
COPY server/ server/

EXPOSE 50051

CMD ["python", "server/server.py"]
