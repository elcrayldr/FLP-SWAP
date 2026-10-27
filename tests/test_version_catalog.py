from flpswap.version_catalog import find_release


def test_windows_and_macos_builds_are_separate():
    assert find_release("21.2.3", "windows", "4004") is not None
    assert find_release("21.2.3", "macos", "3586") is not None
    assert find_release("21.2.3", "windows", "3586") is None


def test_fl_studio_26_1_7_build_5654_is_identified():
    release = find_release("26.1.7", "windows", "5654")
    assert release is not None
    assert release.channel == "stable"


def test_unknown_build_is_not_guessed():
    assert find_release("21.3.6", "windows", "9999") is None
