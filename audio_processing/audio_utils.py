from contextlib import contextmanager
import os
import sys

@contextmanager
def no_alsa_err():
    """
    Context manager to suppress ALSA/Jack error messages by redirecting stderr to /dev/null.
    Useful when initializing PyAudio on Linux to avoid cluttering the console with harmless warnings.
    """
    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        old_stderr = os.dup(2)
        sys.stderr.flush()
        os.dup2(devnull, 2)
        os.close(devnull)
        yield
    finally:
        os.dup2(old_stderr, 2)
        os.close(old_stderr)
