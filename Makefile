.DEFAULT_GOAL := help

help: ## Shows help message.
	@printf "\033[1m%s\033[36m %s\033[32m %s\033[0m \n\n" "Development environment for" "HACS" "Integration";
	@awk 'BEGIN {FS = ":.*##";} /^[a-zA-Z_-]+:.*?##/ { printf " \033[36m make %-25s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST);
	@echo

init:
	@ python -m pip --disable-pip-version-check install -U setuptools wheel
	@ python -m pip --disable-pip-version-check install -r requirements.txt

start: ## Start the HA with the integration
	@bash manage/integration_start;

test: ## Run pytest
	@ python -m pytest;

update: ## Pull master from hacs/integration
	@ git pull upstream master;

homeassistant-install: ## Install the latest dev version of Home Assistant
	@ python -m pip --disable-pip-version-check install -U setuptools wheel
	@ python -m pip --disable-pip-version-check \
		install --upgrade git+git://github.com/home-assistant/home-assistant.git@dev;

homeassistant-update: homeassistant-install ## Alias for 'homeassistant-install'