---
description: "Create a release branch, bump version, and update CHANGELOG. Usage: /release patch|minor|major"
allowed-tools: Bash, Read, Edit, Write
---

Read the current version from `pyproject.toml` (the `version` property).

The bump type is: $ARGUMENTS

Compute the new version by incrementing the appropriate component of the current version:
- `patch` — increment the third number, keep major and minor (e.g. 1.7.0 → 1.7.1)
- `minor` — increment the second number, reset patch to 0 (e.g. 1.7.0 → 1.8.0)
- `major` — increment the first number, reset minor and patch to 0 (e.g. 1.7.0 → 2.0.0)

Then perform these steps in order:

1. Run `git checkout -b release/NEW_VERSION`

2. Replace `OLD_VERSION` with `NEW_VERSION` everywhere it appears in these files. This
   repository publishes three distributions — `ably`, `ably-pubsub-server` and
   `ably-pubsub-device` — which release in lockstep on the same version, so every one of
   these must move together:

   | File                                         | What to change                                                      |
   |----------------------------------------------|---------------------------------------------------------------------|
   | `pyproject.toml`                             | the `version` property                                              |
   | `ably/__init__.py`                           | `lib_version`                                                       |
   | `packages/ably-pubsub-server/pyproject.toml` | the `version` property **and** every `ably==` / `ably[extra]==` pin |
   | `packages/ably-pubsub-device/pyproject.toml` | the `version` property **and** every `ably==` / `ably[extra]==` pin |
   | `ably/pubsub/server/__init__.py`             | `__version__`                                                       |
   | `ably/pubsub/device/__init__.py`             | `__version__`                                                       |

   The pins in `packages/*/pyproject.toml` are easy to miss: each of those files carries the
   version four times over (its own `version`, the `ably==` dependency, and the `oldcrypto`,
   `crypto` and `vcdiff` extras). Confirm with `grep -rn OLD_VERSION` that nothing is left
   behind before moving on — the old version must appear nowhere except `CHANGELOG.md` and
   `uv.lock`.

3. Run `uv sync` to update the `uv.lock` file.

4. Verify the bump is complete and consistent by running:
   ```
   uv run pytest test/unit/pubsub_packaging_test.py -q
   ```
   These tests assert that all three distributions carry the same version and that each
   wrapper pins the core exactly, so they fail if any location was missed. Do not continue
   until they pass.

5. Commit all changed files together with message: `chore: bump version to NEW_VERSION`

6. Fetch merged PRs since the last release tag using:
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

7. In `CHANGELOG.md`, insert the following block immediately after the `# Change Log` heading
   (and its trailing blank line), before the first existing `## [` version entry:

    ```
    ## [NEW_VERSION](https://github.com/ably/ably-python/tree/vNEW_VERSION)

    [Full Changelog](https://github.com/ably/ably-python/compare/vOLD_VERSION...vNEW_VERSION)

    ### What's Changed

    BULLETS_FROM_STEP_6

    ```

8. Commit `CHANGELOG.md` with message: `docs: update CHANGELOG for NEW_VERSION release`

After completing all steps, show the user a summary of what was done, including the list of
files whose version was bumped. If PRs were found, list them. If the placeholder `-` was used
instead, remind them to fill in the `### What's Changed` bullet points in `CHANGELOG.md`
before merging.

Also remind them that a new distribution added to `packages/` in future must be added to the
table in step 2, or its version will silently drift out of lockstep with the others.
