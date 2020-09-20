FROM ludeeus/container:hacs-action

RUN git clone https://github.com/hacs/default.git /default
RUN rm -rf /hacs
RUN git clone --single-branch --branch oauth https://github.com/hacs/integration.git /hacs

COPY action.py /hacs/action.py

ENTRYPOINT ["python3", "/hacs/action.py"]