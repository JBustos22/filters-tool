# filters-tool

A command-line tool that decides which CI/CD pipelines or jobs should run
based on which files changed in a commit or merge request — an analogue of
GitHub Actions' [`paths-changes-filter`](https://github.com/dorny/paths-filter),
built for GitLab CI.

It reads a `filters.yaml` file defining named filters as glob patterns,
compares those filters against a list of changed file paths, and writes the
results to a `filters.env` file that GitLab CI can consume via
`artifacts: reports: dotenv:`. This makes it possible to trigger only the
relevant backend, frontend, docs, or test jobs instead of running everything
on every change.

## `filters.yaml` format

```yaml
filters:
  backend:
    - "app/src/**/*.kt"
    - "!app/src/test/**"
  frontend:
    - "web/**/*.ts"
    - "web/**/*.tsx"
  docs:
    - "README.md"
    - "docs/**/*.md"
```

Each top-level key under `filters:` is a filter name. Its value is a list of
glob patterns, using gitignore-style glob syntax:

- `*` matches any characters within a single path segment.
- `**` matches zero or more path segments.
- A pattern prefixed with `!` is an **exclusion** pattern.
- For a given changed file, that file counts as **included** if it matches
  at least one inclusion pattern **and** does not match any exclusion
  pattern in the list
- A filter is considered **matched** (`true`) if at least one changed file
  ends up included.

This means exclusion patterns only cancel inclusion for the *same file* —
one file matching an exclude pattern does not prevent a different file from
still matching the filter.

## CLI reference

| Flag | Required | Description |
|---|---|---|
| `--config PATH` | yes | Path to `filters.yaml` |
| `--changed-files-file PATH` | no | File with one changed path per line. If omitted, changed files are read from stdin. |
| `--verbose` | no | Log a one-line match/no-match summary per filter to stderr |
| `--explain` | no | Log a full per-file, per-pattern trace to stderr |

Output is always written to `filters.env` in the current working directory —
this path is fixed, not configurable, so any pipeline using this tool can
rely on the same artifact path without tracking a custom filename.

## Using it in GitLab CI

The examples below assume the image is already published (see
[Publishing your own image](#publishing-your-own-image) if you want to build
and host your own instead of using a pre-built one).

A minimal example — see [`examples/gitlab-ci-basic.yml`](examples/gitlab-ci-basic.yml):

```yaml
stages:
  - detect-changes
  - test

paths-check:
  stage: detect-changes
  image: jbustos/filters-tool:v1.0.0
  script:
    - git diff --name-only $CI_MERGE_REQUEST_DIFF_BASE_SHA...$CI_COMMIT_SHA | filters-tool --config examples/filters.yaml
    # Equivalent alternative using --changed-files-file instead of stdin:
    # - git diff --name-only $CI_MERGE_REQUEST_DIFF_BASE_SHA...$CI_COMMIT_SHA > changed_files.txt
    # - filters-tool --config examples/filters.yaml --changed-files-file changed_files.txt
  artifacts:
    reports:
      dotenv: filters.env

backend-tests:
  stage: test
  needs: ["paths-check"]
  rules:
    - if: '$backend == "true"'
  script:
    - echo "running backend tests"
    - ./run-backend-tests.sh
```

For a fuller example showing multiple independent pipelines (backend,
frontend, docs, tests) all gated off one `paths-check` job, see
[`examples/gitlab-ci-multi-pipeline.yml`](examples/gitlab-ci-multi-pipeline.yml).
This is the scenario the tool is really built for: a docs-only change skips
backend/frontend/test jobs entirely instead of running the full suite.

### Publishing your own image

If you want to customize the tool or avoid depending on someone else's
image, build it and push it to whatever container registry you use (Docker
Hub, GitLab Container Registry, ECR, GCR, ...):

```bash
docker build -t <your-registry>/<your-image>:<tag> .
docker login <your-registry>
docker push <your-registry>/<your-image>:<tag>
```

Then point your `.gitlab-ci.yml` jobs' `image:` at your own tag instead. If
you're publishing to a private registry, you'll also need to configure
registry authentication for your GitLab CI job (via `CI_REGISTRY_*`
variables or a `docker login` step) — see GitLab's own [Container Registry
documentation](https://docs.gitlab.com/ee/user/packages/container_registry/)
or your registry provider's equivalent for that setup.

## Testing locally

For trying the tool out on your machine after your changes, first build a
local image:

```bash
docker build -t filters-tool .
```

Then run it against a diff:

```bash
git diff --name-only main... | docker run -i -v "$(pwd)":/repo -w /repo filters-tool --config filters.yaml
```

This mounts your current directory into the container at `/repo` and runs
the tool against it, writing `filters.env` back into your working directory.

### Debugging why a filter did or didn't match: `--explain`

If a filter isn't matching the way you expect, run the tool against a single
changed file (or a small handful) with `--explain`. It prints a full trace to
stderr showing, per filter, which pattern decided each file's outcome:

```bash
echo "app/src/test/FiltersTest.kt" | docker run -i -v "$(pwd)":/repo -w /repo filters-tool --config filters.yaml --explain
```

```
[kotlin_sources]
  app/src/test/FiltersTest.kt: included by "**/*.kt", then excluded by "!**/test/**"
  RESULT: false

[tests]
  app/src/test/FiltersTest.kt: included by "**/test/**/*.kt"
  RESULT: true (matched by app/src/test/FiltersTest.kt)

[documentation]
  (no changed file interacted with this filter's patterns)
  RESULT: false
```

This makes it possible to iterate on `filters.yaml` locally — checking one
file at a time against your patterns — without needing to run a full CI
pipeline to see the outcome.

## Worked example

Given this `filters.yaml`:

```yaml
filters:
  kotlin_sources:
    - "**/*.kt"
    - "!**/test/**"
  tests:
    - "**/test/**/*.kt"
  documentation:
    - "README.md"
    - "docs/**"
```

and changed files `App.kt`, `src/test/FiltersTest.kt`, `README.md`:

```bash
printf "App.kt\nsrc/test/FiltersTest.kt\nREADME.md\n" | \
  docker run -i -v "$(pwd)":/repo -w /repo filters-tool --config filters.yaml
```

produces `filters.env`:

```
kotlin_sources=true
tests=true
documentation=true
```

- `kotlin_sources` matches on `App.kt` (a Kotlin file outside `test/`).
- `tests` matches on `src/test/FiltersTest.kt`.
- `documentation` matches on `README.md`.

## Running the tests

```bash
pip install -r requirements.txt pytest
pytest
```
