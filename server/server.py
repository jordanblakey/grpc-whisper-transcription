import asyncio
import logging
import wave
import numpy as np
from signal import SIGINT, SIGTERM
from faster_whisper import WhisperModel

import grpc
from protos import transcription_pb2
from protos import transcription_pb2_grpc


class WhisperTranscriber(transcription_pb2_grpc.WhisperTranscriberServicer):
    def __init__(self):
        # Try to use GPU if available, otherwise fallback to CPU
        try:
            logging.info("Attempting to initialize Whisper model on CUDA (float16)...")
            self.model = WhisperModel("base.en", device="cuda", compute_type="float16")
            logging.info("Whisper model initialized on CUDA.")
        except Exception as e:
            logging.warning(f"CUDA initialization failed: {e}. Falling back to CPU (int8).")
            self.model = WhisperModel("base.en", device="cpu", compute_type="int8")
            logging.info("Whisper model initialized on CPU.")


    async def StreamTranscription(self, request_iterator, context):
        logging.info("Started new transcription stream")
        
        # Audio state
        utterance_buffer = []  # Audio for current growing utterance
        samples_in_utterance = 0
        samples_since_last_transcribe = 0
        
        # Stream timing
        samples_per_second = 16000
        transcribe_interval_samples = 4000  # Strict 0.25s cooldown
        max_utterance_samples = 30 * samples_per_second
        
        # Transcription state
        absolute_start_time = 0.0
        
        recording_buffer = []
        target_sample_rate = 16000
        
        # Volume threshold for gating (RMS)
        AMPLITUDE_THRESHOLD = 0.005

        try:
            async for chunk in request_iterator:
                # 1. Process received audio
                received_data = np.frombuffer(chunk.data, dtype=np.float32)
                received_rate = chunk.sample_rate if chunk.sample_rate > 0 else target_sample_rate
                
                if received_rate != target_sample_rate:
                    duration = len(received_data) / received_rate
                    target_len = int(duration * target_sample_rate)
                    x = np.arange(len(received_data))
                    x_new = np.linspace(0, len(received_data) - 1, target_len)
                    audio_chunk = np.interp(x_new, x, received_data).astype(np.float32)
                else:
                    audio_chunk = received_data

                utterance_buffer.append(audio_chunk)
                recording_buffer.append(audio_chunk)
                samples_in_utterance += len(audio_chunk)
                samples_since_last_transcribe += len(audio_chunk)
                
                # Check for updates strictly every 1.0s
                if samples_since_last_transcribe >= transcribe_interval_samples:
                    samples_since_last_transcribe = 0 # Reset cooldown
                    
                    v_audio = np.concatenate(utterance_buffer)
                    rms = np.sqrt(np.mean(np.square(v_audio)))
                    
                    # Amplitude Gate
                    if rms < AMPLITUDE_THRESHOLD and samples_in_utterance < max_utterance_samples:
                        # If it's very quiet for 2s, reset the context
                        if samples_in_utterance >= samples_per_second * 2:
                            absolute_start_time += (samples_in_utterance / samples_per_second)
                            utterance_buffer = []
                            samples_in_utterance = 0
                        continue

                    try:
                        # Transcribe the entire growing window
                        segments, info = self.model.transcribe(
                            v_audio, 
                            beam_size=1,
                            vad_filter=True,
                            no_speech_threshold=0.9,
                            log_prob_threshold=-0.5,
                            compression_ratio_threshold=2.4,
                            condition_on_previous_text=False,
                            initial_prompt="I am transcribing live speech."
                        )
                        
                        segments_list = list(segments)
                        speech_text = " ".join([s.text.strip() for s in segments_list if s.no_speech_prob < 0.6]).strip()
                        
                        # Detect silence at the end of the window
                        latest_speech_end = 0.0
                        for s in segments_list:
                            if s.no_speech_prob < 0.6:
                                latest_speech_end = max(latest_speech_end, s.end)
                        
                        current_duration = samples_in_utterance / samples_per_second
                        silence_duration = current_duration - latest_speech_end
                        
                        # Check if VAD removed all audio (common for very short utterances)
                        vad_removed_all = (len(segments_list) == 0 or latest_speech_end == 0.0)
                        
                        # Finalization triggers:
                        # 1. Silence threshold (0.6s) - aggressive for sentence-by-sentence reading
                        # 2. Max utterance length reached (30s)
                        # 3. Short utterance special case: silence >= 0.5s and longer than the speech
                        # 4. If VAD removed all audio and we've been waiting for 1.5+ seconds (stuck partial)
                        should_finalize = (silence_duration >= 0.6) or \
                                         (samples_in_utterance >= max_utterance_samples) or \
                                         (speech_text and silence_duration >= 0.5 and silence_duration > latest_speech_end) or \
                                         (vad_removed_all and current_duration >= 1.5)
                        
                        if should_finalize:
                            if speech_text:
                                result = transcription_pb2.TranscriptionResult(
                                    text=speech_text,
                                    is_final=True,
                                    start_time=absolute_start_time
                                )
                                logging.info(f"FINAL: [{absolute_start_time:06.2f}s] {speech_text}")
                                yield result
                            
                            # Always reset context on finalization/long silence
                            absolute_start_time += current_duration
                            utterance_buffer = []
                            samples_in_utterance = 0
                        else:
                            # Yield live partial update (only if we have text)
                            if speech_text:
                                yield transcription_pb2.TranscriptionResult(
                                    text=speech_text,
                                    is_final=False,
                                    start_time=absolute_start_time
                                )
                                
                    except Exception as e:
                        logging.error(f"Transcription error: {e}")
        finally:
            # ... Wave file saving logic ...
            if recording_buffer:
                try:
                    import os
                    from datetime import datetime
                    full_recording = np.concatenate(recording_buffer)
                    audio_int16 = (np.clip(full_recording, -1.0, 1.0) * 32767).astype(np.int16)
                    
                    recordings_dir = "/app/recordings"
                    os.makedirs(recordings_dir, exist_ok=True)
                    
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_path = os.path.join(recordings_dir, f"recording_{timestamp}.wav")
                    
                    logging.info(f"Saving {len(full_recording)/target_sample_rate:.2f}s of audio to {output_path}")
                    
                    with wave.open(output_path, "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2) # 16-bit
                        wf.setframerate(target_sample_rate)
                        wf.writeframes(audio_int16.tobytes())
                    logging.info(f"Recording saved successfully to {output_path}")
                except Exception as e:
                    logging.error(f"Failed to save recording: {e}")


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

