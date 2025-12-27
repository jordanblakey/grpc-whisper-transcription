import asyncio
import os
import contextlib
import sys
import sounddevice as sd
import time
from kokoro_onnx import Kokoro

os.environ["ORT_LOGGING_LEVEL"] = "3"
import onnxruntime as ort

# print(ort.get_available_providers())
# exit()

# --- Setup & Singleton Initialization ---
here = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(here, "kokoro-v1.0.onnx")
VOICES_PATH = os.path.join(here, "voices-v1.0.bin")

# Global instance to ensure we only load the 80MB+ model once
_KOKORO_INSTANCE = None

def get_engine():
    global _KOKORO_INSTANCE
    if _KOKORO_INSTANCE is None:
        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        sess_options.log_severity_level = 3
        
        providers = [
            ('CUDAExecutionProvider', {
                'device_id': 0,
                'arena_extend_strategy': 'kSameAsRequested',
            }),
            'CPUExecutionProvider'
        ]
        
        with silence_stderr():
            session = ort.InferenceSession(
                MODEL_PATH, 
                sess_options=sess_options, 
                providers=providers
            )
        _KOKORO_INSTANCE = Kokoro.from_session(session, VOICES_PATH)
    return _KOKORO_INSTANCE

async def _warmup():
    """Internal helper to prime the voice tensors."""
    engine = get_engine()
    stream = engine.create_stream(" ", voice="am_fenrir", speed=1.0, lang="en-us")
    async for _ in stream:
        pass

async def _async_narrate(text: str, voice: str = "am_fenrir"):
    engine = get_engine()
    
    # 1. Start the timer immediately before inference
    start_time = time.perf_counter()
    
    stream = engine.create_stream(text, voice=voice, speed=1.0, lang="en-us")
    
    first_chunk = True
    async for samples, sample_rate in stream:
        if first_chunk:
            # 2. End the timer as soon as the first chunk is generated
            end_time = time.perf_counter()
            latency_ms = (end_time - start_time) * 1000
            # print(f"DEBUG: Time to First Audio: {latency_ms:.2f}ms")
            first_chunk = False
            
        sd.play(samples, sample_rate)
        sd.wait()
# --- Public API for other files ---

def narrate(text: str, voice: str = "am_fenrir"):
    """
    The main entry point for other scripts. 
    Handles the event loop automatically.
    """
    try:
        # Try to get the existing loop (if one is running)
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # If we are already inside an async app (like a FastAPI server or Bot)
        return loop.create_task(_async_narrate(text, voice))
    else:
        # For standard synchronous scripts
        return asyncio.run(_async_narrate(text, voice))

@contextlib.contextmanager
def silence_stderr():
    """Redirects stderr to /dev/null at the system level."""
    # Save the original stderr file descriptor
    stderr_fd = sys.stderr.fileno()
    with os.fdopen(os.dup(stderr_fd), 'wb') as copied:
        # Open /dev/null
        with open(os.devnull, 'wb') as devnull:
            # Point stderr to /dev/null
            sys.stderr.flush()
            os.dup2(devnull.fileno(), stderr_fd)
            try:
                yield
            finally:
                # Restore original stderr
                sys.stderr.flush()
                os.dup2(copied.fileno(), stderr_fd)

# Automatically warm up on import if you want zero-lag first calls
# Warning: This adds about 0.5s to the initial 'import voice_engine' line
asyncio.run(_warmup())
