FROM python:3.7

ENV DEVCONTAINER True

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade colorlog black pylint python-language-server
RUN python -m pip install --upgrade git+git://github.com/home-assistant/home-assistant.git@dev
RUN cd && mkdir -p /config/custom_components


WORKDIR /workspace

# Set the default shell to bash instead of sh
ENV SHELL /bin/bash
