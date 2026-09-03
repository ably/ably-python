#!/usr/bin/env python3
"""Pre-flight checks for a lockstep release of ably-pubsub-core and ably-pubsub-server.

Both distributions are released at one version and the server pins the core
exactly, so a release is only meaningful if every version site agrees and both
sets of artifacts are well formed. PyPI has no cross-project transaction: once
the core is uploaded it cannot be taken back, so everything that can be checked
must be checked *before* the first upload.

This is the single implementation behind both callers:

    # release.yml — the version comes from the tag or the dispatch input
    uv run python scripts/release_preflight.py --version 4.0.0 dist/

    # check.yml release-dry-run — no authoritative version, just internal agreement
    uv run python scripts/release_preflight.py dist/

    # /release skill and local use — version sites only, no build needed
    uv run python scripts/release_preflight.py

Exit status is 0 when every check passes and 1 otherwise, with every failure
reported (the run does not stop at the first one).
"""

import argparse
import re
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

CORE_PYPROJECT = REPO_ROOT / 'core' / 'pyproject.toml'
SERVER_PYPROJECT = REPO_ROOT / 'server' / 'pyproject.toml'
CORE_INIT = REPO_ROOT / 'core' / 'src' / 'ably_pubsub' / 'core' / '__init__.py'
SERVER_INIT = REPO_ROOT / 'server' / 'src' / 'ably_pubsub' / 'server' / '__init__.py'

CORE_DIST = 'ably_pubsub_core'
SERVER_DIST = 'ably_pubsub_server'

# PEP 440, the subset a release can actually be: a release segment, an optional
# pre/post/dev suffix. Local versions are excluded — PyPI rejects them.
PEP_440 = re.compile(
    r'^([1-9][0-9]*!)?'
    r'(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))*'
    r'((a|b|rc)(0|[1-9][0-9]*))?'
    r'(\.post(0|[1-9][0-9]*))?'
    r'(\.dev(0|[1-9][0-9]*))?$'
)


def require_split_layout():
    """Refuse to run against a tree that does not have the split layout.

    This script (and the release workflow that calls it) also exists on `main`,
    because `workflow_dispatch` only offers a workflow that is present on the
    default branch — see the plan's step 15b. `main` still has the single flat
    `ably/` package, so a dispatch there must stop here with an explanation
    rather than a FileNotFoundError from the first version site it reads.

    On the split layout every path below exists, so this is a no-op.
    """
    missing = [
        str(path.relative_to(REPO_ROOT))
        for path in (CORE_PYPROJECT, SERVER_PYPROJECT)
        if not path.is_file()
    ]
    if missing:
        raise SystemExit(
            'pre-flight: this workflow releases the split distributions '
            '(ably-pubsub-core and ably-pubsub-server), but this ref still has the '
            'single `ably` layout — no ' + ' or '.join(missing) + '. There is nothing '
            'here to release in lockstep. Dispatch this workflow against a ref that '
            'has the split layout (--ref integration/v4, or a pubsub-split/* branch); '
            'releases of the legacy `ably` distribution are cut from its maintenance '
            'branch with that branch\'s own single-distribution release.yml.'
        )


class Failures:
    def __init__(self):
        self.messages = []

    def add(self, message):
        self.messages.append(message)

    def check(self, condition, message):
        if not condition:
            self.add(message)
        return bool(condition)


def read_scalar(path, pattern, what):
    """Read a single quoted scalar out of a file.

    Deliberately regex rather than tomllib/import: tomllib only arrived in 3.11,
    and importing the packages would make the pre-flight depend on them being
    installed rather than on what is actually in the tree about to be released.
    """
    match = re.search(pattern, path.read_text(), re.MULTILINE)
    if not match:
        raise SystemExit(f'pre-flight could not read {what} from {path}')
    return match.group(1)


