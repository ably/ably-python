# Contributing to ably-python

## Contributing

### Initialising

ably-python uses [Poetry](https://python-poetry.org/) for packaging and dependency management. Please refer to the [Poetry documentation](https://python-poetry.org/docs/#installation) for up to date instructions on how to install Poetry.

Perform the following operations after cloning the repository contents:

```shell
git submodule init
git submodule update
# Install the crypto extra if you wish to be able to run all of the tests
poetry install -E crypto
```

### Running the test suite

```shell
poetry run pytest
```

## Release Process

Releases should always be made through a release pull request (PR), which needs to bump the version number and add to the [change log](CHANGELOG.md).

The release process must include the following steps:

1. Ensure that all work intended for this release has landed to `main`
2. Create a release branch named like `release/2.0.1`
3. Add a commit to bump the version number, updating [`pyproject.toml`](./pyproject.toml) and [`ably/__init__.py`](./ably/__init__.py)
4. Run [`github_changelog_generator`](https://github.com/github-changelog-generator/github-changelog-generator) to automate the update of the [CHANGELOG](./CHANGELOG.md). This may require some manual intervention, both in terms of how the command is run and how the change log file is modified. Your mileage may vary:
   - The command you will need to run will look something like this: `github_changelog_generator -u ably -p ably-python --since-tag v2.0.0 --output delta.md --token $GITHUB_TOKEN_WITH_REPO_ACCESS`. Generate token [here](https://github.com/settings/tokens/new?description=GitHub%20Changelog%20Generator%20token).
   - Using the command above, `--output delta.md` writes changes made after `--since-tag` to a new file
   - The contents of that new file (`delta.md`) then need to be manually inserted at the top of the `CHANGELOG.md`, changing the "Unreleased" heading and linking with the current version numbers
   - Also ensure that the "Full Changelog" link points to the new version tag instead of the `HEAD`
5. Commit this change: `git add CHANGELOG.md && git commit -m "Update change log."`
6. Push the release branch to GitHub
7. Create a release PR (ensure you include an SDK Team Engineering Lead and the SDK Team Product Manager as reviewers) and gain approvals for it, then merge that to `main`
8. Build the synchronous REST client by running `poetry run unasync`
9. From the `main` branch, run `poetry build && poetry publish` (will require you to have a PyPi API token, see [guide](https://www.digitalocean.com/community/tutorials/how-to-publish-python-packages-to-pypi-using-poetry-on-ubuntu-22-04)) to build and upload this new package to PyPi
10. Create a tag named like `v2.0.1` and push it to GitHub - e.g. `git tag v2.0.1 && git push origin v2.0.1`
11. Create the release on GitHub including populating the release notes
12. Update the [Ably Changelog](https://changelog.ably.com/) (via [headwayapp](https://headwayapp.co/)) with these changes

We tend to use [github_changelog_generator](https://github.com/skywinder/Github-Changelog-Generator) to collate the information required for a change log update.
Your mileage may vary, but it seems the most reliable method to invoke the generator is something like:
`github_changelog_generator -u ably -p ably-python --since-tag v1.0.0 --output delta.md`
and then manually merge the delta contents in to the main change log (where `v1.0.0` in this case is the tag for the previous release).
