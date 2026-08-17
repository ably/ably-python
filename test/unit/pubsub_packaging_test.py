"""ably.pubsub is assembled at install time from three distributions.

`ably` ships the core, `ably-pubsub-server` ships `ably/pubsub/server` and
`ably-pubsub-device` ships `ably/pubsub/device`. That only holds together if
`ably.pubsub` stays a namespace directory and the three stay on one version, so
this covers both — neither fails anywhere closer to the mistake than a release.
"""

import re
from pathlib import Path

import pytest

import ably
from ably.pubsub import device, server

REPO_ROOT = Path(__file__).resolve().parents[2]

WRAPPERS = [
    ('ably-pubsub-server', server),
    ('ably-pubsub-device', device),
]


def pyproject_field(path, field):
    # Read rather than parse: tomllib only arrived in Python 3.11, and these are
    # double-quoted scalars at the top of the [project] table.
    match = re.search(rf'^{field} = "([^"]+)"', path.read_text(), re.MULTILINE)
    assert match, f'no {field} in {path}'
    return match.group(1)


# PEP 420: an __init__.py here would belong to whichever distribution shipped it,
# so the other one's subpackage would vanish when that distribution was removed
def test_pubsub_is_a_namespace_directory():
    assert not (REPO_ROOT / 'ably' / 'pubsub' / '__init__.py').exists()


@pytest.mark.parametrize('name,module', WRAPPERS)
def test_each_side_is_a_package_of_its_own(name, module):
    assert Path(module.__file__).name == '__init__.py'


def test_the_core_version_matches_its_pyproject():
    assert pyproject_field(REPO_ROOT / 'pyproject.toml', 'version') == ably.lib_version


@pytest.mark.parametrize('name,module', WRAPPERS)
def test_wrapper_version_matches_its_pyproject(name, module):
    assert pyproject_field(REPO_ROOT / 'packages' / name / 'pyproject.toml', 'version') == module.__version__


@pytest.mark.parametrize('name,module', WRAPPERS)
def test_wrapper_is_released_in_lockstep_with_the_core(name, module):
    assert module.__version__ == ably.lib_version


@pytest.mark.parametrize('name,module', WRAPPERS)
def test_wrapper_pins_the_core_exactly(name, module):
    pyproject = (REPO_ROOT / 'packages' / name / 'pyproject.toml').read_text()
    pins = set(re.findall(r'"ably(?:\[\w+\])?==([^"]+)"', pyproject))
    assert pins == {ably.lib_version}


@pytest.mark.parametrize('name,module', WRAPPERS)
def test_wrapper_ships_only_its_own_subtree(name, module):
    pyproject = (REPO_ROOT / 'packages' / name / 'pyproject.toml').read_text()
    side = name.rsplit('-', 1)[1]
    assert f'only-include = ["ably/pubsub/{side}"]' in pyproject
