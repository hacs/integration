FROM ludeeus/container:hacs-action

RUN git clone https://github.com/hacs/default.git /default

COPY entrypoint.sh /entrypoint.sh
COPY action.py /hacs/action.py

ENTRYPOINT ["/entrypoint.sh"]