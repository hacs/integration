# Use secrets module if available (Python version >= 3.6) per PEP 506
try:
    from secrets import SystemRandom  # type: ignore
except ImportError:
    from random import SystemRandom

random = SystemRandom()
