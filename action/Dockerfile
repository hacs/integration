FROM python:3.12-alpine

WORKDIR /hacs

COPY . /hacs

ENV PIP_EXTRA_INDEX_URL="https://wheels.home-assistant.io/musllinux-index/"

RUN \
    ls /hacs \
    && apk add --no-cache \
        libffi-dev \
    \
    &&  apk add --no-cache --virtual .build-deps \
        bash \
        gcc \
        git \
        musl-dev \
    \
    && bash /hacs/scripts/install/pip_packages setuptools wheel \
    \
    && bash /hacs/scripts/install/pip_packages homeassistant aiogithubapi async-timeout \
    \
    && bash /hacs/scripts/install/frontend \
    \
    && apk del --no-cache .build-deps > /dev/null 2>&1 \
    \
    && rm -rf /var/cache/apk/* \
    \
    && find /usr/local \( -type d -a -name test -o -name tests -o -name '__pycache__' \) -o \( -type f -a -name '*.pyc' -o -name '*.pyo' \) -exec rm -rf '{}' \;

ENTRYPOINT ["python3", "/hacs/action.py"]
