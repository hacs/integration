FROM ghcr.io/ludeeus/devcontainer/python:3.9

WORKDIR /hacs

RUN git clone --quiet --depth 1 https://github.com/hacs/integration.git /hacs
RUN git clone --quiet --depth 1 https://github.com/hacs/default.git /default

RUN cd /hacs && make requirements && make homeassistant-install

COPY ./action.py /hacs/action.py

ENTRYPOINT ["python3", "/hacs/action.py"]