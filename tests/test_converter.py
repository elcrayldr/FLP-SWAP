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


    def test_cancels_if_serializer_drops_an_event_type(self):
        import struct
        import sys
        import types
        from unittest.mock import patch

        def make_flp(events):
            return (
                b"FLhd" + struct.pack("<IHHH", 6, 0, 1, 96)
                + b"FLdt" + struct.pack("<I", len(events)) + events
            )

        class FakeProject:
            def __init__(self):
                self.version = "20.8.3.2304"

        def fake_parse(_path):
            return FakeProject()

        def fake_save(project, path):
            version = project.version.encode("ascii")
            # Deliberately drop event ID 2 to simulate a lossy serializer.
            events = bytes([1, 0x2A, 199, len(version)]) + version
            Path(path).write_bytes(make_flp(events))

        fake_pyflp = types.SimpleNamespace(parse=fake_parse, save=fake_save)
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.flp"
            output = Path(directory) / "output.flp"
            version = b"20.8.3.2304"
            events = bytes([1, 0x2A, 2, 0x2B, 199, len(version)]) + version
            source.write_bytes(make_flp(events))
            with patch.dict(sys.modules, {"pyflp": fake_pyflp}):
                with self.assertRaisesRegex(ConversionError, "cambiad"):
                    convert_flp(source, output, "26.1.7.5654")
            self.assertFalse(output.exists())
            self.assertTrue(source.exists())


if __name__ == "__main__":
    unittest.main()
