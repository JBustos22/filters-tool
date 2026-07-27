"""
Command-line entry point for the filters tool.

Usage (typical, in GitLab CI):
    git diff --name-only $CI_MERGE_REQUEST_DIFF_BASE_SHA... | python -m filters_tool --config filters.yaml

Exit codes:
    0 - successful run (regardless of whether any individual filter matched)
    1 - usage or configuration error (bad --config path, invalid YAML,
        missing 'filters:' key, no changed-files input mechanism provided)
"""

import argparse
import sys

from .config import ConfigError, load_filters
from .matcher import evaluate_all
from .output import write_env


def _read_changed_files(changed_files_file: str | None) -> list:
    """
    Resolve the list of changed file paths.

    An explicitly-given --changed-files-file always wins over stdin, even if
    stdin also has data piped into it. If neither is available (no flag, and
    stdin is an interactive terminal rather than a pipe/redirect), this is
    treated as a usage error -- there's no legitimate reason to run this tool
    in CI with no input mechanism at all. An empty list from a valid input
    mechanism (e.g. an empty diff) is not an error; it just means every
    filter will evaluate to false.
    """
    if changed_files_file is not None:
        try:
            with open(changed_files_file) as f:
                lines = f.read().splitlines()
        except OSError as e:
            raise SystemExit(f"error: could not read --changed-files-file: {e}")
        return [line for line in lines if line.strip()]

    if sys.stdin.isatty():
        raise SystemExit(
            "error: no changed files provided. Pipe file paths via stdin "
            "(e.g. `git diff --name-only ... | filter-tool --config filters.yaml`) "
            "or pass --changed-files-file."
        )

    lines = sys.stdin.read().splitlines()
    return [line for line in lines if line.strip()]


def _print_explain(results: list) -> None:
    """Filter-first, file-second trace of every pattern decision, to stderr."""
    for r in results:
        print(f"[{r.name}]", file=sys.stderr)
        if not r.file_traces:
            print("  (no changed file interacted with this filter's patterns)", file=sys.stderr)
        for trace in r.file_traces:
            hit_descriptions = []
            for hit in trace.hits:
                verb = "included" if hit.include else "excluded"
                hit_descriptions.append(f'{verb} by "{hit.pattern_text}"')
            print(f"  {trace.path}: " + ", then ".join(hit_descriptions), file=sys.stderr)
        verdict = "true" if r.matched else "false"
        by = f" (matched by {r.matched_by})" if r.matched_by else ""
        print(f"  RESULT: {verdict}{by}", file=sys.stderr)
        print(file=sys.stderr)


def _print_verbose(results: list) -> None:
    """One-line summary per filter, to stderr."""
    for r in results:
        verdict = "true" if r.matched else "false"
        by = f" (matched by {r.matched_by})" if r.matched_by else ""
        print(f"[{r.name}] {verdict}{by}", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="filters-tool",
        description=(
            "Evaluate named glob-pattern filters (filters.yaml) against a list of "
            "changed file paths, and write the results as name=true/false lines "
            "to filters.env for GitLab CI's dotenv artifact report."
        ),
        epilog=(
            "Example:\n"
            "  git diff --name-only main... | filters-tool --config filters.yaml\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--config", required=True, metavar="PATH",
        help="Path to filters.yaml",
    )
    parser.add_argument(
        "--changed-files-file", metavar="PATH", default=None,
        help="File with one changed path per line. If omitted, changed files are read from stdin.",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Log a one-line match/no-match summary per filter to stderr.",
    )
    parser.add_argument(
        "--explain", action="store_true",
        help="Log a full per-file, per-pattern trace to stderr, showing which "
             "pattern decided each file's inclusion or exclusion (implies --verbose).",
    )
    return parser


def main(argv: list | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        filters = load_filters(args.config)
    except ConfigError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    changed_files = _read_changed_files(args.changed_files_file)

    results = evaluate_all(filters, changed_files)

    write_env(results)

    if args.explain:
        _print_explain(results)
    elif args.verbose:
        _print_verbose(results)

    return 0


if __name__ == "__main__":
    sys.exit(main())
