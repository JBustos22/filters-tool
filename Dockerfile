# ---- Builder stage ----
# Installs pure-Python dependencies into an isolated directory. No compiler
# toolchain is needed since pathspec and PyYAML have no C-extension deps
# for this use case.
FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --target=/build/deps -r requirements.txt

# ---- Final stage ----
# Only the installed dependencies and application source are copied in --
# no pip, no build cache, no compiler toolchain left behind.
FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /build/deps /usr/local/lib/python3.12/site-packages
COPY filters_tool ./filters_tool

# GitLab CI's docker executor overrides ENTRYPOINT and runs `script:` steps
# from the cloned-repo directory, not this image's WORKDIR -- so PYTHONPATH
# is set here to make `python -m filters_tool` resolve regardless of the
# caller's working directory or entrypoint behavior.
ENV PYTHONPATH=/app

ENTRYPOINT ["python", "-m", "filters_tool"]
