# Tests

This directory contains all test-related code for the WordWeave project.

## Structure

```
tests/
├── README.md           # This file
├── mocks/             # Mock implementations for testing
│   ├── user_repository_mock.go
│   └── email_service_mock.go
├── unit/              # Unit tests
│   └── user_service_test.go
└── integration/       # Integration tests (future)
```

## Running Tests

### Unit Tests

```bash
# Run all unit tests
go test ./tests/unit -v

# Run specific test
go test ./tests/unit -v -run TestUserService_RegisterUser

# Run delete user tests specifically
go test ./tests/unit -v -run TestUserService_DeleteUser
```

### All Tests

```bash
# Run all tests in the project
go test ./...

# Run with coverage
go test ./... -cover
```

## Test Coverage

### Current Test Scenarios (12 test cases)

**User Registration (5 tests)**

- ✅ Successful registration with email sending
- ✅ Invalid email format validation
- ✅ Username length validation
- ✅ Duplicate email detection
- ✅ Duplicate username detection

**User Login (2 tests)**

- ✅ Successful login flow
- ✅ Invalid credential handling

**Email Confirmation (2 tests)**

- ✅ Successful email confirmation
- ✅ Invalid confirmation code handling

**User Deletion (4 tests)**

- ✅ Successful user deletion with cleanup
- ✅ Idempotent delete of non-existent user
- ✅ Idempotent delete with empty ID
- ✅ Idempotent delete same user twice

## Test Categories

### Unit Tests (`tests/unit/`)

- Test individual components in isolation
- Use mocks for external dependencies
- Fast execution (< 2 seconds)
- No external service dependencies

### Integration Tests (`tests/integration/`)

- Test component interactions
- May use real databases (with test containers)
- Test actual AWS services (with localstack)
- Slower execution but more realistic

### Mocks (`tests/mocks/`)

- In-memory implementations of interfaces
- Consistent, predictable behavior
- Used by unit tests
- Easy to setup and tear down

## Key Design Decisions

### Idempotent Operations

- **DELETE operations** are idempotent following REST principles
- Deleting a non-existent user returns success (204 No Content)
- This ensures consistent behavior and prevents client-side errors

### Async Email Handling

- Email sending is asynchronous in production
- Tests use `time.Sleep()` to wait for async operations
- Mock email service tracks all sent emails for verification

## Adding New Tests

1. **Unit Tests**: Add to `tests/unit/` directory
2. **Integration Tests**: Add to `tests/integration/` directory
3. **Mocks**: Add to `tests/mocks/` directory

### Test Naming Convention

- File: `{component}_test.go`
- Function: `Test{Component}_{Method}_{Scenario}`
- Example: `TestUserService_RegisterUser_InvalidEmail`

## Best Practices

1. **Arrange-Act-Assert**: Structure tests clearly
2. **Independent Tests**: Each test should be isolated
3. **Descriptive Names**: Test names should explain the scenario
4. **Fast Execution**: Unit tests should run quickly
5. **Good Coverage**: Aim for >80% test coverage
6. **Idempotent Operations**: Follow REST principles for HTTP methods
