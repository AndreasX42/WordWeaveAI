.PHONY: test test-unit test-integration test-integration-keep-db test-coverage clean build start-dynamodb stop-dynamodb

# Run all tests
test:
	go test ./...

# Run unit tests only
test-unit:
	go test ./tests/unit -v

# Run integration tests with DynamoDB Local
test-integration:
	@echo "Starting DynamoDB Local..."
	docker-compose -f docker-compose.test.yml up -d
	@echo "Waiting for DynamoDB Local to be ready..."
	sleep 5
	@echo "Running integration tests..."
	go test ./tests/integration -v
	@echo "Stopping DynamoDB Local..."
	docker-compose -f docker-compose.test.yml down

# Run integration tests (keeping DynamoDB Local running)
test-integration-keep-db:
	@echo "Running integration tests (keeping DynamoDB Local running)..."
	go test ./tests/integration -v

# Run tests with coverage across all packages
test-coverage:
	go test -coverprofile=coverage.out ./tests/unit
	go tool cover -html=coverage.out -o coverage.html
	@echo "Coverage report generated: coverage.html"

# Run tests with verbose coverage output
test-coverage-func:
	go test -coverprofile=coverage.out ./tests/unit
	go tool cover -func=coverage.out

# Clean build artifacts and coverage files
clean:
	rm -f coverage.out coverage.html
	go clean

# Build the application
build:
	go build -o bin/wordweave .

# Run the application
run:
	go run .

# Install dependencies
deps:
	go mod tidy
	go mod download

# Format code
fmt:
	go fmt ./...

# Run linter (requires golangci-lint)
lint:
	golangci-lint run

# Docker commands for DynamoDB Local
start-dynamodb:
	@echo "Starting DynamoDB Local..."
	docker-compose -f docker-compose.test.yml up -d

stop-dynamodb:
	@echo "Stopping DynamoDB Local..."
	docker-compose -f docker-compose.test.yml down

# Show help
help:
	@echo "Available commands:"
	@echo "  make test            - Run all tests"
	@echo "  make test-unit       - Run unit tests"
	@echo "  make test-integration - Run integration tests"
	@echo "  make test-coverage   - Run tests with HTML coverage report"
	@echo "  make test-coverage-func - Run tests with function coverage"
	@echo "  make build           - Build the application"
	@echo "  make run             - Run the application"
	@echo "  make clean           - Clean build artifacts"
	@echo "  make deps            - Install dependencies"
	@echo "  make fmt             - Format code"
	@echo "  make lint            - Run linter"
	@echo "  make help            - Show this help" 