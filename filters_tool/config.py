"""
Loading and validation for filters.yaml.

Philosophy (per design discussion): fail loudly on things that indicate a
broken/misconfigured setup (missing file, invalid YAML syntax, missing
top-level "filters" key), but stay permissive on technically-valid-but-odd
data (empty filters block, a filter with zero patterns, a filter with only
exclusion patterns). Those are the config author's choice, not this tool's
job to second-guess.
"""

from pathlib import Path
import yaml


class ConfigError(Exception):
    """Raised for any problem with filters.yaml that should abort the run."""


def load_filters(config_path: str) -> dict:
    """
    Load and validate a filters.yaml file, returning the mapping of
    filter name -> list of pattern strings.

    Raises ConfigError with a human-readable message on any failure.
    """
    path = Path(config_path)
    if not path.is_file():
        raise ConfigError(f"config file not found: {config_path}")

    try:
        raw_text = path.read_text()
    except OSError as e:
        raise ConfigError(f"could not read config file {config_path}: {e}") from e

    try:
        data = yaml.safe_load(raw_text)
    except yaml.YAMLError as e:
        raise ConfigError(f"invalid YAML in {config_path}: {e}") from e

    if data is None:
        raise ConfigError(f"{config_path} is empty; expected a top-level 'filters:' key")

    if not isinstance(data, dict):
        raise ConfigError(
            f"{config_path} must be a YAML mapping with a top-level 'filters:' key"
        )

    if "filters" not in data:
        raise ConfigError(f"{config_path} is missing the required top-level 'filters:' key")

    filters = data["filters"]

    if filters is None:
        # `filters:` present but with nothing under it -- valid, just empty.
        return {}

    if not isinstance(filters, dict):
        raise ConfigError(
            f"'filters:' in {config_path} must be a mapping of filter name -> pattern list"
        )

    validated = {}
    for name, patterns in filters.items():
        if patterns is None:
            # `name:` with nothing under it -- treat as an empty pattern list.
            validated[name] = []
            continue
        if not isinstance(patterns, list):
            raise ConfigError(
                f"filter '{name}' in {config_path} must be a list of glob patterns"
            )
        for p in patterns:
            if not isinstance(p, str):
                raise ConfigError(
                    f"filter '{name}' in {config_path} contains a non-string pattern: {p!r}"
                )
        validated[name] = patterns

    return validated
