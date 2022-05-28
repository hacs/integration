FROM ghcr.io/ludeeus/alpine/python:3.10

WORKDIR /hacs

RUN \
    git clone --quiet --depth 1 https://github.com/hacs/integration.git /hacs \
    && python3 -m pip install setuptools > /dev/null \
    && python3 -m pip install homeassistant aiogithubapi > /dev/null \
    && bash /hacs/manage/install_frontend > /dev/null \
    && rm -rf \
        /hacs/.git \
        /hacs/.github \
        /hacs/manage \
        /hacs/test \
        *.*

COPY ./action.py /hacs/action.py

ENTRYPOINT ["python3", "/hacs/action.py"]