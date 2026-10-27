import tempfile
import unittest
from pathlib import Path

from flpswap.converter import ConversionError, convert_flp


class ConverterGuardrailTests(unittest.TestCase):
    def test_rejects_same_source_and_output_path(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "same.flp"
            source.write_bytes(b"not a valid FLP")
            with self.assertRaises(ConversionError):
                convert_flp(source, source, "26.1.7")

    def test_rejects_non_flp_input_before_using_pyflp(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "bad.flp"
            output = Path(directory) / "out.flp"
            source.write_bytes(b"not a valid FLP")
            with self.assertRaises(ConversionError):
                convert_flp(source, output, "26.1.7")
            self.assertFalse(output.exists())

    def test_rejects_invalid_target_version(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.txt"
            output = Path(directory) / "out.flp"
            source.write_bytes(b"")
            with self.assertRaises(ConversionError):
                convert_flp(source, output, "FL Studio 26")


if __name__ == "__main__":
    unittest.main()
