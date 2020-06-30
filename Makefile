.DEFAULT_GOAL := help

help: ## Shows help message.
	@printf "\033[1m%s\033[36m %s\033[32m %s\033[0m \n\n" "Development environment for" "HACS" "Integration";
	@awk 'BEGIN {FS = ":.*##";} /^[a-zA-Z_-]+:.*?##/ { printf " \033[36m make %-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST);
	@echo

init:
	@ python -m pip --disable-pip-version-check install setuptools wheel
	@ python -m pip --disable-pip-version-check install -r requirements.txt

start: ## Start the HA with the integration
	@bash script/integration_start;

test: ## Run pytest
	@ python -m pytest;

update: ## Pull master from hacs/integration
	@ git pull upstream master;
