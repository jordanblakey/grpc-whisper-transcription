import logging
import wave
import numpy as np
from faster_whisper import WhisperModel

import grpc
from protos import transcription_pb2
from protos import transcription_pb2_grpc

class WhisperTranscriber(transcription_pb2_grpc.WhisperTranscriberServicer):
    def __init__(self):
        # Try to use GPU if available, otherwise fallback to CPU
        try:
            logging.info("Attempting to initialize Whisper model on CUDA (float16)...")
            self.model = WhisperModel("tiny.en", device="cuda", compute_type="float16")
            logging.info("Whisper model initialized on CUDA.")
        except Exception as e:
            logging.error(f"CUDA initialization failed: {e}. Exiting.")
            exit(1)

    async def StreamTranscription(self, request_iterator, context):
        logging.info("Started new transcription stream")
        
        # Audio state
        utterance_buffer = []  # Audio for current growing utterance
        samples_in_utterance = 0
        samples_since_last_transcribe = 0
        
        # Stream timing
        samples_per_second = 16000
        transcribe_interval_samples = 16000  # Strict 1s cooldown
        # Max duration per utterance before forcing a split (samples)
        # 30 seconds is the optimal Whisper window size
        max_utterance_samples = 30 * samples_per_second

        # Transcription state
        absolute_start_time = 0.0
        last_speech_text = ""
        last_text_change_time = 0.0
        transcription_history = []  # List of finalized strings
        
        # WPM tracking (session-wide)
        total_words_finalized = 0
        total_speech_seconds = 0.0
        
        recording_buffer = []
        target_sample_rate = 16000
        
        # Volume threshold for gating (RMS).
        AMPLITUDE_THRESHOLD = 0.010 # Reset to a more moderate value
        consecutive_quiet_intervals = 0

        try:
            async for chunk in request_iterator:
                # 1. Process received audio - explicitly Little Endian Float32
                received_data = np.frombuffer(chunk.data, dtype='<f4')
                received_rate = chunk.sample_rate if chunk.sample_rate > 0 else target_sample_rate
                
                if received_rate != target_sample_rate:
                    # Log once or periodically to avoid spamming if resampling is still happening
                    if samples_in_utterance == 0:
                        logging.warning(f"Resampling required: Received {received_rate}Hz, target {target_sample_rate}Hz. This may cause crackling.")
                    
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
                    
                    # Amplitude Gate (Broad filter)
                    if rms < AMPLITUDE_THRESHOLD:
                        consecutive_quiet_intervals += 1
                        if consecutive_quiet_intervals < 2 and samples_in_utterance < max_utterance_samples:
                            continue
                    else:
                        consecutive_quiet_intervals = 0

                    try:
                        # Contextual Prompting: Pass recent history to maintain quality
                        # Limit prompt to last ~300 chars to avoid overwhelming the model
                        history_prompt = " ".join(transcription_history)[-300:].strip()
                        initial_prompt = f"I am transcribing live speech. Context: {history_prompt}" if history_prompt else "I am transcribing live speech."

                        # Transcribe with tuned VAD to handle background music better
                        segments, info = self.model.transcribe(
                            v_audio, 
                            beam_size=1,
                            vad_filter=True,
                            vad_parameters=dict(min_silence_duration_ms=500, speech_pad_ms=200),
                            no_speech_threshold=0.6,
                            log_prob_threshold=-0.5,
                            compression_ratio_threshold=2.4,
                            condition_on_previous_text=False,
                            initial_prompt=initial_prompt
                        )
                        
                        segments_list = list(segments)
                        # Stricter check for speech presence (0.4 prob)
                        speech_text = " ".join([s.text.strip() for s in segments_list if s.no_speech_prob < 0.4]).strip()
                        
                        # Detect silence at the end of the window
                        latest_speech_end = 0.0
                        for s in segments_list:
                             if s.no_speech_prob < 0.4:
                                 latest_speech_end = max(latest_speech_end, s.end)
                        
                        current_duration = samples_in_utterance / samples_per_second
                        silence_duration = current_duration - latest_speech_end
                        
                        # Stall detection: Did the transcription actually grow?
                        if speech_text != last_speech_text:
                            last_speech_text = speech_text
                            last_text_change_time = current_duration
                        
                        stall_duration = current_duration - last_text_change_time
                        
                        # --- Dynamic Threshold Calculation (WPM-Adaptive) ---
                        words = speech_text.split()
                        num_words = len(words)
                        has_strong_punctuation = any(speech_text.endswith(p) for p in [".", "?", "!"])
                        
                        # Calculate Session WPM (with a sane default for the start)
                        avg_wpm = (total_words_finalized / (total_speech_seconds / 60)) if total_speech_seconds > 5 else 150
                        
                        # Base required silence maps to WPM
                        if avg_wpm > 180: # Fast (YouTube)
                            base_required_silence = 0.6
                            stall_threshold = 1.0 if has_strong_punctuation else 1.4
                        elif avg_wpm < 130: # Slow (Narration)
                            base_required_silence = 1.2
                            stall_threshold = 1.5 if has_strong_punctuation else 2.0
                        else: # Normal
                            base_required_silence = 0.9
                            stall_threshold = 1.2 if has_strong_punctuation else 1.8

                        # Aggressive punctuation override
                        required_silence = base_required_silence
                        if has_strong_punctuation:
                            required_silence = min(required_silence, 0.4 if avg_wpm < 130 else 0.3)
                        
                        # Length-based urgency
                        if num_words > 15 or current_duration > 15.0:
                            required_silence = min(required_silence, 0.6)

                        logging.info(f"DEBUG: WPM={avg_wpm:.0f}, silence={silence_duration:.2f}s, stall={stall_duration:.1f}s, words={num_words}, req_silence={required_silence:.1f}s")

                        # Finalization triggers
                        # 1. Proactive Sentence Splitting (YouTube Style): Break at period if buffer > 12s
                        # 2. Dynamic silence threshold reached
                        # 3. Text stall (1.2s-2.0s based on WPM)
                        # 4. Consecutive quiet RMS checks (2.0s)
                        # 5. Hard safety cap (20s)
                        
                        should_finalize = (current_duration > 12.0 and has_strong_punctuation) or \
                                         (silence_duration >= required_silence) or \
                                         (stall_duration >= stall_threshold and silence_duration >= 0.4) or \
                                         (consecutive_quiet_intervals >= 2) or \
                                         (samples_in_utterance >= max_utterance_samples)
                        
                        # --- Fallback Strategy for "Silent" Long Buffers ---
                        if not speech_text and samples_in_utterance > 15 * samples_per_second:
                            logging.info("FALLBACK: Buffer long but empty. Retrying without VAD.")
                            f_segments, _ = self.model.transcribe(
                                v_audio,
                                beam_size=2,
                                vad_filter=False, # Disable VAD to recover missed speech
                                initial_prompt=initial_prompt
                            )
                            f_segments_list = list(f_segments)
                            speech_text = " ".join([s.text.strip() for s in f_segments_list if s.no_speech_prob < 0.6]).strip()
                        
                        if should_finalize:
                            if speech_text:
                                result = transcription_pb2.TranscriptionResult(
                                    text=speech_text,
                                    is_final=True,
                                    start_time=absolute_start_time
                                )
                                logging.info(f"FINAL: [{absolute_start_time:06.2f}s] (WPM:{avg_wpm:.0f}) {speech_text}")
                                yield result
                                
                                # Update WPM stats and history
                                total_words_finalized += num_words
                                total_speech_seconds += current_duration
                                transcription_history.append(speech_text)
                                transcription_history = transcription_history[-5:]

                                # SAFE RESET
                                absolute_start_time += current_duration
                                utterance_buffer = []
                                samples_in_utterance = 0
                                last_speech_text = ""
                                last_text_change_time = 0.0
                            elif samples_in_utterance >= max_utterance_samples + (10 * samples_per_second):
                                # EMERGENCY RESET: Extreme runaway buffer with NO text detected
                                logging.info(f"EMERGENCY: Safety Reset triggered ({current_duration:.1f}s). No text detected in long buffer.")
                                absolute_start_time += current_duration
                                utterance_buffer = []
                                samples_in_utterance = 0
                                last_speech_text = ""
                                last_text_change_time = 0.0
                            elif consecutive_quiet_intervals >= 10:
                                # SILENCE RESET: 10s of absolute electrical silence
                                logging.info(f"DEBUG: Reset after 10s of absolute silence.")
                                absolute_start_time += current_duration
                                utterance_buffer = []
                                samples_in_utterance = 0
                                last_speech_text = ""
                                last_text_change_time = 0.0
                            else:
                                logging.info(f"DEBUG: Finalization trigger met but speech_text empty. Carrying over buffer ({current_duration:.1f}s)")
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