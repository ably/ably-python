# Contributing to ably-python

## Contributing

### Initialising

ably-python uses [uv](https://docs.astral.sh/uv/) for packaging and dependency management. Please refer to the [uv documentation](https://docs.astral.sh/uv/getting-started/installation/) for up to date instructions on how to install uv.

Perform the following operations after cloning the repository contents:

```shell
git submodule init
git submodule update
# Installs both workspace members editable, with the core's crypto and vcdiff extras
uv sync
```

### Running the test suite

```shell
uv run pytest
```

## Release Process

This repository builds **two** distributions, `ably-pubsub-core` and
`ably-pubsub-server`, and releases them **in lockstep**: one version, one tag,
one workflow run. The server pins `ably-pubsub-core==<that version>` exactly, so
a version published for one and not the other is either uninstallable or
invisible.

### Cutting a release

1. Ensure that all work intended for this release has landed to `main`
2. Run `/release patch|minor|major` in Claude Code — this creates the release
   branch, moves every version site together (`core/pyproject.toml`,
   `server/pyproject.toml` including its `ably-pubsub-core==` pins,
   `core/src/ably_pubsub/core/__init__.py`'s `lib_version`, and
   `server/src/ably_pubsub/server/__init__.py`'s `__version__`), refreshes
   `uv.lock`, runs the release pre-flight, and populates the
   [CHANGELOG](./CHANGELOG.md) with merged PRs since the last tag
3. Review the `### What's Changed` entries in [CHANGELOG.md](./CHANGELOG.md) and
   adjust if needed, then commit any edits
4. Create a release PR (ensure you include an SDK Team Engineering Lead and the
   SDK Team Product Manager as reviewers) and gain approvals for it, then merge
   that to `main`
5. Create and push a tag named like `v4.0.1` — one tag releases **both**
   distributions
6. Create the release on GitHub including populating the release notes
7. Go to the [Release Workflow](https://github.com/ably/ably-python/actions/workflows/release.yml)
   and ask an [ably/team-sdk](https://github.com/orgs/ably/teams/team-sdk) member
   to approve the `pypi` environment — that required-reviewer gate is the
   approval step for publishing
8. Update the [Ably Changelog](https://changelog.ably.com/) (via
   [headwayapp](https://headwayapp.co/)) with these changes

### What the pre-flight guarantees

Before anything is uploaded, `scripts/release_preflight.py` (run by
`release.yml`, and on every pull request by `check.yml`'s `release-dry-run` job)
fails the run unless:

- the release version is a valid PEP 440 version and equals **every** version
  site and every `ably-pubsub-core==` pin in the server's pyproject, including
  the ones in each extra;
- `dist/` holds exactly one wheel and one sdist per distribution, at that
  version, and nothing else;
- the core wheel and sdist carry the generated `ably_pubsub/core/sync/` flavour
  (i.e. `unasync` ran);
- neither wheel ships `ably_pubsub/__init__.py` — the namespace must stay
  PEP 420, or the two distributions fight over the same directory;
- the two wheels' file lists do not overlap;
- both distributions bundle `LICENSE`;
- `twine check` passes on all four artifacts.

You can run it yourself at any time:

```shell
# Version sites only, no build needed
uv run python scripts/release_preflight.py

# The full check, exactly what release.yml runs
uv sync && uv run unasync
uv build --package ably-pubsub-core --out-dir dist
uv build --package ably-pubsub-server --out-dir dist
uv run python scripts/release_preflight.py --version 4.0.1 dist/
```

### If the PyPI step fails between core and server

PyPI has no cross-project transaction, so a release is two uploads and the
second can fail after the first has succeeded. That state is expected and
recoverable:

- **Re-run the workflow at the same version.** Both publish steps set
  `skip-existing: true`, so the already-published core is skipped and the server
  is published, completing the release.
- **Never bump the version to get out of a partial release** — that leaves an
  orphan core version on the index forever.
- The core is always published *before* the server, so the failure mode is
  always "core is up, server is not", never a server pinning a core that does
  not exist.

### Prereleases and manual runs

`release.yml` also accepts a `workflow_dispatch` with an explicit version, which
is how prereleases are cut from a branch:

```shell
# TestPyPI only
gh workflow run release.yml --ref pubsub-split/some-branch -f version=4.0.0rc1

# TestPyPI and PyPI
gh workflow run release.yml --ref pubsub-split/some-branch -f version=4.0.0rc1 -f publish=true
```

A dispatch run always publishes to TestPyPI and only reaches PyPI when
`publish: true` is set. `workflow_dispatch` resolves the workflow file from the
**default branch**, so `release.yml` must exist on `main` for this to work even
when `--ref` points elsewhere. Every run — tag or dispatch — publishes to
TestPyPI as the staging step.

### Trusted publisher configuration

Publishing uses PyPI trusted publishing (OIDC); there are no API tokens in this
repository. Both `ably-pubsub-core` and `ably-pubsub-server` must have a trusted
publisher registered **on pypi.org and on test.pypi.org**, bound to this
repository, the workflow file `release.yml`, and the `pypi` / `testpypi`
environment respectively. That configuration lives on pypi.org, not in this
repo — see plan step 16 in [`plan.md`](./plan.md). PyPI's OIDC token covers every
project that trusts the requesting configuration, so a single job's
`id-token: write` publishes both projects.

### Fallback: generating the change log by hand

If `/release` is unavailable, the CHANGELOG section can be produced with
[`github_changelog_generator`](https://github.com/github-changelog-generator/github-changelog-generator):

```shell
github_changelog_generator -u ably -p ably-python --since-tag v4.0.0 --output delta.md --token $GITHUB_TOKEN_WITH_REPO_ACCESS
```

Then merge `delta.md` into the top of `CHANGELOG.md` by hand, changing the
"Unreleased" heading and pointing the "Full Changelog" link at the new tag. The
version sites still have to be moved together — run
`uv run python scripts/release_preflight.py` afterwards to prove they were.
