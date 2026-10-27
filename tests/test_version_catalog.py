from flpswap.version_catalog import find_release


def test_windows_and_macos_builds_are_separate():
    assert find_release("21.2.3", "windows", "4004") is not None
    assert find_release("21.2.3", "macos", "3586") is not None
    assert find_release("21.2.3", "windows", "3586") is None


def test_fl_studio_26_1_7_build_5654_is_identified():
    release = find_release("26.1.7", "windows", "5654")
    assert release is not None
    assert release.channel == "release"


def test_unknown_build_is_not_guessed():
    assert find_release("21.3.6", "windows", "9999") is None


from flpswap.fl_versions import VERSION_LABELS, INTERNAL_VERSION_OVERRIDES
from flpswap.app import internal_version


def test_catalog_contains_all_requested_release_labels():
    assert len(VERSION_LABELS) == 110
    assert len(set(VERSION_LABELS)) == 110
    assert VERSION_LABELS[0] == "FruityLoops 1.0.0"
    assert VERSION_LABELS[-1] == "FL Studio 2026.1.7"


def test_marketing_year_and_build_labels_map_to_internal_values():
    assert internal_version("FL Studio 2024.1") == "24.1.0"
    assert internal_version("FL Studio 2025.1.1 (Build 4879)") == "25.1.1.4879"
    assert internal_version("FL Studio 2025.2.5 (Build 5319)") == "25.2.5.5319"
    assert internal_version("FL Studio 2026.1.7") == "26.1.7.5654"
    assert internal_version("FruityLoops 1.2.7") == "1.2.7"
    assert internal_version("FL Studio 9.5") == "9.5.0"
    assert internal_version("FL Studio 20.8.3 (Build 2304)") == "20.8.3.2304"


def test_every_label_resolves_to_a_nonempty_version():
    for label in VERSION_LABELS:
        value = internal_version(label)
        assert value and value[0].isdigit()
