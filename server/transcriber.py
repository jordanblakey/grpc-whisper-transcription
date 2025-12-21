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
        AMPLITUDE_THRESHOLD = 0.005 # Back to a middle ground to filter out noise floor
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
                        # More history helps with slow narrators
                        history_prompt = " ".join(transcription_history)[-500:].strip()
                        initial_prompt = f"I am transcribing live speech. Context: {history_prompt}" if history_prompt else "I am transcribing live speech."

                        # --- GPU Optimization: Sliding Window ---
                        # Instead of transcribing the FULL buffer (which grows O(N^2)), 
                        # we only transcribe the last 12s for performance.
                        full_audio_v = np.concatenate(utterance_buffer)
                        total_duration = len(full_audio_v) / samples_per_second
                        
                        window_duration = 12.0
                        if total_duration > window_duration:
                            window_samples = int(window_duration * samples_per_second)
                            v_audio = full_audio_v[-window_samples:]
                            window_offset = total_duration - window_duration
                        else:
                            v_audio = full_audio_v
                            window_offset = 0.0

                        # Transcribe with tuned VAD and Word Timestamps
                        segments, _ = self.model.transcribe(
                            v_audio, 
                            beam_size=1,
                            vad_filter=True,
                            vad_parameters=dict(min_silence_duration_ms=500, speech_pad_ms=200),
                            word_timestamps=True,
                            no_speech_threshold=0.6,
                            log_prob_threshold=-0.5,
                            compression_ratio_threshold=2.4,
                            condition_on_previous_text=False,
                            initial_prompt=initial_prompt
                        )
                        
                        segments_list = list(segments)
                        
                        # Calculate rough WPM from the window for heuristics
                        window_text = " ".join([s.text.strip() for s in segments_list if s.no_speech_prob < 0.4]).strip()
                        num_words_window = len(window_text.split())
                        has_strong_punctuation = any(window_text.endswith(p) for p in [".", "?", "!"])
                        
                        avg_wpm = (total_words_finalized / (total_speech_seconds / 60)) if total_speech_seconds > 5 else 150
                        
                        # Dynamic Thresholds
                        if avg_wpm > 180: # Fast (YouTube style)
                            base_required_silence = 0.6
                            stall_threshold = 1.0 if has_strong_punctuation else 1.4
                        elif avg_wpm < 85: # Gothic Narrator (Wizard of Oz style)
                            # Deep patience for dramatic pauses
                            base_required_silence = 4.0
                            stall_threshold = 5.0 if has_strong_punctuation else 7.0
                        elif avg_wpm < 110: # Narrator (Books)
                            base_required_silence = 2.5
                            stall_threshold = 3.0 if has_strong_punctuation else 4.0
                        elif avg_wpm < 140: # Slow
                            base_required_silence = 1.5
                            stall_threshold = 2.0 if has_strong_punctuation else 2.8
                        else: # Normal
                            base_required_silence = 1.0
                            stall_threshold = 1.5 if has_strong_punctuation else 2.2

                        required_silence = base_required_silence
                        if has_strong_punctuation:
                            # If someone just said a period, we can be much snappier
                            required_silence = min(required_silence, 0.4 if avg_wpm < 130 else 0.3)
                        
                        if num_words_window > 15 or total_duration > 15.0:
                            required_silence = min(required_silence, 0.6)

                        # --- Word-Level Incremental Finalization ---
                        last_finalized_end_rel = 0.0
                        
                        current_sentence_words = []
                        all_speech_text_parts = []
                        
                        # Split hierarchies
                        STRONG_STOP = [".", "?", "!", "..."]
                        SOFT_STOP = [",", ";", ":", "-"] # Commas allow splitting but with more patience
                        
                        for s_idx, s in enumerate(segments_list):
                            # Filter out low-confidence segments (hallucinations)
                            if s.no_speech_prob > 0.8 or s.avg_logprob < -1.0: 
                                continue
                            
                            if not s.words:
                                s_text = s.text.strip()
                                if not s_text: continue
                                is_stop = any(s_text.endswith(p) for p in STRONG_STOP)
                                if is_stop:
                                    yield transcription_pb2.TranscriptionResult(
                                        text=s_text, 
                                        is_final=True, 
                                        start_time=absolute_start_time + window_offset + s.start
                                    )
                                    logging.info(f"FINAL (Segment): {s_text}")
                                    last_finalized_end_rel = s.end
                                    total_words_finalized += len(s_text.split())
                                    total_speech_seconds += max(0.2, s.end - s.start)
                                    transcription_history.append(s_text)
                                    transcription_history = transcription_history[-5:]
                                else:
                                    all_speech_text_parts.append(s_text)
                                continue

                            for w_idx, w in enumerate(s.words):
                                w_text = w.word.strip()
                                if not w_text: continue
                                current_sentence_words.append(w_text)
                                
                                # --- Contextual Split Protection ---
                                has_strong = any(w_text.endswith(p) for p in STRONG_STOP)
                                has_soft = any(w_text.endswith(p) for p in SOFT_STOP)
                                is_stop = False
                                
                                # 1. Look Ahead: Is there another word IMMEDIATELY following this one?
                                # This is the highest priority - don't split if speech is continuous.
                                has_next_soon = False
                                if w_idx < len(s.words) - 1:
                                    next_w = s.words[w_idx + 1]
                                    if (next_w.start - w.end) < 0.4:
                                        has_next_soon = True
                                elif s_idx < len(segments_list) - 1:
                                    next_s = segments_list[s_idx + 1]
                                    if (next_s.start - w.end) < 0.4:
                                        has_next_soon = True
                                
                                if not has_next_soon:
                                    # Edge Protection variables
                                    is_absolute_last = (w_idx == len(s.words) - 1) and (s_idx == len(segments_list) - 1)
                                    silence_at_edge = total_duration - (window_offset + w.end)
                                    
                                    # Conjunction/Continuation check in next segments
                                    is_followed_by_continuation = False
                                    if s_idx < len(segments_list) - 1:
                                        next_text = segments_list[s_idx + 1].text.strip().lower()
                                        continuations = ["when", "and", "which", "but", "while", "that", "because", "the", "a"]
                                        if any(next_text.startswith(c) for c in continuations):
                                            is_followed_by_continuation = True
                                    
                                    # Higher word count for narrators to keep paragraphs whole
                                    min_words = 12 if avg_wpm < 100 else 6
                                    is_too_short = len(current_sentence_words) < min_words
                                    
                                    if has_strong:
                                        if is_absolute_last:
                                            # Edge word: require massive silence for narrators
                                            required = (2.5 if avg_wpm < 100 else 1.5) if is_too_short else 0.8
                                            is_stop = (silence_at_edge >= required)
                                        else:
                                            # Mid-segment: inhibit split if it's followed by a continuation
                                            # or if it's too short
                                            is_stop = not (is_too_short or is_followed_by_continuation)
                                    elif has_soft:
                                        # Soft split (comma)
                                        if is_absolute_last:
                                            is_stop = (silence_at_edge >= 1.5)
                                        else:
                                            is_stop = (silence_at_edge >= 1.0)

                                if is_stop:
                                    sentence_text = " ".join(current_sentence_words)
                                    yield transcription_pb2.TranscriptionResult(
                                        text=sentence_text,
                                        is_final=True,
                                        start_time=absolute_start_time + window_offset + w.start
                                    )
                                    logging.info(f"FINAL (Word): [{absolute_start_time + window_offset + w.start:06.2f}s] {sentence_text}")
                                    
                                    total_words_finalized += len(current_sentence_words)
                                    duration_finalized = (w.end - (w.start if len(current_sentence_words) == 1 else s.words[0].start))
                                    total_speech_seconds += max(0.1, duration_finalized)
                                    
                                    transcription_history.append(sentence_text)
                                    transcription_history = transcription_history[-5:]
                                    
                                    # Slicing cushion
                                    last_finalized_end_rel = min(total_duration - window_offset, w.end + 0.05)
                                    current_sentence_words = []

                        # Remaining text for partial update or forced finalization
                        remaining_text = " ".join(current_sentence_words + all_speech_text_parts).strip()
                        
                        # --- Force Finalization Check (Outside Loop) ---
                        latest_speech_timestamp_rel = 0.0
                        for s in segments_list:
                            if s.no_speech_prob < 0.4:
                                latest_speech_timestamp_rel = max(latest_speech_timestamp_rel, s.end)
                        
                        total_silence = total_duration - (window_offset + latest_speech_timestamp_rel)
                        
                        if remaining_text != last_speech_text:
                            last_speech_text = remaining_text
                            last_text_change_time = total_duration
                        total_stall = total_duration - last_text_change_time

                        # Fallback triggers (silence, stall, safety cap)
                        global_trigger = (samples_in_utterance >= max_utterance_samples) or (consecutive_quiet_intervals >= 2)
                        should_force_fallback = (total_silence >= required_silence) or \
                                               (total_stall >= stall_threshold and total_silence >= 0.4)
                        
                        if (global_trigger or should_force_fallback) and remaining_text:
                            # Anti-Hallucination Sink: Catch common "politeness" hallucinations during pauses
                            words = remaining_text.split()
                            clean_text = remaining_text.lower().replace(".", "").replace("!", "").replace("?", "").strip()
                            
                            # Whisper often hallucinations these during silence gaps
                            SINK_WORDS = ["please", "thanks", "thank you", "bye", "you", "it", "with", "the"]
                            is_hallucination = (len(words) == 1 and clean_text in SINK_WORDS)
                            
                            is_junk = (len(words) < 3 and (not any(p in remaining_text for p in STRONG_STOP) or total_silence > 1.0)) or is_hallucination
                            
                            if is_junk:
                                # Carry over
                                pass
                            else:
                                # Finalize the entire remainder as one block
                                yield transcription_pb2.TranscriptionResult(
                                    text=remaining_text, is_final=True, start_time=absolute_start_time + window_offset
                                )
                                logging.info(f"FINAL (Forced): [{absolute_start_time + window_offset:06.2f}s] {remaining_text}")
                                
                                # Complete reset
                                utterance_buffer = []
                                samples_in_utterance = 0
                                absolute_start_time += total_duration
                                last_speech_text = ""
                                last_text_change_time = total_duration
                                # Mark as fully processed
                                remaining_text = "" 
                        elif last_finalized_end_rel > 0:
                            # Tail preservation based on last punctuation split
                            actual_split_time = window_offset + last_finalized_end_rel
                            split_sample = int(actual_split_time * samples_per_second)
                            
                            tail_audio = full_audio_v[split_sample:]
                            absolute_start_time += actual_split_time
                            utterance_buffer = [tail_audio] if len(tail_audio) > 0 else []
                            samples_in_utterance = len(tail_audio)
                            
                            last_speech_text = ""
                            last_text_change_time = 0.0
                        else:
                            # Emergency Cleanup for silent/stuck buffers
                            if global_trigger or consecutive_quiet_intervals >= 10:
                                logging.info(f"EMERGENCY Cleanup ({total_duration:.1f}s)")
                                utterance_buffer = []
                                samples_in_utterance = 0
                                absolute_start_time += total_duration
                                last_speech_text = ""
                            elif remaining_text:
                                # Regular partial update
                                yield transcription_pb2.TranscriptionResult(
                                    text=remaining_text, is_final=False, start_time=absolute_start_time + window_offset
                                )
                                logging.info(f"DEBUG: dur={total_duration:.1f}s, silence={total_silence:.1f}s, words={num_words_window}")
                                
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