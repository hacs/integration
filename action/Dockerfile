# syntax=docker/dockerfile:1
FROM python:3.14-alpine
WORKDIR /hacs

ENV \
    UV_SYSTEM_PYTHON=true \
    UV_EXTRA_INDEX_URL="https://wheels.home-assistant.io/musllinux-index/"

# Install dependencies in a layer keyed only on the dependency manifests and the
# install scripts (the frontend version is pinned inside scripts/install/frontend).
# Editing custom_components/hacs no longer invalidates this expensive layer, and the
# uv/pip cache mounts persist wheel and frontend downloads across builds.
COPY constraints.txt requirements_action.txt ./
COPY scripts/install ./scripts/install

RUN \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=type=cache,target=/root/.cache/pip \
    apk add --no-cache --virtual .build-deps \
        bash \
    \
    && bash /hacs/scripts/install/pip_packages \
        uv==0.9.6 \
    \
    && bash /hacs/scripts/install/uv_packages \
        -r requirements_action.txt \
    \
    && bash /hacs/scripts/install/frontend \
    \
    && apk del --no-cache .build-deps > /dev/null 2>&1 \
    \
    && rm -rf /var/cache/apk/* \
    \
    && find /usr/local \( -type d -a -name test -o -name tests -o -name '__pycache__' \) -o \( -type f -a -name '*.pyc' -o -name '*.pyo' \) -exec rm -rf '{}' \;

# Application source. Kept below the dependency layer so source edits only bust the
# cheap layers here.
COPY . /hacs

RUN \
    mv /hacs/action/action.py /hacs/action.py \
    \
    && rm -rf /hacs/scripts /hacs/action  \
    \
    && rm /hacs/requirements_action.txt  /hacs/constraints.txt

ENTRYPOINT ["python3", "/hacs/action.py"]
