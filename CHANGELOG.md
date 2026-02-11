# Changelog

Based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), following
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Automatic `home` field management in Chart.yaml from git remote URL
  - New `HelmHomeUrlSetter` build step sets `home` to git origin URL (GitHub only)
  - Converts SSH URLs (`git@github.com:org/repo`) to HTTPS format
  - Enabled by default, disable with `--disable-home-url-auto-update`
  - Adds field if missing, updates if present

## 1.6.0 - 2026-01-29

- feat: validate `.name` in `Chart.yaml` to be RFC 1123 compliant to avoid problems when using it in chart
  templated values

## 1.5.2 - 2026-01-19

- fix: create correct GitHub URLs for non-tagged builds

## [1.5.1] - 2025-12-18

### Changed

- update helm to 3.19.4

## [1.5.0] - 2025-12-10

### Changed

- Update architect-orb in CircleCI config to v6.8.0
- switch project from pipenv to uv

### Fixed

- A case where there are no annotations in Chart.yaml is now correctly handled

## [1.3.0] - 2025-10-30

### Added

- Add Github CLI and [gh-token](https://github.com/Link-/gh-token) to Circle CI executor container image

## [1.2.10] - 2025-10-28

### Changed

- Update conftest to [v0.63.0](https://github.com/open-policy-agent/conftest/releases/tag/v0.63.0)
- Update helm/chart-testing to v3.14.0

### Added

- Add `curl` and `jq` to CircleCI image.
- Add `libatomic1` to test runner image as a dependency to `pre-commit`.

## [1.2.9] - 2025-08-05

### Changed

- Update conftest to v0.62.0
- Update helm to v3.18.4
- Update kubelinter to v0.7.5

## 1.2.8 - 2024-12-03

- fix: bug in the release process set wrong version in the code in the container

## 1.2.7 - 2024-12-03

- added: the git tag detection logic from `step-exec-lib` was moved here
- fixed: support for tags with pre-release part, like `1.2.3-gs1`

## 1.2.6 - 2024-10-24

- fix python 3.12 references

## [1.2.5] - 2024-10-08

- fix for: upgrade `step-exec-lib` to v0.2.4 to use all tags, not only annotated

## [1.2.4] - 2024-10-08

- upgrade `step-exec-lib` to v0.2.4 to use all tags, not only annotated

## [1.2.3] - 2024-10-08

- update dependencies:
    - step-exec-lib to v0.2.2 to fix the bug with incorrect git tag discovery
    - generic python update to 3.12

## [1.2.2] - 2023-12-03

- Fixes:
    - `kubectl` was missing from upstream image
    - only `.yaml` extension was accepted for the config file (now `.yml` is fine as well)

## [1.2.0] - 2023-10-17

- Added
    - Add icon exists and has correct aspect ratio validation

- Changed
    - Updated team annotation to set a default value in example
    - Updated dependencies for shared `push-to-app-catalog` GitHub Workflow

## [1.1.5] - 2023-07-20

- Changed
    - Updated python dependencies

## [1.1.4] - 2022-12-07

- Added
    - Add support for default teams in team annotation to support chart dependencies.
- Changed
    - Remove timestamp, module name, and level from log template

## [1.1.3] - 2022-11-17

- Changed
    - added support for the `default` team label value in validation

## [1.1.2] - 2022-03-25

- Fixed
    - Giant Swarm validator config options were not really working

## [1.1.1] - 2022-03-24

- Added
    - Add `push-to-app-catalog` GitHub Action
    - `GiantSwarmHelmValidator` - executes Giant Swarm specific validation rules

- Changed
    - Enabling `kube-linter` verbose output by default
    - Upgrade Helm to 3.8.1
    - Upgrade python to 3.10.3
    - Upgrade chart-testing to 3.5.1
    - Upgrade kube-linter to 0.2.5

## [1.0.4] - 2021-09-21

- Changed
    - Upgrade Helm to 3.7.0

## [1.0.3] - 2021-09-16

- Changed
    - Upgrade python version in container image to 3.8.12
    - Upgrade conftest version in container to 0.27.0

## [1.0.2] - 2021-08-10

- Changed
    - Giant Swarm metadata generator supports now the `upstreamChartVersion` field in `Chart.yaml`. This field
      has to be specified if `upstreamChartUrl` is present.

## [1.0.1] - 2021-06-29

- Changed
    - Breaking change: the build and test functionality is now split into 2 projects. The build part is left
      here in this project, the test part is now a separate project called
      [`app-test-suite`](https://github.com/giantswarm/app-test-suite).

## [0.2.3] - 2021-05-24

- Changed
    - Update our derived chart schema for chart-testing ahead of a chart-testing release to fix issues with
      local subcharts requiring a `repository` field.
    - All dependencies updated, including:
        - python dependencies
        - pre-commit dependencies
        - binaries in docker image:
            - `helm` 3.5.4
            - `kubectl` 1.20.7
            - `ct` 3.4.0
            - `apptestctl` 0.8.0
            - `kube-linter` 0.2.2

## [0.2.2] - 2021-03-23

- Added
    - Support for `requirements.lock` file updating

## [0.2.1] - 2021-03-02

- Added
    - `icon` and `home` attributes are now copied over from `Chart.yaml` to metadata's `main.yaml`
    - support for the [kube-linter](https://docs.kubelinter.io/) static chart verification tool

- Changed
    - **breaking change**: the option `--ct-chart-repos` is now removed, because in `ct` command line options
      are overriding user supplied values in the `ct`'s config file. So far, `abs` was passing stable helm
      charts stable repo by default using command line argument. To fix compatibility with user-supplied `ct`
      config, `abs` stops passing `chart-repos` in command line, so if you need the stable helm charts repo to
      pass validation with `ct`, you're now responsible for creating the correct config file.
    - in metadata files, `dateCreated` is now formatted the same way as in `index.yaml` created by helm
    - update binary dependencies:
        - helm: 3.5.2
        - chart-test: 3.3.1
        - apptestctl: 0.7.0
        - docker: 20.10.3

- Fixed
    - `compatibleProviders` is now added to `ct`'s schema file and is correctly validated
    - remove not-yet-used test types from STEPS_ALL, which resulted in printing pointless steps as available
    - change the simple HelmBuilderValidator build step to STEP_BUILD, so it's executed even when some steps
      other than STEP_BUILD are excluded from run
    - remove redundant test-enabling options (`--enable-XYZ-tests`); use `--skip-steps` to exclude them
    - change validation step name from 'test_validate' to 'validate' (it is not part of a test scenario)
    - **breaking change** '--app-tests-deploy' was a flag, not a value option, but was described as a value
      option; changed to '--app-tests-skip-deploy'
    - cluster reuse when no cluster config file is used was failing and requesting a new cluster anyway
    - printing version - had "vvXYZ" double "v" prefix

## [0.1.7] - 2021-02-03

- Changed
    - Remove capturing of external processes stdout and stderr - they are now printed live by the process
      itself.

## [0.1.6] - 2021-02-03

- Fixed
    - Do not fail if `replace-chart-version-with-git` nor `replace-app-version-with-git` config options are
      specified.
    - Do not try to create the App CR if it already exists.
    - Do not try to remove the App CR if app deployment was skipped.
    - Handle Chart.lock file if it exists and `replace-chart-version-with-git` is specified.

- Added
    - Each command executed is now printed to stdout. If '--debug' is enabled, also full stdout and stderr of
      each command executed is printed

## [0.1.5] - 2021-01-15

- Changes
    - Breaking: `step_unit` name was misleading, renamed now to `step_validate`
    - fix: loading the config file from the root of current working dir. Note: you can safely add `chart-dir`
      option to the config file, if the file is placed in work dir root

## [0.1.4] - 2021-01-14

- fixed release process to correctly attach `dabs.sh` as build artefact

## [0.1.3] - 2021-01-14

- `kind` is now supported as an internal cluster creation mechanism

## [0.1.2] - 2021-01-07

- Added
    - Update `apptestctl` dependency to 0.6.0

## [0.1.1] - 2020-12-22

Initial release

- added: metadata includes now `annotations` and `chartApiVersion` fields
- changed:
    - versions skip the leading 'v' now if it was present in git tag (backward compatible naming)
    - config file is loaded from `.abs/main.yaml`, not from `.abs.yaml` (for future needs)
- testing basic classes and pipelines

[Unreleased]: https://github.com/giantswarm/app-build-suite/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/giantswarm/app-build-suite/compare/v1.2.10...v1.3.0
[1.2.10]: https://github.com/giantswarm/app-build-suite/compare/v1.2.9...v1.2.10
[1.2.9]: https://github.com/giantswarm/app-build-suite/compare/v1.2.0...v1.2.9
[1.2.0]: https://github.com/giantswarm/app-build-suite/compare/v1.1.4...v1.2.0
[1.1.5]: https://github.com/giantswarm/app-build-suite/compare/v1.1.4...v1.1.5
[1.1.4]: https://github.com/giantswarm/app-build-suite/compare/v1.0.4...v1.1.4
[1.0.4]: https://github.com/giantswarm/app-build-suite/compare/v1.0.3...v1.0.4
[1.0.3]: https://github.com/giantswarm/app-build-suite/compare/v1.0.2...v1.0.3
[1.0.2]: https://github.com/giantswarm/app-build-suite/compare/v1.0.1...v1.0.2
[1.0.1]: https://github.com/giantswarm/app-build-suite/compare/v0.2.3...v1.0.1
[0.2.3]: https://github.com/giantswarm/app-build-suite/compare/v0.2.2...v0.2.3
[0.2.2]: https://github.com/giantswarm/app-build-suite/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/giantswarm/app-build-suite/compare/v0.1.7...v0.2.1
[0.1.7]: https://github.com/giantswarm/app-build-suite/compare/v0.1.6...v0.1.7
[0.1.6]: https://github.com/giantswarm/app-build-suite/compare/v0.1.5...v0.1.6
[0.1.5]: https://github.com/giantswarm/app-build-suite/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/giantswarm/app-build-suite/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/giantswarm/app-build-suite/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/giantswarm/app-build-suite/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/giantswarm/app-build-suite/releases/tag/v0.1.1
