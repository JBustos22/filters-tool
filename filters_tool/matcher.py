"""
Core filter-matching logic.

A "filter" is a named list of glob patterns (gitignore-style), where a
leading "!" marks an exclusion pattern. A filter matches the changed-file
set if at least one changed file is "included" by the patterns -- i.e.
the last pattern (in list order) that matches that file is an inclusion
pattern, not an exclusion pattern. This mirrors standard gitignore
semantics: later patterns override earlier ones on a per-file basis.

This module is deliberately independent of argparse/stdin/file I/O so it
can be unit tested directly and reused by the CLI layer.
"""

from dataclasses import dataclass, field
import pathspec


@dataclass
class PatternHit:
    """Record of a single pattern matching a single file."""
    pattern_text: str
    include: bool


@dataclass
class FileTrace:
    """Full trace of how one file was evaluated against one filter's patterns."""
    path: str
    hits: list = field(default_factory=list)  # list[PatternHit], in pattern order

    @property
    def deciding_hit(self):
        """The last matching pattern -- the one whose include/exclude wins."""
        return self.hits[-1] if self.hits else None

    @property
    def included(self) -> bool:
        hit = self.deciding_hit
        return hit is not None and hit.include


@dataclass
class FilterResult:
    """Result of evaluating one named filter against a set of changed files."""
    name: str
    matched: bool
    matched_by: str | None  # path of the file that caused a True result, if any
    file_traces: list  # list[FileTrace], only for files that had >=1 pattern hit


def _compile(patterns: list) -> pathspec.PathSpec:
    """
    Compile a list of pattern strings using gitignore ("gitwildmatch") semantics,
    which is what implements the "*", "**", and "!"-exclusion behavior this
    tool's filters.yaml format is based on.
    """
    return pathspec.PathSpec.from_lines("gitwildmatch", patterns)


def trace_file(spec: pathspec.PathSpec, patterns: list, file_path: str) -> FileTrace:
    """
    Evaluate a single file against a compiled pattern spec, recording every
    pattern that matched it (in order). The last hit determines the outcome.
    """
    trace = FileTrace(path=file_path)
    for pattern_text, compiled in zip(patterns, spec.patterns):
        if compiled.pattern is None:
            # A blank/comment line compiles to a null pattern; nothing to match.
            continue
        if compiled.match_file(file_path) is not None:
            trace.hits.append(PatternHit(pattern_text=pattern_text, include=compiled.include))
    return trace


def evaluate_filter(name: str, patterns: list, changed_files: list) -> FilterResult:
    """
    Evaluate one named filter's patterns against the full list of changed files.

    A filter matches if any changed file's deciding pattern is an inclusion.
    Files with no pattern interaction at all are omitted from file_traces to
    keep --explain output focused on files that were actually relevant.
    """
    if not patterns:
        return FilterResult(name=name, matched=False, matched_by=None, file_traces=[])

    spec = _compile(patterns)

    file_traces = []
    matched = False
    matched_by = None

    for file_path in changed_files:
        trace = trace_file(spec, patterns, file_path)
        if not trace.hits:
            continue  # irrelevant to this filter, skip from trace output
        file_traces.append(trace)
        if trace.included and not matched:
            matched = True
            matched_by = file_path

    return FilterResult(name=name, matched=matched, matched_by=matched_by, file_traces=file_traces)


def evaluate_all(filters: dict, changed_files: list) -> list:
    """
    Evaluate every named filter in filters.yaml's "filters" mapping against
    the changed file list. Returns a list of FilterResult, in the same order
    the filters were defined (dict insertion order, as parsed from YAML).
    """
    return [evaluate_filter(name, patterns, changed_files) for name, patterns in filters.items()]
