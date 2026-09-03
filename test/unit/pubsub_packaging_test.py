"""Invariants of the two distributions built from this repository.

`ably_pubsub` is assembled at install time out of `ably-pubsub-core` and
`ably-pubsub-server`. That only holds together if the namespace stays a PEP 420
namespace, if the two wheels never claim the same files, and if the versions
stay in lockstep with the server's exact pin on the core. None of those fail
anywhere closer to the mistake than a release, so they are asserted here.
"""

import re
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

import ably_pubsub.core
import ably_pubsub.server

REPO_ROOT = Path(__file__).resolve().parents[2]
CORE_SRC = REPO_ROOT / 'core' / 'src' / 'ably_pubsub'
SERVER_SRC = REPO_ROOT / 'server' / 'src' / 'ably_pubsub'


def pyproject_field(path, field):
    # Read rather than parse: tomllib only arrived in Python 3.11, and these are
    # double-quoted scalars at the top of the [project] table.
    match = re.search(rf'^{field} = "([^"]+)"', path.read_text(), re.MULTILINE)
    assert match, f'no {field} in {path}'
    return match.group(1)


# PEP 420: an __init__.py here would belong to whichever distribution shipped it,
# so the other one's subpackage would vanish when that distribution was removed
@pytest.mark.parametrize('src', [CORE_SRC, SERVER_SRC], ids=['core', 'server'])
def test_ably_pubsub_is_a_namespace_directory(src):
    assert src.is_dir()
    assert not (src / '__init__.py').exists()


def test_each_distribution_ships_only_its_own_subpackage():
    assert {p.name for p in CORE_SRC.iterdir()} == {'core'}
    assert {p.name for p in SERVER_SRC.iterdir()} == {'server'}


def test_the_three_version_sites_agree():
    core_version = pyproject_field(REPO_ROOT / 'core' / 'pyproject.toml', 'version')
    server_version = pyproject_field(REPO_ROOT / 'server' / 'pyproject.toml', 'version')
    assert core_version == ably_pubsub.core.lib_version
    assert server_version == ably_pubsub.core.lib_version
    assert ably_pubsub.server.__version__ == ably_pubsub.core.lib_version


def test_the_server_pins_the_core_exactly_including_every_extra():
    pyproject = (REPO_ROOT / 'server' / 'pyproject.toml').read_text()
    pins = set(re.findall(r'"ably-pubsub-core(?:\[[\w,]+\])?==([^"]+)"', pyproject))
    assert pins == {ably_pubsub.core.lib_version}


@pytest.mark.parametrize('extra', ['crypto', 'vcdiff', 'oldcrypto'])
def test_the_server_forwards_each_core_extra(extra):
    pyproject = (REPO_ROOT / 'server' / 'pyproject.toml').read_text()
    assert f'"ably-pubsub-core[{extra}]=={ably_pubsub.core.lib_version}"' in pyproject


def test_the_server_re_exports_everything_it_declares_public():
    missing = [name for name in ably_pubsub.server.__all__ if not hasattr(ably_pubsub.server, name)]
    assert missing == []


def test_the_server_declares_everything_it_re_exports():
    """Nothing pulled out of the core is public by accident and undocumented."""
    from_the_core = {
        name for name, value in vars(ably_pubsub.server).items()
        if not name.startswith('_') and name[0].isupper()
        and getattr(value, '__module__', '').startswith('ably_pubsub.')
    }
    assert from_the_core
    assert from_the_core <= set(ably_pubsub.server.__all__)


@pytest.mark.timeout(300)
@pytest.mark.skipif(shutil.which('uv') is None, reason='needs uv to build the distributions')
def test_the_two_wheels_do_not_overlap(tmp_path):
    for package in ('ably-pubsub-core', 'ably-pubsub-server'):
        subprocess.run(
            ['uv', 'build', '--package', package, '--wheel', '--out-dir', str(tmp_path)],
            cwd=REPO_ROOT, check=True, capture_output=True)

    wheels = {}
    for wheel in tmp_path.glob('*.whl'):
        with zipfile.ZipFile(wheel) as z:
            wheels[wheel.name.split('-')[0]] = set(z.namelist())

    assert set(wheels) == {'ably_pubsub_core', 'ably_pubsub_server'}
    core, server = wheels['ably_pubsub_core'], wheels['ably_pubsub_server']

    assert core & server == set()
    # The generated sync flavour is not in version control, so a build that
    # forgot to run unasync first would otherwise publish silently
    assert any(name.startswith('ably_pubsub/core/sync/') for name in core)
    assert 'ably_pubsub/__init__.py' not in core | server
    assert all(name.startswith(('ably_pubsub/core/', 'ably_pubsub_core-')) for name in core)
    assert all(name.startswith(('ably_pubsub/server/', 'ably_pubsub_server-')) for name in server)
