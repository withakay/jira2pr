# Makefile for jira2pr tool

# Variables
PYTHON := uv run python
SCRIPT_DIR := jira2pr
K8S_DIR := k8s
HELM_DIR := $(K8S_DIR)/helm/jira2pr-cronjob
CRONJOB_DIR := $(K8S_DIR)/cronjob

# Default target
.PHONY: help
help:
	@echo "Available targets:"
	@echo "  make install       - Install dependencies using uv"
	@echo "  make run TICKET=X  - Run jira2pr for a specific ticket"
	@echo "  make get-ticket TICKET=X - Get ticket body from JIRA"
	@echo "  make batch         - Run batch update for all open PRs"
	@echo "  make batch-dry     - Run batch update in dry-run mode"
	@echo "  make test          - Run tests"
	@echo ""
	@echo "Kubernetes deployment:"
	@echo "  make k8s-secrets   - Create Kubernetes secrets from .envrc"
	@echo "  make k8s-deploy    - Deploy to Kubernetes using kubectl"
	@echo "  make k8s-delete    - Delete Kubernetes deployment"
	@echo "  make k8s-logs      - View logs from the latest cronjob"
	@echo ""
	@echo "Helm deployment:"
	@echo "  make helm-install  - Install using Helm chart"
	@echo "  make helm-upgrade  - Upgrade Helm deployment"
	@echo "  make helm-delete   - Delete Helm deployment"
	@echo ""
	@echo "Development:"
	@echo "  make lint          - Run code linting"
	@echo "  make format        - Format code"
	@echo "  make clean         - Clean generated files"

# Install dependencies
.PHONY: install
install:
	cd $(SCRIPT_DIR) && uv sync

# Run for a specific ticket
.PHONY: run
run:
ifndef TICKET
	$(error TICKET is not set. Usage: make run TICKET=PROJ-123)
endif
	cd $(SCRIPT_DIR) && $(PYTHON) jira2pr.py $(TICKET)

# Run with output to file
.PHONY: run-output
run-output:
ifndef TICKET
	$(error TICKET is not set. Usage: make run-output TICKET=PROJ-123)
endif
	cd $(SCRIPT_DIR) && $(PYTHON) jira2pr.py $(TICKET) --output pr-description.md
	@echo "PR description saved to $(SCRIPT_DIR)/pr-description.md"

# Get ticket details
.PHONY: get-ticket
get-ticket:
ifndef TICKET
	$(error TICKET is not set. Usage: make get-ticket TICKET=PROJ-123)
endif
	cd $(SCRIPT_DIR) && $(PYTHON) jira2pr.py $(TICKET) --output -

# Find PR for a ticket
.PHONY: find-pr
find-pr:
ifndef TICKET
	$(error TICKET is not set. Usage: make find-pr TICKET=PROJ-123)
endif
	cd $(SCRIPT_DIR) && $(PYTHON) jira2pr.py $(TICKET) --find-pr

# Update PR for a ticket
.PHONY: update-pr
update-pr:
ifndef TICKET
	$(error TICKET is not set. Usage: make update-pr TICKET=PROJ-123 [PR=42])
endif
	cd $(SCRIPT_DIR) && $(PYTHON) jira2pr.py $(TICKET) --update-pr $(if $(PR),$(PR))

# Run batch update
.PHONY: batch
batch:
	cd $(SCRIPT_DIR) && $(PYTHON) jira2pr.py --batch-update $(if $(PREFIX),--ticket-prefix $(PREFIX))

# Run batch update in dry-run mode
.PHONY: batch-dry
batch-dry:
	cd $(SCRIPT_DIR) && $(PYTHON) jira2pr.py --batch-update --dry-run $(if $(PREFIX),--ticket-prefix $(PREFIX))

# Run tests
.PHONY: test
test:
	cd $(SCRIPT_DIR) && $(PYTHON) -m pytest test_ticket_extraction.py -v

# Kubernetes deployment targets
.PHONY: k8s-secrets
k8s-secrets:
	@echo "Creating Kubernetes secrets from .envrc..."
	cd $(CRONJOB_DIR) && ./create-jira2pr-secrets.sh

.PHONY: k8s-configmap
k8s-configmap:
	@echo "Creating Kubernetes configmap..."
	cd $(CRONJOB_DIR) && ./create-jira2pr-configmap.sh

