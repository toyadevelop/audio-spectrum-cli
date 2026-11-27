"""Focused tests for generated chirps and spectrogram scaling."""

import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from analyze import compute_spectrogram
from generate_test_wav import generate_test_wav


class TestChirpGeneration(unittest.TestCase):
    def test_chirp_is_two_seconds_and_sweeps_up(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "chirp.wav"
            generate_test_wav(output, "chirp")
            sample_rate, audio = wavfile.read(output)

        self.assertEqual(sample_rate, 48_000)
        self.assertEqual(audio.shape, (96_000,))
        early_crossings = np.count_nonzero(np.diff(np.signbit(audio[:4_800])))
        late_crossings = np.count_nonzero(np.diff(np.signbit(audio[-4_800:])))
        self.assertGreater(early_crossings, 0)
        self.assertGreater(late_crossings, early_crossings * 100)


class TestSpectrogram(unittest.TestCase):
    def test_spectrogram_amplitude_is_calibrated_to_dbfs(self) -> None:
        sample_rate = 48_000
        n_fft = 1024
        time = np.arange(sample_rate) / sample_rate
        audio = 0.5 * np.sin(2 * np.pi * 750 * time)

        frequencies, frame_times, spectrum_db = compute_spectrogram(
            audio, sample_rate, n_fft
        )

        self.assertEqual(spectrum_db.shape, (n_fft // 2 + 1, frame_times.size))
        self.assertEqual(frequencies[16], 750)
        self.assertAlmostEqual(float(np.max(spectrum_db[16])), -6.0206, delta=0.1)
        self.assertTrue(np.all(np.isfinite(spectrum_db)))


if __name__ == "__main__":
    unittest.main()
