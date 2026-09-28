# Minimal, disposable Linux target for PurpleLab simulations.
#
# This image contains only a small fixed-behavior runner script -- no SSH,
# no offensive tooling, no unnecessary services. It only ever collects
# known, safe telemetry for known PurpleLab technique IDs.

FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /opt/purplelab

COPY runner.py .

USER nobody

ENTRYPOINT ["python3", "-B", "runner.py"]
