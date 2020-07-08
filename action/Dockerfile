FROM ludeeus/container:hacs-action

RUN git clone https://github.com/hacs/default.git /default

COPY action.py /hacs/action.py

ENTRYPOINT ["python3", "/hacs/action.py"]