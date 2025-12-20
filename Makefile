.PHONY: help

help: ## Display this help screen
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

docker-build: ## Build Docker images
	@echo "Building Docker images..."
	docker compose build

docker-system-prune: ## Prune all unused Docker objects
	@echo "Pruning Docker..."
	docker system prune -a --volumes --force

watch: ## Watch for changes and rebuild
	@echo "Watching for changes..."
	docker compose watch

logs: ## Tail logs for all containers
	docker compose logs -f

down: ## Stop and remove containers, networks, volumes, and images
	docker compose down

install-whisper-system-deps: ## Install system dependencies for Whisper
	sudo apt install nvidia-cuda-toolkit
	sudo apt install nvidia-cudnn
	sudo apt install nvidia-cublas
