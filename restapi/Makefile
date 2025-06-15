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
	go build -o bin/restapi .

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

# CI/CD specific targets
.PHONY: ci-test ci-test-unit ci-test-integration ci-test-all ci-prepare

# CI preparation - install deps, format, lint
ci-prepare:
	@echo "Preparing CI environment..."
	go mod tidy
	go mod download
	go fmt ./...
	@echo "CI environment ready"

# CI unit tests with detailed output and coverage
ci-test-unit:
	@echo "Running unit tests for CI..."
	go test ./tests/unit -v -race -coverprofile=unit-coverage.out
	go tool cover -func=unit-coverage.out

# CI integration tests with timeout and detailed logging
ci-test-integration:
	@echo "Starting DynamoDB Local for CI..."
	docker-compose -f docker-compose.test.yml up -d
	@echo "Waiting for DynamoDB Local to be ready..."
	sleep 5
	@echo "Running integration tests for CI..."
	go test ./tests/integration -v -race -timeout=2m -coverprofile=integration-coverage.out || (docker-compose -f docker-compose.test.yml down && exit 1)
	@echo "Stopping DynamoDB Local..."
	docker-compose -f docker-compose.test.yml down
	@echo "Integration tests completed"

# CI combined coverage report
ci-test-coverage:
	@echo "Generating combined coverage report..."
	@echo "Using existing coverage files from previous test runs..."
	# Check if coverage files exist
	@if [ ! -f unit-coverage.out ]; then echo "Warning: unit-coverage.out not found"; fi
	@if [ ! -f integration-coverage.out ]; then echo "Warning: integration-coverage.out not found"; fi
	# Generate HTML reports from existing coverage files
	@if [ -f unit-coverage.out ]; then go tool cover -html=unit-coverage.out -o unit-coverage.html; fi
	@if [ -f integration-coverage.out ]; then go tool cover -html=integration-coverage.out -o integration-coverage.html; fi
	# Merge coverage files if you have gocovmerge installed
	# gocovmerge unit-coverage.out integration-coverage.out > combined-coverage.out
	# go tool cover -html=combined-coverage.out -o combined-coverage.html
	@echo "Coverage reports generated"

# Run all CI tests in sequence
ci-test-all: ci-prepare ci-test-unit ci-test-integration # ci-test-coverage
	@echo "All CI tests completed successfully"

# Cleanup CI artifacts
ci-clean: clean
	rm -f unit-coverage.out integration-coverage.out combined-coverage.out
	rm -f unit-coverage.html integration-coverage.html combined-coverage.html 