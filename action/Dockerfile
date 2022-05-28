FROM ghcr.io/ludeeus/alpine/python:3.10

WORKDIR /hacs

RUN \
    apk add --no-cache \
        libffi-dev \
    \
    &&  apk add --no-cache --virtual .build-deps \
        gcc \
        musl-dev \
    \
    && git clone --quiet --depth 1 https://github.com/hacs/integration.git /hacs \
    \
    && python3 -m pip --disable-pip-version-check install setuptools wheel \
    \
    && python3 -m pip --disable-pip-version-check install homeassistant aiogithubapi \
    \
    && bash /hacs/manage/install_frontend \
    \
    && apk del --no-cache .build-deps > /dev/null 2>&1 \
    \
    && rm -rf /var/cache/apk/* \
    \
    && find /usr/local \( -type d -a -name test -o -name tests -o -name '__pycache__' \) -o \( -type f -a -name '*.pyc' -o -name '*.pyo' \) -exec rm -rf '{}' \;

COPY ./action.py /hacs/action.py

ENTRYPOINT ["python3", "/hacs/action.py"]