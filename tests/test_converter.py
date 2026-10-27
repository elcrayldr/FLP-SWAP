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

    def test_downgrades_fl25_playlist_records_to_fl24_record_size(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "fl25.flp"
            output = Path(directory) / "fl24.flp"
            banner = "FL Studio 25.2.4.4960.4960\\x00".encode("utf-16le")
            banner_event = bytes([0xC0, len(banner)]) + banner
            playlist = bytes(range(80)) + bytes(range(80))
            playlist_event = bytes([0xE9, 80]) + playlist[:80] + bytes([0xE9, 80]) + playlist[80:]
            events = (
                bytes([0xAC, 1, 1, 0])
                + banner_event
                + text_event(199, "25.2.4.4960")
                + bytes([159]) + struct.pack("<I", 4960)
                + playlist_event
            )
            source.write_bytes(make_flp(events))
            output_report = convert_flp(source, output, "24.1.0")
            out_raw = output.read_bytes()
            _, out_events, _ = __import__("flpswap.flp_migration", fromlist=["read_events"]).read_events(out_raw)
            e9_payloads = [event.payload for event in out_events if event.event_id == 0xE9]
            self.assertEqual(len(e9_payloads), 2)
            self.assertEqual([len(payload) for payload in e9_payloads], [60, 60])
            self.assertEqual(e9_payloads[0] + e9_payloads[1], playlist[:60] + playlist[80:140])
            self.assertEqual(output_report["migration"]["playlist_records_resized"], 2)
            self.assertFalse(any(event.event_id == 0x9F for event in out_events))

    def test_fl25_1_playlist_layout_is_detected_without_fl25_2_banner(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "fl25_1.flp"
            output = Path(directory) / "fl24.flp"
            playlist = bytes(range(80))
            playlist_event = bytes([0xE9, 80]) + playlist
            events = text_event(199, "25.1.6.4997") + bytes([159]) + struct.pack("<I", 4997) + playlist_event
            source.write_bytes(make_flp(events))

            report = convert_flp(source, output, "24.1.0")
            from flpswap.flp_migration import read_events
            _, events_out, _ = read_events(output.read_bytes())
            clips = [event.payload for event in events_out if event.event_id == 0xE9]
            self.assertEqual(len(clips), 1)
            self.assertEqual(len(clips[0]), 60)
            self.assertEqual(clips[0], playlist[:60])
            self.assertEqual(report["migration"]["playlist_records_resized"], 1)


if __name__ == "__main__":
    unittest.main()
