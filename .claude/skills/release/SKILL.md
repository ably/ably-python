---
description: "Create a release branch, bump version, and update CHANGELOG. Usage: /release patch|minor|major"
allowed-tools: Bash, Read, Edit, Write
---

Read the current version from `core/pyproject.toml` (the `version` property). Both
distributions built from this repo — `ably-pubsub-core` and `ably-pubsub-server` —
are released in lockstep, so there is one version for all of the sites below and
they must never diverge. One `vX.Y.Z` tag releases both distributions: the release
workflow builds them together, refuses to upload anything unless every site agrees,
and publishes the core before the server.

The bump type is: $ARGUMENTS

Compute the new version by incrementing the appropriate component of the current version:
- `patch` — increment the third number, keep major and minor (e.g. 1.7.0 → 1.7.1)
- `minor` — increment the second number, reset patch to 0 (e.g. 1.7.0 → 1.8.0)
- `major` — increment the first number, reset minor and patch to 0 (e.g. 1.7.0 → 2.0.0)

Then perform these steps in order:

1. Run `git checkout -b release/NEW_VERSION`
2. Replace `OLD_VERSION` with `NEW_VERSION` in all of the following places:
    - `core/pyproject.toml` — the `version` property
    - `server/pyproject.toml` — the `version` property, **and** every
      `ably-pubsub-core==OLD_VERSION` pin in `[project.dependencies]` and
      `[project.optional-dependencies]`
    - `core/src/ably_pubsub/core/__init__.py` — `lib_version` value
    - `server/src/ably_pubsub/server/__init__.py` — `__version__` value
3. Run `uv sync` to update the `uv.lock` file
4. Run `uv run python scripts/release_preflight.py --version NEW_VERSION` — the
   same check the release workflow runs before it uploads anything, in its
   build-free mode (no `dist/` argument), so a missed site fails here rather
   than mid-release
5. Run `uv run pytest test/unit/pubsub_packaging_test.py` — the packaging
   invariants that do not depend on a build
6. Commit all files together with message: `chore: bump version to NEW_VERSION`
7. Fetch merged PRs since the last release tag using:
   ```
   gh pr list --state merged --base main --json number,title,mergedAt --limit 200
   ```
   Then get the date of the last release tag with:
   ```
   git log vOLD_VERSION --format="%aI" -1
   ```
   Filter the PRs to only those merged after that tag date. Format each as:
   ```
   - Short, one sentence summary from PR title and description [#NUMBER](https://github.com/ably/ably-python/pull/NUMBER)
   ```
   If the tag doesn't exist or there are no merged PRs, use a single `-` placeholder bullet instead.

8. In `CHANGELOG.md`, insert the following block immediately after the `# Change Log` heading (and its trailing blank line), before the first existing `## [` version entry:

```
## [NEW_VERSION](https://github.com/ably/ably-python/tree/vNEW_VERSION)

[Full Changelog](https://github.com/ably/ably-python/compare/vOLD_VERSION...vNEW_VERSION)

### What's Changed

BULLETS_FROM_STEP_7

```

9. Commit `CHANGELOG.md` with message: `docs: update CHANGELOG for NEW_VERSION release`

After completing all steps, show the user a summary of what was done. If PRs were found, list them. If the placeholder `-` was used instead, remind them to fill in the `### What's Changed` bullet points in `CHANGELOG.md` before merging.