def version_sites():
    return {
        f'{CORE_PYPROJECT.relative_to(REPO_ROOT)} [project] version':
            read_scalar(CORE_PYPROJECT, r'^version = "([^"]+)"', 'version'),
        f'{SERVER_PYPROJECT.relative_to(REPO_ROOT)} [project] version':
            read_scalar(SERVER_PYPROJECT, r'^version = "([^"]+)"', 'version'),
        f'{CORE_INIT.relative_to(REPO_ROOT)} lib_version':
            read_scalar(CORE_INIT, r"^lib_version = '([^']+)'", 'lib_version'),
        f'{SERVER_INIT.relative_to(REPO_ROOT)} __version__':
            read_scalar(SERVER_INIT, r"^__version__ = '([^']+)'", '__version__'),
    }


def core_pins():
    """Every `ably-pubsub-core[...]==<version>` pin in the server's pyproject."""
    text = SERVER_PYPROJECT.read_text()
    return set(re.findall(r'"ably-pubsub-core(?:\[[\w,]+\])?==([^"]+)"', text))


def core_extras():
    """The names in the core's `[project.optional-dependencies]` table."""
    text = CORE_PYPROJECT.read_text()
    section = text.split('[project.optional-dependencies]', 1)[1]
    section = re.split(r'^\[', section, maxsplit=1, flags=re.MULTILINE)[0]
    return re.findall(r'^(\w+) = \[', section, re.MULTILINE)


def check_versions(failures, expected):
    sites = version_sites()
    pins = core_pins()

    if expected is None:
        # No authoritative version: the sites only have to agree with each other,
        # and the first one is then taken as the release version for the rest.
        expected = sorted(sites.values())[0]

    failures.check(
        PEP_440.match(expected),
        f'version {expected!r} is not a valid PEP 440 public version',
    )

    for site, value in sorted(sites.items()):
        failures.check(value == expected, f'{site} is {value!r}, expected {expected!r}')

    failures.check(pins, 'no ably-pubsub-core== pin found in server/pyproject.toml')
    for pin in sorted(pins):
        failures.check(
            pin == expected,
            f'server/pyproject.toml pins ably-pubsub-core=={pin}, expected =={expected}',
        )

    # Every extra the core offers must be forwarded, or `pip install
    # ably-pubsub-server[crypto]` silently installs a core without the extra.
    server_text = SERVER_PYPROJECT.read_text()
    for extra in core_extras():
        failures.check(
            f'"ably-pubsub-core[{extra}]=={expected}"' in server_text,
            f'server/pyproject.toml does not forward the core extra {extra!r} at {expected}',
        )

    return expected


def one_of_each(failures, dist_dir, version):
    """Exactly one wheel and one sdist per distribution, at the release version."""
    found = {}
    for name in (CORE_DIST, SERVER_DIST):
        wheels = sorted(dist_dir.glob(f'{name}-*.whl'))
        sdists = sorted(dist_dir.glob(f'{name}-*.tar.gz'))
        failures.check(len(wheels) == 1, f'expected exactly one {name} wheel in {dist_dir}, found {len(wheels)}')
        failures.check(len(sdists) == 1, f'expected exactly one {name} sdist in {dist_dir}, found {len(sdists)}')
        for path in wheels + sdists:
            failures.check(
                f'-{version}' in path.name.replace(f'{name}', '', 1),
                f'{path.name} is not version {version}',
            )
        found[name] = (wheels[0] if wheels else None, sdists[0] if sdists else None)

    unexpected = sorted(
        p.name for p in dist_dir.iterdir()
        if p.suffix in {'.whl', '.gz'} and not p.name.startswith((CORE_DIST + '-', SERVER_DIST + '-'))
    )
    failures.check(not unexpected, f'unexpected files in {dist_dir}: {", ".join(unexpected)}')
    return found


def wheel_names(path):
    with zipfile.ZipFile(path) as zf:
        return set(zf.namelist())


