---
title: "Code Style Guide and Pre-commit Hooks"
status: active
category: guide
last_reviewed: 2026-02-09
review_cycle: 6months
---

# Code Style Guide and Pre-commit Hooks

This document describes the code style rules and pre-commit hooks used in the TheOpenMusicBox project. Following these rules ensures a consistent codebase and facilitates collaboration between developers.

## Table of Contents

1. [Pre-commit Hooks](#pre-commit-hooks)
2. [Pydocstyle Rules](#pydocstyle-rules)
3. [Flake8 Rules](#flake8-rules)
4. [Black Configuration](#black-configuration)
5. [Isort Configuration](#isort-configuration)
6. [Docformatter](#docformatter)
7. [Best Practices](#best-practices)
8. [Troubleshooting Common Issues](#troubleshooting-common-issues)

## Pre-commit Hooks

The project uses several pre-commit hooks to ensure code quality before each commit:

- **black**: Automatic code formatter
- **isort**: Import organization
- **flake8**: Linter for detecting errors and style issues
- **docformatter**: Docstring formatter
- **pydocstyle**: Documentation convention checker

These hooks run automatically when you attempt to make a commit. If any of them fails, the commit is blocked until the issues are resolved.

## Pydocstyle Rules

The following pydocstyle rules are enabled in our configuration (`.pydocstyle`):

### Enabled Rules

- **D101**: Public classes must have a docstring
- **D102**: Public methods must have a docstring
- **D103**: Public functions must have a docstring
- **D205**: A blank line is required between the summary line and the description
- **D400**: The first line must end with a period

**Note**: Rule D200 (Single-line docstrings must fit on one line) has been disabled to allow more flexibility in the presentation of short docstrings.

### Correct Format for Docstrings

```python
def my_function(param1, param2):
    """This is a summary that ends with a period.

    This is the detailed description that is separated
    from the summary line by a blank line.

    Args:
        param1: Description of the first parameter.
        param2: Description of the second parameter.

    Returns:
        Description of what the function returns.

    Raises:
        ExceptionType: Description of conditions that trigger the exception.
    """
    pass
```

### Common Errors and Solutions

| Error | Description | Solution |
|-------|-------------|----------|
| D205 | No blank line between summary and description | Add a blank line after the first line |
| D400 | First line does not end with a period | Add a period at the end of the first line |

## Flake8 Rules

Flake8 checks code compliance with PEP 8 and detects potential errors.

### Important Rules

- **E501**: Line length limit (typically 88 or 100 characters)
- **F401**: Unused imports
- **F841**: Unused local variables
- **E302/E305**: Correct spacing between functions/classes (2 blank lines)
- **E231**: Spacing after commas

### Compliant Code Example

```python
import os
from typing import Dict, List, Optional


# Two blank lines before class definitions
class MyClass:
    """This class does something useful."""

    def __init__(self, param1: str, param2: int = 0):
        """Initialize the instance.

        Args:
            param1: First parameter.
            param2: Second parameter, defaults to 0.
        """
        self.param1 = param1
        self.param2 = param2

    # One blank line between methods
    def my_method(self, items: List[str]) -> Dict[str, int]:
        """Do something with the items.

        Args:
            items: List of items to process.

        Returns:
            Dictionary of results.
        """
        result = {}
        for item in items:
            result[item] = len(item)
        return result
```

## Black Configuration

Black is a code formatter that applies a consistent style to all Python code.

### Main Rules

- Maximum line length of 88 characters
- Use of double quotes for strings
- 4-space indentation
- Spacing around operators
- Automatic formatting of lists, dictionaries, and function calls

### How to Use Black

```bash
# Format a file
black app/src/services/my_file.py

# Format all Python files in a directory
black app/src/
```

## Isort Configuration

Isort organizes imports according to a standard order.

### Organization Rules

1. Python standard library imports first
2. Third-party imports next
3. Local imports last
4. Alphabetical sorting within each section

### Well-Organized Imports Example

```python
# Standard imports
import os
import sys
from pathlib import Path

# Third-party imports
import numpy as np
import pandas as pd
from flask import Flask

# Local imports
from app.src.config import app_config
from app.src.helpers.exceptions import InvalidFileError
```

## Docformatter

The `docformatter` tool is used to automatically format docstrings according to PEP 257 conventions. It ensures that:

- Triple quotes are on separate lines
- Formatting is consistent
- Indentation is correct
- Lists are properly formatted

### Docformatter Configuration

To ensure compatibility with pydocstyle rules (notably D205 and D400), docformatter is configured with the following arguments in our pre-commit:

```yaml
args:
  - --in-place                # Modifies files in place
  - --pre-summary-newline     # Ensures a blank line after opening quotes
  - --make-summary-multi-line # Ensures the summary line ends with a period
  - --force-wrap              # Forces wrapping of long lines
  - --wrap-summaries=88       # Limits summary line length
  - --wrap-descriptions=88    # Limits description line length
```

**Important**: This configuration ensures compliance with rules D205 (blank line after summary) and D400 (period at the end of summary) required by our pydocstyle configuration.

Docformatter ensures that docstrings follow a consistent format.

### Main Features

- Correct docstring indentation
- Appropriate spacing
- Formatting of Args, Returns, Raises sections, etc.

### How to Use Docformatter

```bash
# Format a file
docformatter --in-place app/src/services/my_file.py

# Format with specific options
docformatter --in-place --make-summary-multi-line --pre-summary-newline app/src/services/my_file.py
```

## Best Practices

### For Docstrings

1. **Be concise but complete**: The first line should clearly summarize the purpose of the function/class.
2. **Document all parameters**: Each parameter must be documented with its type and purpose.
3. **Document return values**: Specify what the function returns.
4. **Document exceptions**: Indicate which exceptions can be raised and under what conditions.

### For Code Style

1. **Run formatting tools before committing**: Use `black` and `isort` to format your code.
2. **Limit line length**: Keep lines under 88 characters.
3. **Use descriptive names**: Variable and function names should be clear and descriptive.
4. **Follow naming conventions**:
   - `snake_case` for variables and functions
   - `PascalCase` for classes
   - `UPPER_SNAKE_CASE` for constants

## Troubleshooting Common Issues

### Temporarily Bypassing Hooks

In some cases, you may need to temporarily bypass pre-commit hooks:

```bash
git commit --no-verify -m "Commit message"
```

**Note**: This practice should be used sparingly and only in exceptional situations.

### Resolving Pydocstyle Errors

1. **D205 (missing blank line)**:
   ```python
   def my_function():
       """This is a summary.

       This is the description.
       """
   ```

2. **D400 (missing period)**:
   ```python
   def my_function():
       """This is a summary that ends with a period.
       """
   ```

### Resolving Flake8 Errors

1. **E501 (line too long)**:
   - Split long strings
   - Use parentheses to split expressions
   - Reorganize logic across multiple lines

2. **F401 (unused import)**:
   - Remove unused imports
   - If the import is needed for side effects, add `# noqa: F401`

---

This guide is a living document that will be updated as code standards evolve. For any questions or suggestions, please contact the development team.
