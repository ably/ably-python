Contributing to ably-python
-----------

## Contributing

### Initialising

Perform the following operations after cloning the repository contents:

```shell
git submodule init
git submodule update
pip install -r requirements-test.txt
```

### Running the test suite

```shell
python -m pytest test
```

## Release Process

Releases should always be made through a release pull request (PR), which needs to bump the version number and add to the [change log](CHANGELOG.md).

The release process must include the following steps:

1. Ensure that all work intended for this release has landed to `main`
2. Create a release branch named like `release/1.2.3`
3. Add a commit to bump the version number, updating [`setup.py`](./setup.py) and [`ably/__init__.py`](./ably/__init__.py)
4. Add a commit to update the change log
5. Push the release branch to GitHub
6. Open a PR for the release against the release branch you just pushed
7. Gain approval(s) for the release PR from maintainer(s)
8. Land the release PR to `main`
9. From the `main` branch, run `python setup.py sdist upload -r ably` to build and upload this new package to PyPi
10. Create a tag named like `v1.2.3` and push it to GitHub - e.g. `git tag v1.2.3 && git push origin v1.2.3`
11. Create the release on GitHub including populating the release notes

We tend to use [github_changelog_generator](https://github.com/skywinder/Github-Changelog-Generator) to collate the information required for a change log update.
Your mileage may vary, but it seems the most reliable method to invoke the generator is something like:
`github_changelog_generator -u ably -p ably-python --since-tag v1.0.0 --output delta.md`
and then manually merge the delta contents in to the main change log (where `v1.0.0` in this case is the tag for the previous release).
