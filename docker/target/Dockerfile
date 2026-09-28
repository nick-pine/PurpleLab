# Minimal, disposable Linux target for PurpleLab simulations.
#
# This image contains only the shared stdlib-only collector module and a
# small fixed-behavior runner script -- no SSH, no offensive tooling, no
# unnecessary services. It only ever collects known, safe telemetry for
# known PurpleLab technique IDs.
#
# Build context is the repository root (see purplelab/lab.py), so the
# collector module can be copied from `simulations/` without duplicating it.

FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /opt/purplelab

COPY simulations/_stdlib_collectors.py .
COPY docker/target/runner.py .

USER nobody

ENTRYPOINT ["python3", "-B", "runner.py"]
