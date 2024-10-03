"""Processes a WAV file using the audio processor."""

import argparse
import wave

from pyspeex_noise import AudioProcessor

SAMPLES_10MS = 160


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument("wav_in", help="WAV input file (16Khz 16-bit mono)")
    parser.add_argument("wav_out", help="WAV output file")
    parser.add_argument("--auto-gain", type=float, default=4000)
    parser.add_argument("--noise-suppression", type=int, default=-30)
    args = parser.parse_args()

    audio_processor = AudioProcessor(args.auto_gain, args.noise_suppression)

    wav_in: wave.Wave_read = wave.open(args.wav_in, "rb")
    with wav_in:
        assert wav_in.getframerate() == 16000, "Sample rate must be 16Khz"
        assert wav_in.getsampwidth() == 2, "Sample width must be 16-bit"
        assert wav_in.getnchannels() == 1, "Only mono audio is supported"

        wav_out: wave.Wave_write = wave.open(args.wav_out, "wb")
        with wav_out:
            wav_out.setframerate(16000)
            wav_out.setsampwidth(2)
            wav_out.setnchannels(1)

            # Process in 10ms chunks
            chunk = wav_in.readframes(SAMPLES_10MS)
            while chunk:
                if len(chunk) < SAMPLES_10MS:
                    wav_out.writeframes(chunk)
                    break

                processed = audio_processor.Process10ms(chunk)
                wav_out.writeframes(processed.audio)
                chunk = wav_in.readframes(SAMPLES_10MS)


if __name__ == "__main__":
    main()
