Contributing to ably-python
-----------

## Contributing

1. Fork it
2. Create your feature branch (`git checkout -b my-new-feature`)
3. Commit your changes (`git commit -am 'Add some feature'`)
4. Ensure you have added suitable tests and the test suite is passing (`py.test`)
5. Push to the branch (`git push origin my-new-feature`)
6. Create a new Pull Request

## Test suite

```shell
git submodule init
git submodule update
pip install -r requirements-test.txt
pytest test
```

## Release Process

1. Update [`setup.py`](./setup.py) and [`ably/__init__.py`](./ably/__init__.py) with the new version number
2. Run [`github_changelog_generator`](https://github.com/skywinder/Github-Changelog-Generator) to automate the update of the [CHANGELOG](./CHANGELOG.md). Once the CHANGELOG has completed, manually change the `Unreleased` heading and link with the current version number such as `v1.0.0`. Also ensure that the `Full Changelog` link points to the new version tag instead of the `HEAD`.
3. Commit
4. Run `python setup.py sdist upload -r ably` to build and upload this new package to PyPi
5. Tag the new version such as `git tag v1.0.0`
6. Visit https://github.com/ably/ably-python/tags and add release notes for the release including links to the changelog entry.
7. Push the tag to origin `git push origin v1.0.0`
