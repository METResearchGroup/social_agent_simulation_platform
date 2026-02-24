# Testing Guide

This directory contains the test suite for the agent simulation platform.

## Prerequisites

- [uv](https://github.com/astral-sh/uv) package manager installed
- All test dependencies are defined in `pyproject.toml` under `[project.optional-dependencies.test]`

## Running Tests

All tests should be run from the **root directory** of the project using `uv run pytest`.

### Basic Commands

```bash
# Run all tests
uv run pytest

# Run all tests with verbose output
uv run pytest -v

# Run tests in a specific directory
uv run pytest tests/db/

# Run a specific test file
uv run pytest tests/db/repositories/test_run_repository.py

# Run a specific test class
uv run pytest tests/db/repositories/test_run_repository.py::TestSQLiteRunRepositoryCreateRun

# Run a specific test method
uv run pytest tests/db/repositories/test_run_repository.py::TestSQLiteRunRepositoryCreateRun::test_creates_run_with_correct_config_values
```

### Coverage Reports

```bash
# Run tests with coverage report
uv run pytest --cov=db --cov-report=term-missing

# Generate HTML coverage report
uv run pytest --cov=db --cov-report=html

# View HTML report (after generation)
open htmlcov/index.html
```

### Test Output Options

```bash
# Short traceback format (default)
uv run pytest --tb=short

# Line-only traceback (minimal output)
uv run pytest --tb=line

# Long traceback (detailed output)
uv run pytest --tb=long

# No traceback (just summary)
uv run pytest --tb=no
```

## Test Structure

Tests follow the structure of the source code:

```text
tests/
├── db/
│   └── repositories/
│       └── test_run_repository.py
└── README.md
```

## Test Standards

All tests follow the project's testing standards:

- **100% test coverage** required for all new/modified code
- **One test class per function** - Each function gets its own test class
- **Arrange-Act-Assert pattern** - Tests follow consistent structure
- **Mock external dependencies** - Database, APIs, and external services are mocked
- **Descriptive test names** - Test names clearly describe what they verify
- **Comprehensive docstrings** - Every test method has a docstring

## Troubleshooting

### Import Errors

If you encounter import errors, ensure you're running tests from the root directory with `uv run pytest`. The `uv` command automatically handles Python path configuration.

### Missing Dependencies

If test dependencies are missing, install them with:

```bash
uv sync --extra test
```

### Path Conflicts

If you encounter path conflicts (e.g., importing from wrong `lib.timestamp_utils`), ensure you're using `uv run pytest` from the root directory, which handles path configuration automatically.

## Continuous Integration

Tests are designed to run in CI environments without any special configuration. Simply run:

```bash
uv run pytest
```

from the project root directory.
