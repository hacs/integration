FROM ghcr.io/ludeeus/devcontainer/python:3.9

WORKDIR /hacs

RUN git clone --quiet --depth 1 https://github.com/hacs/integration.git /hacs

RUN python3 -m pip install homeassistant aiogithubapi > /dev/null
RUN bash /hacs/manage/install_frontend > /dev/null

COPY ./action.py /hacs/action.py

ENTRYPOINT ["python3", "/hacs/action.py"]