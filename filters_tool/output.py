"""
Writing the .env output file consumed by GitLab CI's `artifacts: reports: dotenv:`.

The output path is intentionally fixed (not configurable) so that any
GitLab CI pipeline using this tool can rely on a single, predictable
artifact path without needing to pass or track a custom filename.
"""

OUTPUT_FILENAME = "filters.env"


def write_env(results: list, output_path: str = OUTPUT_FILENAME) -> None:
    """
    Write one `name=true`/`name=false` line per FilterResult, in the order
    given (which matches the order filters were defined in filters.yaml).
    """
    lines = [f"{r.name}={'true' if r.matched else 'false'}" for r in results]
    content = "\n".join(lines) + ("\n" if lines else "")
    with open(output_path, "w") as f:
        f.write(content)
