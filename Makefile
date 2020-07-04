.DEFAULT_GOAL := help

WHEELS := https://wheels.home-assistant.io/alpine-3.11/amd64/

help: ## Shows help message.
	@printf "\033[1m%s\033[36m %s\033[32m %s\033[0m \n\n" "Development environment for" "HACS" "Integration";
	@awk 'BEGIN {FS = ":.*##";} /^[a-zA-Z_-]+:.*?##/ { printf " \033[36m make %-25s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST);
	@echo

init: homeassistant-install
	python -m pip --disable-pip-version-check install -r requirements.txt --find-links $(WHEELS)

start: ## Start the HA with the integration
	@bash manage/integration_start;

test: ## Run pytest
	python -m pytest;

lint: ## Run linters
	pre-commit install-hooks --config .github/pre-commit-config.yaml;
	pre-commit run --hook-stage manual --all-files --config .github/pre-commit-config.yaml;

update: ## Pull master from hacs/integration
	git pull upstream master;

homeassistant-install: ## Install the latest dev version of Home Assistant
	python -m pip --disable-pip-version-check install -U setuptools wheel --find-links $(WHEELS);
	python -m pip install -U --pre homeassistant;
	#python -m pip --disable-pip-version-check \
	#	install --upgrade git+git://github.com/home-assistant/home-assistant.git@dev;

homeassistant-update: homeassistant-install ## Alias for 'homeassistant-install'