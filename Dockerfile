FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc-aarch64-linux-gnu \
        libc6-dev-arm64-cross \
        qemu-user-static \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/simproxy
COPY . .
RUN pip install --no-cache-dir .

WORKDIR /work
ENTRYPOINT ["simproxy"]
CMD ["--version"]
