FROM python:3.14-alpine@sha256:f6a589d43c42b9e7f7dc67a12d37132491f362859a5d750607710cc56da3bc72
WORKDIR /hacs

COPY . /hacs

ENV \
    UV_SYSTEM_PYTHON=true \
    UV_EXTRA_INDEX_URL="https://wheels.home-assistant.io/musllinux-index/"

RUN \
    apk add --no-cache --virtual .build-deps \
        bash \
    \
    && bash /hacs/scripts/install/pip_packages \
        uv==0.9.6 \
    \
    && bash /hacs/scripts/install/uv_packages \
        -r requirements_action.txt \
    \
    && apk del --no-cache .build-deps > /dev/null 2>&1 \
    \
    && rm -rf /var/cache/apk/* \
    \
    && find /usr/local \( -type d -a -name test -o -name tests -o -name '__pycache__' \) -o \( -type f -a -name '*.pyc' -o -name '*.pyo' \) -exec rm -rf '{}' \; \
    \
    && mv /hacs/action/action.py /hacs/action.py \
    \
    && rm -rf /hacs/scripts /hacs/action  \
    \
    && rm /hacs/requirements_action.txt  /hacs/constraints.txt

ENTRYPOINT ["python3", "/hacs/action.py"]
