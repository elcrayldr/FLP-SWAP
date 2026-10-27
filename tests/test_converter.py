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
            self.assertTrue(report["migration"]["build_event_updated"])
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

    def test_downgrades_fl25_2_to_fl25_1_using_known_special_event_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "fl25_2.flp"
            output = Path(directory) / "fl25_1.flp"
            banner = "FL Studio 25.2.4.4960.4960\\x00".encode("utf-16le")
            banner_event = bytes([0xC0, len(banner)]) + banner
            playlist = bytes(range(80))
            playlist_event = bytes([0xE9, len(playlist)]) + playlist
            events = (
                bytes([0xAC, 1, 1, 0])
                + banner_event
                + text_event(199, "25.2.4.4960")
                + bytes([159]) + struct.pack("<I", 4960)
                + playlist_event
            )
            source.write_bytes(make_flp(events))
            original = source.read_bytes()

            report = convert_flp(source, output, "25.1.6.4997")

            result = output.read_bytes()
            self.assertEqual(source.read_bytes(), original)
            self.assertTrue(report["source_preserved"])
            self.assertEqual(report["detected_source_version"], "25.2.4.4960")
            self.assertEqual(report["target_version"], "25.1.6.4997")
            self.assertEqual(report["migration"]["removed_known_fl25_events"], ["0xAC", "0xC0-banner"])
            self.assertNotIn(bytes([0xAC, 1, 1, 0]), result)
            self.assertNotIn(banner_event, result)
            self.assertIn(struct.pack("<I", 4997), result)
            self.assertFalse(report["compatibility_verified"])

    def test_refuses_lossy_playlist_downgrade_instead_of_truncating_clip_records(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "fl25.flp"
            output = Path(directory) / "fl24.flp"
            banner = "FL Studio 25.2.4.4960.4960\\x00".encode("utf-16le")
            banner_event = bytes([0xC0, len(banner)]) + banner
            playlist = bytes(range(80))
            playlist_event = bytes([0xE9, len(playlist)]) + playlist
            events = (
                bytes([0xAC, 1, 1, 0])
                + banner_event
                + text_event(199, "25.2.4.4960")
                + bytes([159]) + struct.pack("<I", 4960)
                + playlist_event
            )
            source.write_bytes(make_flp(events))
            with self.assertRaisesRegex(ConversionError, "proteger el proyecto"):
                convert_flp(source, output, "24.1.0")
            self.assertFalse(output.exists())

    def test_refuses_fl25_1_playlist_downgrade_without_field_aware_migration(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "fl25_1.flp"
            output = Path(directory) / "fl24.flp"
            playlist = bytes(range(80))
            playlist_event = bytes([0xE9, len(playlist)]) + playlist
            events = text_event(199, "25.1.6.4997") + bytes([159]) + struct.pack("<I", 4997) + playlist_event
            source.write_bytes(make_flp(events))

            with self.assertRaisesRegex(ConversionError, "proteger el proyecto"):
                convert_flp(source, output, "24.1.0")
            self.assertFalse(output.exists())

    def test_converts_legacy_fruityloops_file_without_version_event_when_source_is_declared(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "fruityloops_1.flp"
            output = Path(directory) / "fruityloops_copy.flp"
            source.write_bytes(make_flp(bytes([1, 0x2A])))

            report = convert_flp(source, output, "1.0.0", declared_source_version="1.0.0")

            self.assertTrue(output.exists())
            self.assertTrue(report["source_preserved"])
            self.assertEqual(report["detected_source_version"], "1.0.0")
            self.assertFalse(report["migration"]["target_supports_version_event"])


if __name__ == "__main__":
    unittest.main()
