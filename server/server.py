import asyncio
import logging
from signal import SIGINT, SIGTERM

import grpc
from protos import transcription_pb2_grpc
from transcriber import WhisperTranscriber

async def serve():
    port = "50051"
    server = grpc.aio.server()
    transcription_pb2_grpc.add_WhisperTranscriberServicer_to_server(WhisperTranscriber(), server)
    server.add_insecure_port("[::]:" + port)
    await server.start()
    print(f"Server started on {port}", flush=True)

    async def server_graceful_shutdown():
        print("Starting graceful shutdown...")
        await server.stop(5)

    loop = asyncio.get_running_loop()
    for signal in (SIGINT, SIGTERM):
        loop.add_signal_handler(
            signal,
            lambda: asyncio.create_task(server_graceful_shutdown()),
        )

    await server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    asyncio.run(serve())

