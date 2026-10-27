import hashlib
from pathlib import Path

from flpswap.flp_inspector import inspect_flp


def test_inspector_does_not_modify_file(tmp_path: Path):
    project = tmp_path / "demo.flp"
    original = b"TEST_FLP_SAMPLE_BYTES_123456"
    project.write_bytes(original)
    result = inspect_flp(project)
    assert project.read_bytes() == original
    assert result.sha256 == hashlib.sha256(original).hexdigest()
    assert result.status == "inspected_unverified_format"


def test_short_file_is_flagged(tmp_path: Path):
    project = tmp_path / "broken.flp"
    project.write_bytes(b"FLP")
    result = inspect_flp(project)
    assert result.status == "invalid_or_truncated"
