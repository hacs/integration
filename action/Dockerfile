FROM ludeeus/container:hacs-action

RUN \
    cd /hacs \
    && git pull \
    # && tag=$(git describe --tags `git rev-list --tags --max-count=1`) \ # disabled for now (During tests)
    # && git checkout $tag -b $tag \  # disabled for now (During tests)
    && git clone https://github.com/hacs/default.git /default \
    && make init

COPY entrypoint.sh /entrypoint.sh
COPY action.py /hacs/action.py

ENTRYPOINT ["/entrypoint.sh"]