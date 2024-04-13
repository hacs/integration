FROM python:3.12-alpine

WORKDIR /hacs

COPY . /hacs

ENV PIP_EXTRA_INDEX_URL="https://wheels.home-assistant.io/musllinux-index/"

RUN \
    apk add --no-cache --virtual .build-deps \
        bash \
    \
    && bash /hacs/scripts/install/pip_packages \
        -r requirements_action.txt \
    \
    && bash /hacs/scripts/install/frontend \
    \
    && apk del --no-cache .build-deps > /dev/null 2>&1 \
    \
    && rm -rf /var/cache/apk/* \
    \
    && find /usr/local \( -type d -a -name test -o -name tests -o -name '__pycache__' \) -o \( -type f -a -name '*.pyc' -o -name '*.pyo' \) -exec rm -rf '{}' \; \
    \
    && cp /hacs/action/action.py /hacs/action.py

ENTRYPOINT ["python3", "/hacs/action.py"]
