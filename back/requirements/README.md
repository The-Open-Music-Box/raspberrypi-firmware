# Requirements Directory

This directory contains all requirements files for the project:
- `base.txt`: Common dependencies for all environments.
- `prod.txt`: Production dependencies (minimal, imports `base.txt`).
- `dev.txt`: Development dependencies (imports `base.txt` + dev tools).
- `test.txt`: Test dependencies (imports `base.txt` + test tools).

**Usage:**
- For production: `pip install -r requirements/prod.txt`
- For development: `pip install -r requirements/dev.txt`
- For testing: `pip install -r requirements/test.txt`

**Note:** Update `base.txt` for shared runtime dependencies. Use pip-tools or manual curation as needed.
