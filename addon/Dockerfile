ARG BUILD_FROM
FROM $BUILD_FROM

# Alpine 3.22 ships Python 3.12: no compression.zstd, so zstd is simply not advertised (see cup_api.py).
RUN apk add --no-cache python3 py3-brotli

WORKDIR /app
# Explicit copies only: .env and log*.txt (patient data) must never enter the image.
COPY main.py ./
COPY cup_checker ./cup_checker

COPY addon/run.sh /
RUN chmod a+x /run.sh

CMD ["/run.sh"]
