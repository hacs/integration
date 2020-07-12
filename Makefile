.DEFAULT_GOAL := help
HAS_APK := $(shell command -v apk 2>/dev/null)
HAS_APT := $(shell command -v apt 2>/dev/null)
WHEELS := https://wheels.home-assistant.io/alpine-3.12/amd64/

help: ## Shows help message.
	@printf "\033[1m%s\033[36m %s\033[32m %s\033[0m \n\n" "Development environment for" "HACS" "Integration";
	@awk 'BEGIN {FS = ":.*##";} /^[a-zA-Z_-]+:.*?##/ { printf " \033[36m make %-25s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST);
	@echo

init: requirements homeassistant-install install-custom_components

requirements:
ifdef HAS_APK
	apk add libxml2-dev libxslt-dev
endif
ifdef HAS_APT
	sudo apt update && sudo apt install libxml2-dev libxslt-dev
endif
	python3 -m pip --disable-pip-version-check install -U setuptools wheel --find-links $(WHEELS)
	python3 -m pip --disable-pip-version-check install --ignore-installed -r requirements.txt --find-links $(WHEELS)

start: ## Start the HA with the integration
	@bash manage/integration_start;

test: ## Run pytest
	python3 -m pytest --cov=./ --cov-report=xml;

lint: ## Run linters
	pre-commit install-hooks --config .github/pre-commit-config.yaml;
	pre-commit run --hook-stage manual --all-files --config .github/pre-commit-config.yaml;
	bellybutton lint

coverage:
	coverage report --skip-covered

update: ## Pull master from hacs/integration
	git pull upstream master;

install-custom_components:
	python3 setup.py develop

homeassistant-install: ## Install the latest dev version of Home Assistant
	python3 -m pip --disable-pip-version-check install -U setuptools wheel --find-links $(WHEELS);
	python3 -m pip install -U --pre homeassistant;
	#python3 -m pip --disable-pip-version-check \
	#	install --upgrade git+git://github.com/home-assistant/home-assistant.git@dev;

homeassistant-update: homeassistant-install ## Alias for 'homeassistant-install'