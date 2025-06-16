# Makefile for AWS CDK and Lambda management
.PHONY: help clean build synth deploy deploy-all destroy-all lambda-build lambda-layer lambda-function maven-build full-build

# Default target
help:
	@echo "Available targets:"
	@echo "  clean           - Clean build artifacts"
	@echo "  maven-build     - Maven clean install"
	@echo "  lambda-build    - Build both Lambda layer and function"
	@echo "  lambda-layer    - Build only Lambda layer"
	@echo "  lambda-function - Build only Lambda function"
	@echo "  synth           - CDK synthesize"
	@echo "  full-build      - Maven build + CDK synth"
	@echo "  deploy-sqs      - Deploy SqsLambdaStack only"
	@echo "  deploy-all      - Deploy all stacks"
	@echo "  destroy-all     - Destroy all stacks"
	@echo "  rebuild-deploy  - Clean + build + deploy all"

# Clean targets
clean-all:
	python3 build_lambda.py clean
	mvn clean

# Maven build
maven-build:
	mvn clean install

# Lambda build targets
lambda-full-build:
	python3 build_lambda.py

lambda-layer-build:
	python3 build_lambda.py layer

lambda-function-build:
	python3 build_lambda.py function

# CDK targets
synth:
	cdk synth

full-build: maven-build lambda-full-build synth
	@echo "Full build completed"

# Deploy targets
deploy-sqs: cdk deploy vStack/SqsLambdaStack --require-approval never

deploy-all: cdk deploy --all --require-approval never

# Destroy target
destroy-all:
	cdk destroy --all --require-approval never

# Combined workflows
rebuild-deploy: clean-all full-build deploy-all
	@echo "Complete rebuild and deployment finished"

# Quick development cycle
dev: lambda-full-build deploy-sqs
	@echo "Development deployment completed"

# Full CI/CD pipeline
ci: clean-lambda full-build lambda-full-build deploy-all
	@echo "CI/CD pipeline completed"