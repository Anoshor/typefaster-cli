# TYPEFASTER client image (optional).
# The client is a terminal app; this image is handy for trying it without a
# local Python install:  docker run -it --rm typefaster-client
# Build context must be the repository ROOT:
#   docker build -f client/Dockerfile -t typefaster-client .
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TERM=xterm-256color

WORKDIR /app
COPY pyproject.toml README.md /app/
COPY client /app/client
RUN pip install /app

RUN useradd --create-home --uid 10001 player
USER player

ENTRYPOINT ["typefaster"]
