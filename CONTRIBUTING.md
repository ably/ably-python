# Contributing to ably-python

## Contributing

### Initialising

ably-python uses [uv](https://docs.astral.sh/uv/) for packaging and dependency management. Please refer to the [uv documentation](https://docs.astral.sh/uv/getting-started/installation/) for up to date instructions on how to install uv.

Perform the following operations after cloning the repository contents:

```shell
git submodule init
git submodule update
# Install the crypto extra if you wish to be able to run all of the tests
uv sync --extra crypto
```

### Repository layout

This repository builds three distributions, released together on the same version. They all install into the one `ably` package, so what you import never tells you which distribution shipped it:

| Distribution | Source | Imported as | Role |
|--------------|--------|-------------|------|
| `ably` | [`ably/`](./ably), except `ably/pubsub` | `ably`, `ably.sync` | The shared core, containing all of the implementation |
| `ably-pubsub-server` | [`ably/pubsub/server/`](./ably/pubsub/server) | `ably.pubsub.server` | The server-side factories |
| `ably-pubsub-device` | [`ably/pubsub/device/`](./ably/pubsub/device) | `ably.pubsub.device` | The device-side factory |

Each side re-exports the core's public surface and adds factories that return the core's clients unchanged, so that the package a caller installs names the side their application runs on. They pin the core exactly, so any change to the core's public surface needs the corresponding re-export added to both.

The packaging metadata for the two pubsub distributions lives in [`packages/`](./packages), away from the code it ships. Two rules keep that arrangement working, and both are covered by [`test/unit/pubsub_packaging_test.py`](./test/unit/pubsub_packaging_test.py):

- **`ably/pubsub/` must not gain an `__init__.py`.** It is a namespace directory (PEP 420) so that two distributions can each contribute a subpackage to it. An `__init__.py` would belong to whichever one shipped it, and removing that distribution would take the other side's subpackage with it.
- **The source stays in the shared `ably/` tree**, not beside the `pyproject.toml` that ships it. `ably` is a regular package, so Python looks for `ably.pubsub` only under the directory `ably` itself was imported from — in a checkout, that is `ably/`. Each sdist reaches up to collect its subtree, and its wheel is then built from that sdist.

### Running the test suite

```shell
uv run pytest
```

Because the pubsub code lives in the `ably/` tree, `ably.pubsub.server` and `ably.pubsub.device` import from a checkout with nothing installed beyond the core. Their tests are in [`test/unit/`](./test/unit) and need no network.

To build all three distributions — build the sdist first, which `uv build` does by default:

```shell
uv build --out-dir dist
uv build packages/ably-pubsub-server --out-dir dist
uv build packages/ably-pubsub-device --out-dir dist
```

## Release Process (Claude Code)

1. Ensure that all work intended for this release has landed to `main`
2. Run `/release patch|minor|major` in Claude Code — this creates the release branch, bumps the version in all required files, and populates the [CHANGELOG](./CHANGELOG.md) with merged PRs since the last tag automatically
3. Review the `### What's Changed` entries in [CHANGELOG.md](./CHANGELOG.md) and adjust if needed, then commit any edits
4. Create a release PR (ensure you include an SDK Team Engineering Lead and the SDK Team Product Manager as reviewers) and gain approvals for it, then merge that to `main`
5. Create a tag named like `v2.0.1` and push it to GitHub - e.g. `git tag v2.0.1 && git push origin v2.0.1`
6. Create the release on GitHub including populating the release notes
7. Go to the [Release Workflow](https://github.com/ably/ably-python/actions/workflows/release.yml) and ask [ably/team-sdk](https://github.com/orgs/ably/teams/team-sdk) member to approve publishing to the PyPI registry
8. Update the [Ably Changelog](https://changelog.ably.com/) (via [headwayapp](https://headwayapp.co/)) with these changes

## Release Process (Manual)

Releases should always be made through a release pull request (PR), which needs to bump the version number and add to the [change log](CHANGELOG.md).

`ably`, `ably-pubsub-server` and `ably-pubsub-device` are published in a single upload, so that a release is all three or none of them — the wrappers pin the core exactly, so a partial release is an unusable one. This works because the short-lived token PyPI mints from an OIDC request carries every project that trusts the requesting configuration, which means **all three PyPI projects must register the same trusted publisher**: this repository, `release.yml`, and the `pypi` environment (and likewise `testpypi`). Adding a fourth distribution means registering it the same way before its first release, or the whole upload fails.

The release process must include the following steps:

1. Ensure that all work intended for this release has landed to `main`
2. Create a release branch named like `release/2.0.1`
3. Add a commit to bump the version number. All three distributions release in lockstep, so this means [`pyproject.toml`](./pyproject.toml), [`ably/__init__.py`](./ably/__init__.py), and, for each pubsub distribution, its `pyproject.toml` under [`packages/`](./packages) (both its own version and its `ably==` pins) and the `__version__` in its module under [`ably/pubsub/`](./ably/pubsub). The tests in [`test/unit/pubsub_packaging_test.py`](./test/unit/pubsub_packaging_test.py) fail if any of these drift apart
4. Run [`github_changelog_generator`](https://github.com/github-changelog-generator/github-changelog-generator) to automate the update of the [CHANGELOG](./CHANGELOG.md). This may require some manual intervention, both in terms of how the command is run and how the change log file is modified. Your mileage may vary:
   - The command you will need to run will look something like this: `github_changelog_generator -u ably -p ably-python --since-tag v2.0.0 --output delta.md --token $GITHUB_TOKEN_WITH_REPO_ACCESS`. Generate token [here](https://github.com/settings/tokens/new?description=GitHub%20Changelog%20Generator%20token).
   - Using the command above, `--output delta.md` writes changes made after `--since-tag` to a new file
   - The contents of that new file (`delta.md`) then need to be manually inserted at the top of the `CHANGELOG.md`, changing the "Unreleased" heading and linking with the current version numbers
   - Also ensure that the "Full Changelog" link points to the new version tag instead of the `HEAD`
5. Commit this change: `git add CHANGELOG.md && git commit -m "Update change log."`
6. Push the release branch to GitHub
7. Create a release PR (ensure you include an SDK Team Engineering Lead and the SDK Team Product Manager as reviewers) and gain approvals for it, then merge that to `main`
8. Create a tag named like `v2.0.1` and push it to GitHub - e.g. `git tag v2.0.1 && git push origin v2.0.1`
9. Create the release on GitHub including populating the release notes
10. Go to the [Release Workflow](https://github.com/ably/ably-python/actions/workflows/release.yml) and ask [ably/team-sdk](https://github.com/orgs/ably/teams/team-sdk) member to approve publishing to the PyPI registry. All three distributions go up in a single upload, so there is one approval for the release as a whole
11. Update the [Ably Changelog](https://changelog.ably.com/) (via [headwayapp](https://headwayapp.co/)) with these changes

We tend to use [github_changelog_generator](https://github.com/skywinder/Github-Changelog-Generator) to collate the information required for a change log update.
Your mileage may vary, but it seems the most reliable method to invoke the generator is something like:
`github_changelog_generator -u ably -p ably-python --since-tag v1.0.0 --output delta.md`
and then manually merge the delta contents in to the main change log (where `v1.0.0` in this case is the tag for the previous release).
