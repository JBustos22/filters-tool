import pytest

from filters_tool.config import ConfigError, load_filters

FIXTURE = "tests/fixtures/filters.yaml"


def test_loads_valid_fixture():
    filters = load_filters(FIXTURE)
    assert set(filters.keys()) == {"kotlin_sources", "tests", "documentation"}
    assert filters["kotlin_sources"] == ["**/*.kt", "!**/test/**"]


def test_missing_file_raises(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_filters(str(tmp_path / "nope.yaml"))


def test_malformed_yaml_raises(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("filters: [this, is, not, a, mapping")
    with pytest.raises(ConfigError, match="invalid YAML"):
        load_filters(str(bad))


def test_missing_filters_key_raises(tmp_path):
    f = tmp_path / "no_filters_key.yaml"
    f.write_text("something_else:\n  a: 1\n")
    with pytest.raises(ConfigError, match="missing the required"):
        load_filters(str(f))


def test_empty_file_raises(tmp_path):
    f = tmp_path / "empty.yaml"
    f.write_text("")
    with pytest.raises(ConfigError, match="empty"):
        load_filters(str(f))


def test_empty_filters_block_is_valid(tmp_path):
    f = tmp_path / "empty_filters.yaml"
    f.write_text("filters:\n")
    assert load_filters(str(f)) == {}


def test_filter_with_no_patterns_is_valid(tmp_path):
    f = tmp_path / "empty_pattern_list.yaml"
    f.write_text("filters:\n  backend:\n")
    assert load_filters(str(f)) == {"backend": []}


def test_non_list_patterns_raises(tmp_path):
    f = tmp_path / "bad_shape.yaml"
    f.write_text("filters:\n  backend: \"not_a_list\"\n")
    with pytest.raises(ConfigError, match="must be a list"):
        load_filters(str(f))


def test_non_string_pattern_raises(tmp_path):
    f = tmp_path / "bad_pattern.yaml"
    f.write_text("filters:\n  backend:\n    - 123\n")
    with pytest.raises(ConfigError, match="non-string pattern"):
        load_filters(str(f))


def test_filters_not_a_mapping_raises(tmp_path):
    f = tmp_path / "filters_list.yaml"
    f.write_text("filters:\n  - not\n  - a\n  - mapping\n")
    with pytest.raises(ConfigError, match="must be a mapping"):
        load_filters(str(f))
