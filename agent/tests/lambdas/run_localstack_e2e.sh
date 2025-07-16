#!/bin/bash

# LocalStack End-to-End Testing Script
# This script sets up LocalStack and runs comprehensive e2e tests

set -e

echo "🚀 LocalStack End-to-End Testing Setup"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose is not installed. Please install it and try again."
    exit 1
fi

# Step 1: Start LocalStack
print_status "Starting LocalStack..."
docker-compose -f local-e2e-test-resources.yml up -d

# Wait for LocalStack to be ready
print_status "Waiting for LocalStack to be ready..."
sleep 10

# Check if LocalStack is ready
max_attempts=30
attempt=0
while [ $attempt -lt $max_attempts ]; do
    if curl -s http://localhost:4566/_localstack/health > /dev/null 2>&1; then
        print_success "LocalStack is ready!"
        break
    fi
    
    ((attempt++))
    print_status "Waiting for LocalStack... (attempt $attempt/$max_attempts)"
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    print_error "LocalStack failed to start within expected time"
    exit 1
fi

# Step 2: Set up AWS resources
print_status "Setting up AWS resources in LocalStack..."
python local_aws_setup.py

if [ $? -ne 0 ]; then
    print_error "Failed to set up AWS resources"
    exit 1
fi

# Step 3: Run end-to-end tests
print_status "Running end-to-end tests..."
python test_localstack_simple.py

if [ $? -eq 0 ]; then
    print_success "All end-to-end tests passed!"
    echo ""
    echo "🎉 Your application is ready for AWS deployment!"
    echo ""
    echo "LocalStack Resources:"
    echo "  🔌 WebSocket API: Available at LocalStack endpoint"
    echo "  📊 DynamoDB: Tables created and populated with test data"
    echo "  💾 S3: Bucket created for media storage"
    echo "  📬 SQS: Queue created for async processing"
    echo "  ⚡ Lambda: Functions created for WebSocket handling"
    echo ""
    echo "To view LocalStack resources:"
    echo "  curl http://localhost:4566/_localstack/health"
    echo "  aws --endpoint-url=http://localhost:4566 dynamodb list-tables"
    echo "  aws --endpoint-url=http://localhost:4566 s3 ls"
    echo ""
else
    print_error "Some tests failed. Please check the output above."
    exit 1
fi

# Step 4: Option to keep LocalStack running or stop it
echo ""
read -p "Do you want to keep LocalStack running for further testing? (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_status "Stopping LocalStack..."
    docker-compose down
    print_success "LocalStack stopped."
else
    print_success "LocalStack is still running."
    echo ""
    echo "Useful commands:"
    echo "  docker-compose logs -f localstack  # View logs"
    echo "  docker-compose down               # Stop LocalStack"
    echo "  python local_aws_setup.py         # Re-setup resources"
    echo "  python tests/lambdas/test_e2e_localstack.py  # Run tests again"
fi

echo ""
print_success "End-to-end testing complete!" 