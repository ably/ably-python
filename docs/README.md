# Documentation

This directory contains the source files for the Ably Python SDK documentation, built using [MkDocs](https://www.mkdocs.org/) and [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/).

## Building the Documentation

### Prerequisites

- Python 3.12 or higher (documentation tools require Python 3.12+)
- Install documentation dependencies: `uv sync --extra docs`

### Build HTML Documentation

```bash
# Build the documentation
uv run mkdocs build

# The generated HTML will be in the site/ directory
```

### Serve Documentation Locally

```bash
# Start a local development server
uv run mkdocs serve

# Open http://127.0.0.1:8000/ in your browser
```

The development server automatically rebuilds the documentation when you make changes to the source files.

## Documentation Structure

- `docs/` - Documentation source files (Markdown)
  - `index.md` - Home page
  - `api/` - API reference documentation
- `mkdocs.yml` - MkDocs configuration
- `site/` - Generated HTML documentation (gitignored)

## How It Works

The documentation uses [mkdocstrings](https://mkdocstrings.github.io/) to automatically generate API documentation from Python docstrings. The special `:::` syntax in Markdown files tells mkdocstrings to extract and render documentation from Python modules:

```markdown
::: ably.rest.rest.AblyRest
```

This automatically generates formatted documentation including:
- Class and method signatures
- Docstrings
- Type hints
- Parameters and return types
