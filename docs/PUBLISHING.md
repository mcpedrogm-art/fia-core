# Publishing

## PyPI (trusted publishing)

The repository ships [`.github/workflows/publish.yml`](../.github/workflows/publish.yml).
It publishes to PyPI when a GitHub Release is published, using OIDC trusted
publishing: no API token is stored anywhere.

One-time setup (PyPI side, by a maintainer):

1. Sign in at <https://pypi.org>.
2. Go to **Publishing → Add a pending publisher** (the project does not exist
   yet) and fill in:
   - PyPI project name: `fia-core-full`
   - Owner: `mcpedrogm-art`
   - Repository name: `fia-core`
   - Workflow name: `publish.yml`
   - Environment name: `pypi`

The PyPI distribution is named `fia-core-full`; the import package (`fia_core`)
and the command (`fia`) do not change.

Then, for every release:

1. Bump `version` in `pyproject.toml` and `fia_core/__init__.py`.
2. Update `CHANGELOG.md`.
3. Publish a GitHub Release with a tag like `v0.2.0`.

The workflow builds the sdist and wheel and uploads them.

## Manual upload (alternative)

```bash
python -m build
python -m twine upload dist/*
```

Twine asks for the username `__token__` and your PyPI API token.
