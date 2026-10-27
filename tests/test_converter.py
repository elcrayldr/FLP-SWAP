import struct
import tempfile
import unittest
from pathlib import Path

from flpswap.converter import ConversionError, convert_flp


def make_flp(events, channel_count=1, ppq=96):
    return (
        b"FLhd" + struct.pack("<IHHH", 6, 0, channel_count, ppq)
        + b"FLdt" + struct.pack("<I", len(events)) + events
    )


def text_event(event_id, value):
    payload = value.encode("ascii") + b"\x00"
    return bytes([event_id, len(payload)]) + payload


class ConverterGuardrailTests(unittest.TestCase):
    def test_rejects_same_source_and_output_path(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "same.flp"
            source.write_bytes(b"not a valid FLP")
            with self.assertRaises(ConversionError):
                convert_flp(source, source, "26.1.7")

    def test_rejects_non_flp_input_before_writing_output(self):
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

    def test_rewrites_version_and_preserves_all_other_event_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.flp"
            output = Path(directory) / "output.flp"
            # Include an unknown/opaque event payload to ensure it survives exactly.
            untouched = bytes([2, 0x2B, 200, 4, 0x00, 0xFF, 0x41, 0x80])
            events = (
                bytes([1, 0x2A])
                + untouched
                + text_event(199, "20.8.3.2304")
                + bytes([159]) + struct.pack("<I", 2304)
            )
            source.write_bytes(make_flp(events))
            original = source.read_bytes()

            report = convert_flp(source, output, "26.1.7.5654")

            result = output.read_bytes()
            self.assertEqual(source.read_bytes(), original)
            self.assertTrue(report["source_preserved"])
            self.assertEqual(report["detected_source_version"], "20.8.3.2304")
            self.assertEqual(report["target_version"], "26.1.7.5654")
            self.assertTrue(report["build_event_updated"])
            self.assertIn(untouched, result)
            self.assertEqual(report["input_event_count"], report["output_event_count"])
            self.assertFalse(report["compatibility_verified"])

    def test_refuses_to_convert_without_version_event(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.flp"
            output = Path(directory) / "output.flp"
            source.write_bytes(make_flp(bytes([1, 0x2A])))
            with self.assertRaisesRegex(ConversionError, "versión"):
                convert_flp(source, output, "26.1.7.5654")
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
