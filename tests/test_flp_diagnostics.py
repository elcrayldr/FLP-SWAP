import struct
import tempfile
import unittest
from pathlib import Path

from flpswap.flp_diagnostics import compare_inventories, inventory_flp


def make_flp(events: bytes) -> bytes:
    return (
        b"FLhd" + struct.pack("<IHHH", 6, 0, 1, 96)
        + b"FLdt" + struct.pack("<I", len(events)) + events
    )


class FlpDiagnosticsTests(unittest.TestCase):
    def test_inventory_counts_fixed_and_variable_events(self):
        # Event ID 1 has a one-byte payload; ID 200 has varint length 3.
        events = bytes([1, 0x2A, 200, 3]) + b"abc" + bytes([199, 4]) + b"20.8"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.flp"
            path.write_bytes(make_flp(events))
            inventory = inventory_flp(path)
        self.assertEqual(inventory.event_count, 3)
        self.assertEqual(inventory.event_id_counts[1], 1)
        self.assertEqual(inventory.event_id_counts[200], 1)
        self.assertEqual(inventory.version_payloads, ("20.8",))

    def test_rejects_truncated_event(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.flp"
            path.write_bytes(make_flp(bytes([200, 5, 1])))
            with self.assertRaises(ValueError):
                inventory_flp(path)

    def test_compare_detects_event_loss(self):
        with tempfile.TemporaryDirectory() as directory:
            before_path = Path(directory) / "before.flp"
            after_path = Path(directory) / "after.flp"
            before_path.write_bytes(make_flp(bytes([1, 1, 2, 2])))
            after_path.write_bytes(make_flp(bytes([1, 1])))
            result = compare_inventories(inventory_flp(before_path), inventory_flp(after_path))
        self.assertFalse(result["event_id_counts_match_except_version_event"])
        self.assertEqual(result["event_id_count_changes"][0]["event_id"], 2)


if __name__ == "__main__":
    unittest.main()
