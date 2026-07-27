from filters_tool.matcher import evaluate_all, evaluate_filter


def test_assignment_worked_example():
    """Matches the exact example from the assignment spec."""
    filters = {
        "kotlin_sources": ["**/*.kt", "!**/test/**"],
        "tests": ["**/test/**/*.kt"],
        "documentation": ["README.md", "docs/**"],
    }
    changed_files = ["App.kt", "src/test/FiltersTest.kt", "README.md"]

    results = {r.name: r.matched for r in evaluate_all(filters, changed_files)}

    assert results == {
        "kotlin_sources": True,
        "tests": True,
        "documentation": True,
    }


def test_per_file_semantics_not_globally_poisoned():
    """
    A file matching an exclusion pattern must not prevent a *different* file
    from matching the same filter's inclusion pattern. This guards against the
    common bug of computing "any include" and "any exclude" as independent
    global booleans instead of evaluating per file.
    """
    result = evaluate_filter(
        "backend",
        ["app/**/*.kt", "!app/test/**"],
        ["app/src/Main.kt", "app/test/Foo.kt"],
    )
    assert result.matched is True
    assert result.matched_by == "app/src/Main.kt"


def test_excluded_file_does_not_match():
    result = evaluate_filter(
        "backend",
        ["app/**/*.kt", "!app/test/**"],
        ["app/test/Foo.kt"],
    )
    assert result.matched is False
    assert result.matched_by is None


def test_no_relevant_files_does_not_match():
    result = evaluate_filter("docs", ["docs/**/*.md"], ["app/src/Main.kt"])
    assert result.matched is False
    assert result.file_traces == []


def test_empty_pattern_list_never_matches():
    result = evaluate_filter("empty", [], ["anything.txt"])
    assert result.matched is False
    assert result.file_traces == []


def test_only_exclusion_patterns_never_matches():
    """A filter with no inclusion patterns can never match anything."""
    result = evaluate_filter("odd", ["!**/test/**"], ["app/src/Main.kt", "app/test/Foo.kt"])
    assert result.matched is False


def test_empty_changed_files_all_false():
    filters = {"backend": ["app/**"], "docs": ["docs/**"]}
    results = {r.name: r.matched for r in evaluate_all(filters, [])}
    assert results == {"backend": False, "docs": False}


def test_trace_records_deciding_pattern_order():
    result = evaluate_filter(
        "kotlin_sources",
        ["**/*.kt", "!**/test/**"],
        ["src/test/FiltersTest.kt"],
    )
    trace = result.file_traces[0]
    assert [h.pattern_text for h in trace.hits] == ["**/*.kt", "!**/test/**"]
    assert trace.included is False  # last hit is the exclusion
