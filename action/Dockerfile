FROM ghcr.io/ludeeus/debian/python:3.9

WORKDIR /hacs

RUN git clone --quiet --depth 1 https://github.com/hacs/integration.git /hacs
RUN git clone --quiet --depth 1 https://github.com/hacs/default.git /default

RUN cd /hacs && make init

COPY ./action.py /hacs/action/action.py

ENTRYPOINT ["python3", "/hacs/action/action.py"]