def sdist_names(path):
    with tarfile.open(path) as tf:
        # Strip the `<name>-<version>/` prefix so paths compare like the wheel's.
        return {n.split('/', 1)[1] for n in tf.getnames() if '/' in n}


def check_artifacts(failures, dist_dir, version):
    found = one_of_each(failures, dist_dir, version)

    core_wheel, core_sdist = found[CORE_DIST]
    server_wheel, server_sdist = found[SERVER_DIST]

    # The generated sync flavour is not in git; a core built without running
    # unasync first looks fine until someone imports ably_pubsub.core.sync.
    if core_wheel:
        names = wheel_names(core_wheel)
        failures.check(
            any(n.startswith('ably_pubsub/core/sync/') for n in names),
            f'{core_wheel.name} does not contain ably_pubsub/core/sync/ (was unasync run?)',
        )
    if core_sdist:
        names = sdist_names(core_sdist)
        failures.check(
            any('ably_pubsub/core/sync/' in n for n in names),
            f'{core_sdist.name} does not contain ably_pubsub/core/sync/ (was unasync run?)',
        )

    # PEP 420: an __init__.py here would belong to whichever distribution shipped
    # it, so removing that one would delete the other's entry into the namespace.
    for wheel in (core_wheel, server_wheel):
        if wheel:
            failures.check(
                'ably_pubsub/__init__.py' not in wheel_names(wheel),
                f'{wheel.name} ships ably_pubsub/__init__.py; the namespace must stay PEP 420',
            )

    # Two wheels writing the same path into site-packages means installing one
    # overwrites the other and uninstalling either breaks what is left.
    if core_wheel and server_wheel:
        core_files = {n for n in wheel_names(core_wheel) if not n.endswith('/')}
        server_files = {n for n in wheel_names(server_wheel) if not n.endswith('/')}
        overlap = sorted(core_files & server_files)
        failures.check(not overlap, f'the two wheels both ship: {", ".join(overlap)}')

    # Both distributions must carry the licence they claim in their metadata.
    for path in (core_wheel, server_wheel):
        if path:
            failures.check(
                any(n.endswith('.dist-info/licenses/LICENSE') for n in wheel_names(path)),
                f'{path.name} does not bundle LICENSE',
            )
    for path in (core_sdist, server_sdist):
        if path:
            failures.check('LICENSE' in sdist_names(path), f'{path.name} does not bundle LICENSE')

    artifacts = sorted(
        str(p) for p in dist_dir.iterdir()
        if p.is_file() and (p.name.endswith('.whl') or p.name.endswith('.tar.gz'))
    )
    result = subprocess.run(
        [sys.executable, '-m', 'twine', 'check', *artifacts],
        capture_output=True,
        text=True,
    )
    sys.stdout.write(result.stdout)
    sys.stdout.write(result.stderr)
    failures.check(result.returncode == 0, 'twine check failed')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        '--version',
        help='the version being released (from the tag or the workflow_dispatch input). '
             'Without it the version sites only have to agree with each other.',
    )
    parser.add_argument(
        'dist',
        nargs='?',
        type=Path,
        help='directory holding the built distributions. Omit to check the version sites only.',
    )
    args = parser.parse_args(argv)

    require_split_layout()

    failures = Failures()
    version = check_versions(failures, args.version)

    if args.dist is not None:
        if not args.dist.is_dir():
            raise SystemExit(f'pre-flight: {args.dist} is not a directory')
        check_artifacts(failures, args.dist, version)

    if failures.messages:
        print(f'\nPre-flight FAILED ({len(failures.messages)} problem(s)); nothing should be published:\n',
              file=sys.stderr)
        for message in failures.messages:
            print(f'  - {message}', file=sys.stderr)
        return 1

    scope = 'version sites' if args.dist is None else f'version sites and the artifacts in {args.dist}'
    print(f'Pre-flight OK: {scope} all agree on {version}.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
