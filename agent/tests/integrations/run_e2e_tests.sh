#!/bin/bash

# E2E Integration Tests Runner
# This script sets up and runs the end-to-end integration tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.e2e.yml"
LOCALSTACK_URL="http://localhost:4566"

# Functions
print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  E2E Integration Tests${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_step() {
    echo -e "${YELLOW}🔄 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
    exit 1
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

check_requirements() {
    print_step "Checking requirements..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed or not in PATH"
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed or not in PATH"
    fi
    
    # Check Python
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        print_error "Python is not installed or not in PATH"
    fi
    
    # Check .env file
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        print_warning ".env file not found. Make sure you have API keys configured."
        echo "Create a .env file with:"
        echo "OPENAI_API_KEY=your_key"
        echo "ELEVENLABS_API_KEY=your_key"
        echo "PEXELS_API_KEY=your_key"
    fi
    
    print_success "Requirements check passed"
}

start_localstack() {
    print_step "Starting LocalStack..."
    
    # Change to the directory containing docker-compose.e2e.yml
    cd "$SCRIPT_DIR"
    
    # Ensure clean start - remove any existing containers/volumes
    print_step "Cleaning up any existing LocalStack instances..."
    docker rm -f localstack-e2e-test 2>/dev/null || true
    docker-compose -f docker-compose.e2e.yml down --volumes --remove-orphans 2>/dev/null || true
    
    # Start LocalStack fresh
    docker-compose -f docker-compose.e2e.yml up -d
    
    print_step "Waiting for LocalStack to be ready..."
    
    # Wait for LocalStack to be healthy
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s "$LOCALSTACK_URL/_localstack/health" > /dev/null 2>&1; then
            print_success "LocalStack is ready"
            return 0
        fi
        
        echo -n "."
        sleep 2
        ((attempt++))
    done
    
    print_error "LocalStack did not start within expected time"
}

stop_localstack() {
    print_step "Stopping LocalStack..."
    cd "$SCRIPT_DIR"
    
    # Force complete cleanup with volume removal
    docker-compose -f docker-compose.e2e.yml down --volumes --remove-orphans
    
    # Remove any lingering containers
    docker rm -f localstack-e2e-test 2>/dev/null || true
    
    # Clean up any persistent data
    docker volume prune -f 2>/dev/null || true
    
    print_success "LocalStack stopped"
}

run_tests() {
    print_step "Running E2E tests..."
    
    cd "$PROJECT_ROOT"
    
    # Run tests using the Python runner
    if python3 tests/integrations/run_e2e_tests.py --skip-health-check "$@"; then
        print_success "All tests passed!"
        return 0
    else
        print_error "Tests failed!"
        return 1
    fi
}

cleanup() {
    print_step "Cleaning up..."
    stop_localstack
}

show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --help, -h          Show this help message"
    echo "  --no-cleanup        Don't stop LocalStack after tests"
    echo "  --skip-start        Skip LocalStack startup (assume it's already running)"
    echo "  --test-path PATH    Run specific test path"
    echo "  --verbose, -v       Verbose output"
    echo ""
    echo "Examples:"
    echo "  $0                              # Run all tests"
    echo "  $0 --verbose                    # Run with verbose output"
    echo "  $0 --test-path TestSQSValidation  # Run specific test class"
    echo "  $0 --no-cleanup                # Keep LocalStack running after tests"
}

# Parse command line arguments
CLEANUP=true
SKIP_START=false
TEST_PATH=""
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_help
            exit 0
            ;;
        --no-cleanup)
            CLEANUP=false
            shift
            ;;
        --skip-start)
            SKIP_START=true
            shift
            ;;
        --test-path)
            TEST_PATH="$2"
            shift 2
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Main execution
main() {
    print_header
    
    # Set up cleanup trap
    if [ "$CLEANUP" = true ]; then
        trap cleanup EXIT
    fi
    
    # Check requirements
    check_requirements
    
    # Start LocalStack if needed
    if [ "$SKIP_START" = false ]; then
        start_localstack
    else
        print_step "Skipping LocalStack startup (assuming it's already running)"
    fi
    
    # Build test arguments
    TEST_ARGS=()
    if [ -n "$TEST_PATH" ]; then
        TEST_ARGS+=("--test-path" "$TEST_PATH")
    fi
    if [ "$VERBOSE" = true ]; then
        TEST_ARGS+=("--pytest-args" "-v" "-s")
    fi
    
    # Run tests
    run_tests "${TEST_ARGS[@]}"
}

# Run main function
main "$@" 