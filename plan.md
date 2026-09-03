# ably-python → ably-pubsub-python: PubSub package split plan

Execution plan for applying PDR-091b (PubSub package split, major releases) to the Python SDK.

**Sources of truth:**
- [PDR-091: SDK naming and MAU classification](https://ably.atlassian.net/wiki/spaces/product/pages/5220106242) — parent, DECIDED IN PRINCIPLE. Device/server split, factory doors, agent header as the declaration mechanism. Calls out that Python's agent string is hardcoded and "needs small core changes first".
- [PDR-091b companion: PubSub package split (major releases)](https://ably.atlassian.net/wiki/spaces/product/pages/5362810886) — DECIDED. New majors on a new `pubsub-core`, not thin wrappers; repo renames; old packages "not touched at all" and EOL after one year; PyPI trusted publisher must be rebound at the rename.
- [PDR-091b2: Per-SDK rollout plan v2](https://ably.atlassian.net/wiki/spaces/product/pages/5348425729) — IN REVIEW. Python section: "Repo: ably-python → ably-pubsub-python. New package: ably-pubsub-server. Factory doors: create_http_client(...), create_realtime_client(...)". Owner field is blank. The agent-identifier convention (per-language family rename + cross-SDK versionless side flags) is Umair's footer comment on this page (2026-09-02).
- [PDR-091c companion: high-level SDKs stay unified](https://ably.atlassian.net/wiki/spaces/product/pages/5363499015) — DECIDED. No high-level Python SDKs exist today, so the only consequence here is that core must be able to expose a supported types subset if one ever appears.
- [PDR-091d companion: public API renaming](https://ably.atlassian.net/wiki/spaces/product/pages/5363957781) — **IN REVIEW** (steps marked ⚠️091d are conditional on it being decided).
- [SDK device/server split — step sequence doc](https://docs.google.com/document/d/1r96vOSOft1yT84NxbdpCh0IomTwzIpKskQ-wA5e28M0) — the 12-step order this plan follows.
- Reference implementations: [ably-js#2293](https://github.com/ably/ably-js/pull/2293) (split, MERGED to `integration/v3`), [#2294](https://github.com/ably/ably-js/pull/2294) (UTS per side), [#2296](https://github.com/ably/ably-js/pull/2296) (lockstep release), [#2297](https://github.com/ably/ably-js/pull/2297) (versionless side flags + `ably-pubsub-js` identifier); [ably-ruby#453/#454/#455/#457](https://github.com/ably/ably-ruby/pulls) and `Git/ably-ruby/plan.md` (server-only sibling, furthest along).
- Agent registry: [ably-common#361](https://github.com/ably/ably-common/pull/361) — **OPEN** as of 2026-09-03. Registers `ably-pubsub-server`/`ably-pubsub-device` (versionless flags) and `ably-pubsub-python` (versioned family). Today's registry has `ably-python` only.
- Infra prerequisite: [infrastructure#13005](https://github.com/ably/infrastructure/pull/13005) — **MERGED 2026-09-01**; `ably-sdk-builds-ably-pubsub-python` IAM role exists (the `ably-python` role stays).
- Prior attempt in this repo: [ably-python#681](https://github.com/ably/ably-python/pull/681) (`server-device-split`, OPEN) — the thin-wrapper shape PDR-091a **declined**. See step 9 for what to salvage and why it is closed rather than merged.

**What Python ships (per PDR-091b2):** Python is a **server-only** SDK. One new public distribution, `ably-pubsub-server`, built on a new `ably-pubsub-core` distribution. **No device package.** Factory doors: `create_http_client(...)` and `create_realtime_client(...)`, plus a sync flavour of the HTTP door (today's `ably.sync` REST client has no realtime counterpart). Repo renamed `ably-python` → `ably-pubsub-python` (direct rename — PyPI identity is not tied to the repo URL, so the ably-go/ably-cocoa copy-first exception does not apply). Today's `ably` distribution (currently 3.1.2) enters a 1-year maintenance window, then EOL.

**Current repo facts the plan relies on (verified 2026-09-03):**
- Single flat-layout package `ably/` with hatchling; version lives in two places (`pyproject.toml` and `lib_version` in `ably/__init__.py`); the `/release` skill bumps both.
- `ably/sync/**` and `test/ably/sync/**` are **generated**, not committed (`.gitignore`), by `uv run unasync` (`ably/scripts/unasync.py`), which rewrites `ably` → `ably.sync` imports and renames `AblyRest`→`AblyRestSync` etc. CI and the release build both run it; `release.yml` asserts `ably/sync/` is in the wheel and sdist.
- Agent string is hardcoded in one place — `HttpUtils.default_headers()` (`ably/http/httputils.py:45`): `ably-python/<lib_version> python/<runtime>` — and the websocket transport reuses those headers (`ably/transport/websockettransport.py:81`). There is **no `agents` client option**. `test/ably/rest/resthttp_test.py:187` asserts the exact current shape.
- `release.yml` is tag-triggered (`v*`), builds one distribution, publishes to TestPyPI on every run and to PyPI (project `ably`) on tags via **trusted publishing** bound to `ably/ably-python` + `release.yml` + GitHub environment `pypi`. So, unlike Ruby, **the legacy package's releases also break at the rename** until the `ably` project's publisher is re-pointed.
- `features.yml` uploads via `ably/features` with `repository-name: ably-python` (OIDC → per-repo IAM role). No docs workflow.
- `requires-python = ">=3.7"` but CI tests 3.8–3.14; 3.7 and 3.8 are EOL upstream.
- PyPI names `ably-pubsub-core`, `ably-pubsub-server` (and `-device`) all return 404 — unclaimed.

---

## Phase 0 — Decisions and prerequisites (before writing code)

1. **Confirm distribution names and claim them on PyPI.** Names: `ably-pubsub-core` (summary/description must state it is an internal implementation package for Ably's own packages, not for direct external use) and `ably-pubsub-server`. Both verified unclaimed (2026-09-03). PyPI has no reservation feature, but it has **pending trusted publishers**: a publisher can be registered for a not-yet-existing project name, and the first OIDC upload creates the project. Claim the names **through the release workflow** (step 15b), not by hand: register pending publishers for both names, put a placeholder version (e.g. `0.0.1a0`, PEP 440 pre-release so `pip install` never picks it up by default) on a throwaway branch, dispatch the workflow at it. That one run claims both names and proves the OIDC exchange, the core→server ordering and the skip-existing re-run guardrail. **DECIDED 2026-09-03: rename first, then claim.** Pending publishers bind to owner + repo name, so the claim happens immediately after step 17 against `ably/ably-pubsub-python` and is never rebound. Accepted risk: the names stay exposed until the rename window; if squatting is observed, fall back to claiming early and re-creating the two publisher entries post-rename. Do not delete the placeholder release until a real version exists. Add the SDK-team owners to both new projects once they exist.
   - **Account access:** find who owns the `ably` PyPI project (its maintainers list on pypi.org) and where the credentials live (SDK Team / 1Password); the same account needs to create the pending publishers and later re-point the `ably` project's publisher (step 25).
2. **Import namespace — DECIDED 2026-09-03: `ably_pubsub` (PEP 420 namespace).** This is the Python-specific decision that Ruby and JS did not have. The legacy `ably` distribution owns the top-level `ably/` import package (a regular package with `__init__.py`). If `ably-pubsub-core` also shipped `ably/`, pip would install both file sets into the same directory: installing one overwrites the other's files and uninstalling either deletes shared files, silently corrupting any environment that has both during migration (one venv serving two services, or a transitive dependency still on `ably`). PDR-091b also says the old package is "not re-exported or reused". Proposal:
   - New top-level import package **`ably_pubsub`**, a PEP 420 namespace package shared by the two distributions: `ably-pubsub-core` ships `ably_pubsub/core/**` (today's `ably/**`, moved), `ably-pubsub-server` ships `ably_pubsub/server/**`. Neither ships `ably_pubsub/__init__.py`.
   - Public usage: `from ably_pubsub.server import create_http_client, create_realtime_client`; sync flavour `from ably_pubsub.server.sync import create_http_client`. Core types consumers need are re-exported from `ably_pubsub.server` (step 10), so nobody imports `ably_pubsub.core` directly.
   - Rejected: keeping `ably` as the core's import name (clobbers the legacy dist, and is the 091a wrapper shape); `ably.pubsub.server` inside the `ably` package (PR #681's layout — same problem, and it requires `ably` itself to be the core).
   - Record the decision in PDR-091b2's ably-python section; it drives the migration guide's import mapping.
3. **Factory-door surface — DECIDED 2026-09-03: mirror the constructor kwargs, plus a sync HTTP door.** Record it in PDR-091b2 and fill in the blank Owner field. Each factory takes exactly the keyword arguments the constructor it wraps takes today, so nothing is lost in translation (an options-object-first signature like ably-js/ruby was considered and rejected as un-Pythonic and a larger migration):
   - `ably_pubsub.server.create_http_client(key=None, token=None, token_details=None, **options)` → HTTP (REST) client
   - `ably_pubsub.server.create_realtime_client(key=None, loop=None, **options)` → realtime client (asyncio, as today)
   - `ably_pubsub.server.sync.create_http_client(key=None, token=None, token_details=None, **options)` → synchronous HTTP client (today's `ably.sync.AblyRestSync`)
   These are the only documented entry points of the new package. Python is the only SDK with a generated sync flavour, so say explicitly in b2 that the sync door exists and that there is no sync realtime door.
4. **New major version — DECIDED 2026-09-03: `4.0.0`, lockstep.** Current distribution is 3.1.2; core + server both start at `4.0.0` and release in lockstep forever after (ably-js keeps one version across core/device/server; ably-ruby the same). The server distribution pins `ably-pubsub-core==4.0.0` exactly. (Starting fresh at 1.0.0 was rejected: it reads as a downgrade next to `ably` 3.x.)
5. **Python floor and extras — DECIDED 2026-09-03: `requires-python = ">=3.8"`** for both new distributions, aligning metadata with what CI already tests (drops only the `python_version=='3.7'` dependency branches; the `'3.8'` branches and the `mock`/`async-case` shims stay). Extras: `crypto` and `vcdiff` forward from server to core (`ably-pubsub-core[crypto]==4.0.0`). **`oldcrypto` (pycrypto) is ported as-is for now**; its removal is folded into the 091d deprecated-surface deletion list (step 18) rather than decided here.
6. **⚠️091d — DECIDED 2026-09-03: build on current names, rename last.** Phases 2–5 use `AblyRest`/`AblyRealtime`; if PDR-091d is approved, the new packages ship `HttpClient`/`RealtimeClient` (etc.), `ably_pubsub.core.rest` becomes `ably_pubsub.core.http`, and deprecated surface is deleted rather than ported — as one final mechanical PR (Phase 6, step 18) so nothing else blocks on the DR and the restructure diff stays reviewable. Renaming up-front, or deciding now to skip the rename regardless, were both rejected.
7. **Register the agent identifiers.** Both strings Python will send must be in the ably-common registry before any prerelease ships them: the versionless side flag `ably-pubsub-server` and the versioned family identifier `ably-pubsub-python` (source = the renamed repo). Both are in ably-common#361, which is OPEN — track it to merge; if it stalls, split the Python entries into their own PR. The `-server` suffix is load-bearing: realtime grants the MAU server exemption on API-key auth by matching an agent entry ending in `-server`. Then bump the `submodules/` (ably-common) pin in this repo.
8. **Get the MAU pricing release date** from the project hub — it drives the GA target and the forcing-function messaging in the migration guide.
9. **PR #681 — DECIDED 2026-09-03: leave open for now; revisit when the first integration-branch PR opens.** It implements the 091a thin-wrapper shape (`ably` stays the public core; `ably-pubsub-server` adds `ably.pubsub.server` into the `ably` package; `AblyRest`/`AblyRealtime` gain a `DeprecationWarning`). 091b forbids all three: the old package is "not touched at all", nothing is re-exported from it, and the new packages are built on a new core — so it will not merge as-is. Salvage into Phase 2–4 rather than lose: the factory signatures and docstrings, the hand-written `sync.py` door, the unasync exclusion pattern, the packaging-invariant tests (`test/unit/pubsub_packaging_test.py`), the re-export parity test, and the one-upload lockstep release shape in its `release.yml`. Once the restructure PR (step 11) is up, close #681 with a pointer to it so two competing shapes are not visible to the team at once.

## Phase 1 — Open the integration branch

10. Create a long-lived **`integration/v4`** branch off `main` (this repo's precedent is `integration/realtime` for the 2.0 work; ably-js uses `integration/v3`, ably-ruby `integration/v2`). All split work lands there as **stacked PRs**; nothing ships from it until Phase 7. Apply the same branch protection/required checks as `main`. (Note: `.github/workflows/*.yml` trigger on `pull_request` regardless of base, so PRs into the integration branch get CI for free; `push:` triggers only list `main`, add `integration/v4` so the merged state is also checked.)
10b. **The PR stack.** Mirror the ably-js (#2293 → #2294 → #2296 → #2297) and ably-ruby (#453 → #454; #455/#457 straight to `main`) shape: each PR is based on the one before it so they review independently and merge in order into `integration/v4`; the two workflow/rename PRs go to `main` directly because they must exist on the default branch to be useful. Branch names `pubsub-split/<topic>` as in ably-ruby.

    | # | Branch | Base | Contents | Plan steps |
    | --- | --- | --- | --- | --- |
    | 1 | `pubsub-split/restructure` | `integration/v4` | uv workspace, `core/` + `server/` layout, `git mv ably/** → core/src/ably_pubsub/core`, unasync/ruff/pytest path updates, factory doors + re-exports, `agents` option + identifier rename + side stamping, test suite moved, agent assertions, packaging-invariant tests | 11, 12, 13, 14, 14b, 14c |
    | 2 | `pubsub-split/release-tooling` | PR 1's branch | lockstep `release.yml` (pre-flight, core-then-server, skip-existing, dispatch input), `release-dry-run` job in `check.yml`, `/release` skill for three version sites, `CONTRIBUTING.md` release sections | 15, 15b, 16 |
    | 3 | `pubsub-split/release-workflow-on-main` | **`main`** | cherry-pick of PR 2's `release.yml` only, so `workflow_dispatch` works against integration refs (inert on main: pre-flight refuses its single-dist state) | 15b |
    | 4 | `pubsub-split/rename-references` | **`main`** | `features.yml` repository-name, pyproject URLs, README/CONTRIBUTING/capabilities links; merged in the rename freeze window, then merged forward into `integration/v4` | 17 |
    | 5 | `pubsub-split/docs` | PR 2's branch | README rewrite, `UPDATING.md` 3.x→4.0 migration section, per-dist READMEs, `CHANGELOG.md` 4.0.0 entry | 19, 20 |
    | 6 | `pubsub-split/api-rename` (⚠️091d) | PR 5's branch | `AblyRest`→`HttpClient` etc., deprecated-surface deletions, unasync rename list, test/doc updates — opened only once 091d is decided | 18 |

    Rules for the stack: PR 1 is big by nature (a `git mv` of the whole tree) — keep the *behavioural* changes (agent option, factory doors) in separate commits from the move so reviewers can diff each. Each PR's description links the plan step it implements, as the ably-js PRs do. When a lower PR merges into `integration/v4`, retarget the next one at `integration/v4`. Merge `main` into `integration/v4` after PRs 3 and 4 land so the branch carries the workflow and rename changes. Periodically merge `main` forward (ruby's `a057dcce` pattern) so the integration branch never drifts far from released fixes.

## Phase 2 — Repo restructure: core + server distributions

11. **Restructure the repo into a two-distribution uv workspace**, e.g.:
    ```
    pyproject.toml            # workspace root only: [tool.uv.workspace] members = ["core", "server"];
                              # dev deps, pytest/ruff config, no [project] that publishes
    core/
      pyproject.toml          # name = "ably-pubsub-core"; hatch wheel packages = ["src/ably_pubsub"]
      src/ably_pubsub/core/   # today's ably/** moves here with `git mv` so history follows
        __init__.py           # api_version, lib_version, public re-exports (as ably/__init__.py today)
        scripts/unasync.py    # generator, paths updated; [project.scripts] unasync stays here
        sync/                 # GENERATED, still gitignored
    server/
      pyproject.toml          # name = "ably-pubsub-server"; dependencies = ["ably-pubsub-core==<version>"]
      src/ably_pubsub/server/
        __init__.py           # factory doors + enumerated re-exports; __version__
        sync.py               # sync HTTP door (hand-written, not generated)
    test/                     # stays at root, runs against both workspace members
    ```
    - No `ably_pubsub/__init__.py` anywhere (PEP 420). Editable installs of both members merge the namespace, so the root test suite imports `ably_pubsub.core` and `ably_pubsub.server` from one venv.
    - The server pyproject declares a **pinned, exact-version** dependency on the core (`ably-pubsub-core==4.0.0`) — the analogue of ably-js's exact `peerDependencies`, enforcing lockstep and preventing two core versions. Locally, `[tool.uv.sources] ably-pubsub-core = { workspace = true }` resolves it to the checkout.
    - Delete the root `[project] name = "ably"`; the `ably` distribution is never published from this branch again (fixes ship from the maintenance branch, Phase 8). `LONG_DESCRIPTION.rst` goes (each dist gets its own README as `readme`).
    - Keep `lib_version` and the two pyproject versions as the version sites (three now); the `/release` skill and the release pre-flight (step 15) know all three. While editing the skill, fix its CHANGELOG links, which point at `ably-java`.
    - `unasync`: source rule becomes `core/src/ably_pubsub/core` → `core/src/ably_pubsub/core/sync`, import rewrite `ably_pubsub.core` → `ably_pubsub.core.sync`; exclude `server/` from generation (its sync door is hand-written). Test rules follow the moved paths. Ruff `extend-exclude` updated for the new generated paths.
    - Packaging checks move with it: the wheel/sdist must contain `ably_pubsub/core/sync/`, and **must not** contain `ably_pubsub/__init__.py`.
12. **Implement the factory doors in `ably-pubsub-server`.** Each factory:
    - Accepts everything today's constructor accepts (same keyword signature — reuse core's existing key/token/token_details disambiguation rather than duplicating it).
    - Stamps the versionless side-declaring agent entry `ably-pubsub-server` (see step 13) via the new `agents` option and constructs the core client.
    - Re-exports the core types consumers need to reference (clients, channel/presence/message types, `ChannelOptions`, `CipherParams`, `Capability`, `TokenDetails`, exceptions — start from today's `ably/__init__.py` export list) so consumers never import `ably_pubsub.core` directly, mirroring ably-js's enumerated `core-exports`. Enumerate; don't star-import.
    - The sync door does the same against the generated `ably_pubsub.core.sync` module.
13. **Agent plumbing.** Rework the hardcoded header to match the ably-js contract (`packages/shared/side.ts` / `getAgentString`) and the convention in ably-common#361:
    - Add an additive **`agents: dict[str, str | None]`** client option in `Options`. `HttpUtils.default_headers()` takes the options and renders each entry as `name/version`, or a bare `name` when the version is `None` (a flag, like `browser`). Both HTTP requests and the websocket handshake already share this one function, so there is a single seam.
    - Rename the family identifier `ably-python` → **`ably-pubsub-python`** (versioned with `lib_version`) — on the integration branch, before any prerelease, so even prerelease traffic partitions cleanly from legacy `ably-python/*` traffic. The maintenance branch keeps `ably-python`.
    - The server factory appends `ably-pubsub-server` with `None` (per ably-common#361 the side entry carries no version — the `ably-pubsub-python/x.y.z` entry beside it does). Target wire shape: `ably-pubsub-python/4.0.0 python/3.12.1 ably-pubsub-server`.
    - The side entry is applied last and wins any collision on its own identifier — the side is the package's to declare, not the caller's. Caller-supplied `agents` entries (a layered SDK's attribution) are preserved.
    - The `-server` suffix must never be renamed without preserving the suffix (billing classifies by it). Put a comment saying exactly that where the identifier constant is defined, as ably-js and ably-ruby do.

## Phase 3 — Tests and conformance

14. Rework the test suite to the new layout: `test/unit` and `test/ably/**` import from `ably_pubsub.core`; add factory-door tests for the server package (async, realtime, sync). Keep the existing check matrix green (3.8–3.14 per step 5; × JSON/msgpack via the existing `VaryByProtocolTestsMetaclass`; × async/generated sync). Run the full sandbox suite from the integration branch. Update `.ably/capabilities.yaml` ("Agent Identifier: Agents" becomes true) and the `features.yml` job for the new layout.
14b. **Add explicit agent assertions that fail loudly** (this is what billing reads):
    - `create_http_client`: the `Ably-Agent` request header contains the versionless `ably-pubsub-server` token and the `ably-pubsub-python/<lib_version>` token, and **no** `ably-pubsub-server/<anything>` form (the `name/None` regression ably-js#2297 guards against).
    - `create_realtime_client`: the websocket handshake headers carry the same (assert on the headers the transport passes to `websockets.connect`, and on a live sandbox connection).
    - The sync door produces the same header.
    - Caller-supplied agent entries survive; the side entry cannot be overridden by the caller.
    - Rewrite `test/ably/rest/resthttp_test.py:187`'s regex for the new family identifier (RSC7d).
14c. **Add packaging-invariant tests** (adapted from PR #681's `test/unit/pubsub_packaging_test.py`): no `ably_pubsub/__init__.py` in either source tree; the two wheels' file lists don't overlap; the three version sites and the server→core pin agree; server extras forward to the core at the same pinned version; `ably_pubsub.server.__all__` matches what it re-exports. The release dry-run (step 15b) checks the built artifacts, but nothing else asserts package contents, and a namespace mistake would otherwise surface only after publish.

## Phase 4 — Release tooling: lockstep + auto-publishing

15. **Rework `release.yml` into a lockstep release of both distributions** (PyPI trusted publishing is already in place for `ably`; this is the "consistent auto-publishing" PDR-091b calls for):
    - Build both distributions into one `dist/` (`uv build --package ably-pubsub-core` / `--package ably-pubsub-server`, after `uv run unasync`).
    - **Pre-flight before anything is uploaded:** the tag/dispatch version equals all three version sites and the server's exact core pin; exactly one wheel + one sdist per distribution; `ably_pubsub/core/sync/` present in the core artifacts; `ably_pubsub/__init__.py` absent from both; `twine check` passes.
    - Publish **core first, then server**, as two explicit `pypa/gh-action-pypi-publish` steps with `skip-existing: true`, so a run that failed between the two is completed by re-running it (PyPI has no cross-project transaction, so make the partial state re-runnable rather than pretending it is impossible). PyPI's OIDC token covers every project that trusts the same publisher config, so one job with one `id-token: write` publishes both.
    - Keep the TestPyPI publish on every run as the staging step for both names (needs pending publishers on test.pypi.org too; the existing `[[tool.uv.index]] experimental` index already points there for the consumer-side check in step 21).
    - Keep the `pypi` GitHub environment's required-reviewer approval gate.
15b. **Make the workflow dispatchable and testable early.** Add `workflow_dispatch` with a `version` input alongside the tag trigger, and a `release-dry-run` job in `check.yml` that runs the same pre-flight and builds both distributions on every PR, so version-site/pin regressions surface continuously. `workflow_dispatch` only works once the workflow file exists on the **default branch** — and this work merges to `integration/v4` until Phase 7 — so **cherry-pick `release.yml` to `main` early** (as ably-ruby#455 did): it is inert there (its pre-flight refuses main's single-distribution state) and enables `gh workflow run release.yml --ref <branch>` against integration refs. Then use it for the name claim (step 1) and deliberately test the guardrails: re-run the same version (both skipped as already published) and dispatch a mismatched version (pre-flight aborts with nothing uploaded).
16. **Configure trusted publishers on pypi.org (and test.pypi.org)** for both new projects, bound to `ably/ably-pubsub-python` + `release.yml` + environment `pypi`. Per step 1 this happens **immediately after the rename** (step 17), so the binding is made once against the new name and the placeholder claim run doubles as the binding test. Rewrite `CONTRIBUTING.md`'s two release-process sections for the new flow (one tag → both distributions; no manual `github_changelog_generator` path).

## Phase 5 — Repo rename and publishing rebind

17. **Rename the repo `ably-python` → `ably-pubsub-python`** (direct rename; GitHub redirects cover clones and web links). The IAM prerequisite (infrastructure#13005) is merged, so this can happen any time — the natural slot is after the restructure and release-tooling PRs merge to `integration/v4`, coordinated with the programme's cross-SDK rename freeze window (check with Evgenii whether renames are batched), and before the trusted-publisher setup. Announce the freeze window to the SDK team first. In the same pass, update internal references:
    - `.github/workflows/features.yml`: `repository-name: ably-python` → `ably-pubsub-python` (selects the new `ably-sdk-builds-ably-pubsub-python` role).
    - `core/pyproject.toml` and `server/pyproject.toml` `[project.urls]`, README badges/links (PyPI badge now `ably-pubsub-server`), `CONTRIBUTING.md`, `.ably/capabilities.yaml` links, the `/release` skill's URLs. Leave historic `CHANGELOG.md` links alone (redirects cover them).
    - **Re-point the legacy `ably` project's trusted publisher** on PyPI (and TestPyPI) to `ably/ably-pubsub-python` — otherwise the first 3.x maintenance release fails. This is the one rebind Ruby did not need.
    - **Never recreate a repo named `ably/ably-python` afterwards.** A new repo under the old name destroys GitHub's redirect for every existing clone and link. Python is a direct-rename SDK (the maintenance branch lives in the renamed repo), so the old name stays vacant forever — worth stating in the rollout notes since ably-go/ably-cocoa deliberately do the opposite.
    - **Done when:** clone and web redirects verified (`git ls-remote` on an existing checkout, plus web URLs for the repo, a PR, and a file permalink), CI fully green post-rename (full `check.yml` matrix + lint), `features.yml` runs clean with the new repository-name **and its upload lands** (proves the new IAM role — this failure mode is otherwise silent), and a TestPyPI publish from the workflow succeeds under the new binding.

## Phase 6 — Public API pass (⚠️091d) — last change on the integration branch

18. **This is deliberately the final code change before the integration branch merges**, gated on PDR-091d being approved — everything in Phases 2–5 is built and kept green on the current names, then this lands as one mechanical pass on top:
    - Rename `AblyRest` → `HttpClient`, `AblyRealtime` → `RealtimeClient`; `ably_pubsub.core.rest.*` → `ably_pubsub.core.http.*` (`rest.channel.Channel` → `HttpChannel`/`HttpChannels`, `rest.auth`, `rest.push`, `rest.annotations` follow); `RealtimeChannel` stays. Update `unasync.py`'s `rename_classes` list and the `Sync` suffix mapping accordingly (`HttpClientSync`).
    - Produce the Python deprecated-surface deletion list and delete rather than port. Known candidates today: the `environment`, `rest_host`, `realtime_host` client options (deprecated in 3.0 in favour of `endpoint`, per `UPDATING.md`), the `oldcrypto` extra (pycrypto, unmaintained since 2013 — deferred here from step 5), and the `Undocumented` constructor kwargs if the owner agrees. Anything already deprecated in 3.x is a deletion candidate by default; keeping it requires a stated reason. Nothing not currently deprecated is silently dropped.
    - Re-run the full Phase 3 pass (including the agent assertions and generated sync flavour) after the rename.
    - Record the full old-name → new-name table in PDR-091b2's Python section (it feeds the migration guide, step 20).
    - If 091d is **declined**, skip this phase and ship the surface as-is (factories return `AblyRest`/`AblyRealtime`). If it is **still undecided** when the rest of the branch is done, escalate to the programme before merging: renaming later would cost another major, so the merge/GA date and the 091d decision need to be reconciled explicitly rather than defaulted.

## Phase 7 — Docs, prerelease, GA

19. Rewrite `README.md` for the new packages: `pip install ably-pubsub-server`, factory-door quickstarts (async realtime, async HTTP, sync HTTP), explicit statement that `ably-pubsub-core` is internal; each distribution gets a short README that PyPI renders. Drop the "Full Realtime support unavailable" section, which is stale.
20. **Migration guide** (`UPDATING.md`, new top section "3.x (`ably`) → 4.0.0 (`ably-pubsub-server`)"): machine-applicable mapping table — `pip install ably` → `pip install ably-pubsub-server`; `from ably import AblyRest` / `AblyRest(key=...)` → `from ably_pubsub.server import create_http_client` / `create_http_client(key=...)`; `AblyRealtime(...)` → `create_realtime_client(...)`; `from ably.sync import AblyRestSync` → `from ably_pubsub.server.sync import create_http_client`; type imports `from ably import X` → `from ably_pubsub.server import X`; ⚠️091d renames and the deleted-API list if applicable. State the MAU forcing function and the EOL date. All samples rewritten onto the new package; LLM-facing docs regenerated (coordinate with the docs team's cross-SDK pass).
21. **Prerelease** (`4.0.0rc1`, PEP 440 — never installed by default) of both distributions via the workflow — proves the lockstep pipeline and both trusted-publisher bindings end-to-end before GA. Include a consumer-side check the workflow itself cannot do: in a clean container, `pip install ably-pubsub-server==4.0.0rc1` (no `--pre`, exact pin), import it, create a client, and assert the `Ably-Agent` value — proving the exact core pin resolves from the public index and the published artifact works. Also verify `pip install ably-pubsub-server` **alongside** `ably==3.1.2` in one venv leaves both importable (the step 2 rationale).
22. **Merge `integration/v4` to `main`.** New development continues on main under the renamed repo.
23. **GA release, lockstep, coordinated.** Core + server at the frozen version, released in the org-wide coordinated window with the other SDKs (rollout date is set by the programme, keyed to the MAU pricing date — do not GA unilaterally).

## Phase 8 — Maintenance window for the old `ably` distribution

24. Cut a maintenance branch from the last 3.x release tag (`v3.1.2`; naming TBC org-wide, e.g. `maintenance/3.x`) **before** the integration merge lands on main. The `ably` distribution's future security/critical fixes are released from this branch only, still tag-triggered through its own (unchanged, single-distribution) `release.yml`. No new features, **no `DeprecationWarning` on the constructors, and no runtime side-detection is ever added** — 091b says the existing packages are "not touched at all"; once MAU pricing is live the old constructors are rejected server-side, which is the intended forcing function. Its agent string stays `ably-python/3.x`.
25. Confirm the legacy `ably` PyPI project's trusted publisher points at the renamed repo (step 17) and cut a trivial patch release from the maintenance branch to prove it — a rebind mistake found at the first real security fix is the worst time to find it.
26. Publish the support policy: README banner + CHANGELOG entry on the maintenance branch and on main stating maintenance-only status, the EOL date (GA date + 1 year), and a link to the migration guide. Update the `ably` project's PyPI description/README to say the same, and set its `Development Status` classifier to `7 - Inactive` at EOL. In ably-common, add the sunset for `ably-python` (all versions) at the EOL date so the registry carries it.

---

## Cross-cutting checklist

- [ ] Distribution names claimed on PyPI via the workflow, after the rename (step 1); SDK-team owners added
- [x] Import namespace `ably_pubsub` (PEP 420) decided 2026-09-03 (step 2) — [ ] recorded in PDR-091b2
- [x] Factory-door signatures incl. sync door decided 2026-09-03 (step 3) — [ ] Owner field filled and surface recorded in PDR-091b2
- [x] Version `4.0.0`, floor `>=3.8`, `oldcrypto` deferred to 091d list — decided 2026-09-03 (steps 4, 5) — [ ] recorded in PDR-091b2
- [ ] `ably-pubsub-server` + `ably-pubsub-python` present in ably-common registry; submodule bumped (step 7; ably-common#361)
- [ ] MAU release date known; GA window agreed with programme (steps 8, 23)
- [ ] PR #681 closed with pointer once the restructure PR is open; salvage items landed (step 9)
- [ ] ⚠️091d outcome tracked; Phase 6 executed, skipped, or escalated accordingly (step 18)
- [ ] Agent assertions in CI fail loudly, incl. the no-`name/None` regression (step 14b)
- [ ] Lockstep release proven via `4.0.0rc1` and the clean-container install check (step 21)
- [ ] Post-rename: redirects, CI, features upload (IAM), both new trusted publishers **and the legacy `ably` publisher** verified (steps 17, 25)
- [ ] Maintenance branch + EOL policy published; registry sunset added (steps 24–26)

## Sequencing notes / risks

- **Order matters at the rename:** rename → workflow/metadata reference updates → trusted-publisher (re)binds for three PyPI projects (`ably-pubsub-core`, `ably-pubsub-server`, legacy `ably`) → verify features upload and a TestPyPI publish, all in one freeze window, or releases and the S3 upload fail (the latter silently).
- **The agent-registry PR (step 7) is the only step worth doing immediately**; the PyPI name claim (step 1) is decided to follow the rename so the publisher binding is made once. Everything else flows through the integration branch. Because the names stay unclaimed until the rename window, keep an eye on pypi.org for squatting and fall back to claim-first if it appears.
- **Namespace clobbering is the Python-specific trap.** The new core must not ship an `ably/` import package, and neither new distribution may ship `ably_pubsub/__init__.py`. The packaging tests (14c) and the release pre-flight (15) both assert this; the clean-container side-by-side install (21) proves it against the real index.
- **PyPI has no cross-project atomic upload.** Lockstep is enforced by pre-flight (nothing uploads unless everything agrees) plus core-before-server ordering plus `skip-existing` re-runs, not by a transaction. Say so in `CONTRIBUTING.md`.
- **Legacy releases use OIDC too.** Unlike RubyGems (manual API key), the `ably` project's trusted publisher is bound to the old repo name; forgetting to re-point it only shows up at the next security fix (step 25 exists to catch this early).
- **Generated sync code** runs through every phase: the restructure must keep `unasync` working (paths, import rewrite, class-rename list under ⚠️091d), and the sync door is hand-written so it must be kept in step with the async one by test, not by generation.
- **Python has no device package**, so there is no shared "side" helper across two packages; keep the agent-stamping logic in one place in the server package regardless, with the suffix warning comment.
- The current metadata advertises Python 3.7 while CI tests 3.8+; step 5 aligns the floor to `>=3.8` for 4.0. Raising it further (3.8 is EOL upstream) would be another breaking change, so if that is wanted it should ride this major — revisit before Phase 7 if the owner changes their mind.