.PHONY: k8s-deploy
k8s-deploy: k8s-secrets k8s-configmap
	@echo "Deploying to Kubernetes..."
	cd $(CRONJOB_DIR) && ./update-jira2pr-cronjob.sh
	kubectl apply -f $(CRONJOB_DIR)/jira2pr-secrets.yaml
	kubectl apply -f $(CRONJOB_DIR)/jira2pr-configmap.yaml
	kubectl apply -f $(CRONJOB_DIR)/jira2pr-cronjob.yaml

.PHONY: k8s-delete
k8s-delete:
	@echo "Deleting Kubernetes deployment..."
	kubectl delete -f $(CRONJOB_DIR)/jira2pr-cronjob.yaml --ignore-not-found
	kubectl delete -f $(CRONJOB_DIR)/jira2pr-configmap.yaml --ignore-not-found
	kubectl delete -f $(CRONJOB_DIR)/jira2pr-secrets.yaml --ignore-not-found

.PHONY: k8s-logs
k8s-logs:
	@echo "Fetching logs from the latest job..."
	@pod=$$(kubectl get pods -l job-name -o jsonpath='{.items[-1].metadata.name}' 2>/dev/null); \
	if [ -z "$$pod" ]; then \
		echo "No job pods found. The cronjob may not have run yet."; \
	else \
		kubectl logs $$pod; \
	fi

.PHONY: k8s-jobs
k8s-jobs:
	@echo "Listing recent jobs..."
	kubectl get jobs -l app=jira2pr --sort-by=.metadata.creationTimestamp

# Helm deployment targets
.PHONY: helm-install
helm-install:
ifndef SECRETS_FILE
	$(error SECRETS_FILE is not set. Usage: make helm-install SECRETS_FILE=my-secrets.yaml)
endif
	@echo "Installing Helm chart..."
	helm install jira2pr-cronjob $(HELM_DIR) -f $(HELM_DIR)/values.yaml -f $(SECRETS_FILE)

.PHONY: helm-upgrade
helm-upgrade:
ifndef SECRETS_FILE
	$(error SECRETS_FILE is not set. Usage: make helm-upgrade SECRETS_FILE=my-secrets.yaml)
endif
	@echo "Upgrading Helm deployment..."
	helm upgrade jira2pr-cronjob $(HELM_DIR) -f $(HELM_DIR)/values.yaml -f $(SECRETS_FILE)

.PHONY: helm-delete
helm-delete:
	@echo "Deleting Helm deployment..."
	helm uninstall jira2pr-cronjob

.PHONY: helm-status
helm-status:
	@echo "Helm deployment status..."
	helm status jira2pr-cronjob

# Development targets
.PHONY: lint
lint:
	cd $(SCRIPT_DIR) && uv run ruff check jira2pr.py test_ticket_extraction.py

.PHONY: format
format:
	cd $(SCRIPT_DIR) && uv run ruff format jira2pr.py test_ticket_extraction.py

.PHONY: clean
clean:
	@echo "Cleaning generated files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -f $(SCRIPT_DIR)/pr-description.md
	rm -f $(CRONJOB_DIR)/jira2pr-secrets.yaml
	rm -f $(CRONJOB_DIR)/jira2pr-configmap.yaml
	rm -f $(CRONJOB_DIR)/values-snippet.yaml

# GitHub Actions targets
.PHONY: gh-run
gh-run:
	@echo "Triggering GitHub Action workflow..."
	gh workflow run jira2pr.yml

.PHONY: gh-run-dry
gh-run-dry:
	@echo "Triggering GitHub Action workflow in dry-run mode..."
	gh workflow run jira2pr.yml -f dry_run=true

.PHONY: gh-status
gh-status:
	@echo "Checking GitHub Action workflow status..."
	gh run list --workflow=jira2pr.yml --limit=5

# Utility targets
.PHONY: check-env
check-env:
	@echo "Checking environment variables..."
	@echo "JIRA_URL: $${JIRA_URL:?not set}"
	@echo "JIRA_USERNAME: $${JIRA_USERNAME:?not set}"
	@echo "JIRA_API_TOKEN: $${JIRA_API_TOKEN:?[hidden]}"
	@echo "GITHUB_TOKEN: $${GITHUB_TOKEN:?[hidden]}"
	@echo "GITHUB_OWNER: $${GITHUB_OWNER:?not set}"
	@echo "GITHUB_REPO: $${GITHUB_REPO:?not set}"
	@echo "All required environment variables are set!"

.PHONY: version
version:
	@cd $(SCRIPT_DIR) && $(PYTHON) jira2pr.py --version 2>/dev/null || echo "Version not implemented"