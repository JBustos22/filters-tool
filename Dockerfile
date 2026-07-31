# ---- Builder stage ----
# Installs the package (and its pure-Python deps) into a venv. No compiler
# toolchain is needed since pathspec and PyYAML have no C-extension deps
# for this use case. Using a venv (rather than `pip install --target`)
# ensures the `filters-tool` console-script entry point actually gets
# generated, not just the importable package.
FROM python:3.12-slim AS builder

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build
COPY pyproject.toml .
COPY src ./src
RUN pip install --no-cache-dir .

# ---- Final stage ----
# Only the venv (deps + package + the filters-tool script) is copied in --
# no pip, no build cache, no compiler toolchain left behind. GitLab CI's
# docker executor overrides ENTRYPOINT and runs `script:` steps from the
# cloned-repo directory, so having `filters-tool` on PATH (rather than
# relying on cwd-relative imports) is what makes it resolve regardless of
# the caller's working directory.
FROM python:3.12-slim

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

ENTRYPOINT ["filters-tool"]
