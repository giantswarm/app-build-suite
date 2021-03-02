# Changelog

Based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), following [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `icon` and `home` attributes are now copied over from `Chart.yaml` to metadata's `main.yaml`
- support for the [kube-linter](https://docs.kubelinter.io/) static chart verification tool

### Changed

- **breaking change**: the option `--ct-chart-repos` is now removed, because in `ct` command line options are
  overriding user supplied values in the `ct`'s config file. So far, `abs` was passing stable helm charts stable
  repo by default using command line argument. To fix compatibility with user-supplied `ct` config, `abs`
  stops passing `chart-repos` in command line, so if you need the stable helm charts repo to pass validation with
  `ct`, you're now responsible for creating the correct config file.
- in metadata files, `dateCreated` is now formatted the same way as in `index.yaml` created by helm
- update binary dependencies:
  - helm: 3.5.2
  - chart-test: 3.3.1
  - apptestctl: 0.7.0
  - docker: 20.10.3

### Fixed

- `compatibleProviders` is now added to `ct`'s schema file and is correctly validated
- remove not-yet-used test types from STEPS_ALL, which resulted in printing pointless steps as available
- change the simple HelmBuilderValidator build step to STEP_BUILD, so it's executed even when some steps other than
  STEP_BUILD are excluded from run
- remove redundant test-enabling options (`--enable-XYZ-tests`); use `--skip-steps` to exclude them
- change validation step name from 'test_validate' to 'validate' (it is not part of a test scenario)
- **breaking change** '--app-tests-deploy' was a flag, not a value option, but was described as a value option;
  changed to '--app-tests-skip-deploy'
- cluster reuse when no cluster config file is used was failing and requesting a new cluster anyway
- printing version - had "vvXYZ" double "v" prefix

## [0.1.7] - 2021-02-03

### Changed

- Remove capturing of external processes stdout and stderr - they are now printed live by the process itself.

## [0.1.6] - 2021-02-03

### Fixed

- Do not fail if `replace-chart-version-with-git` nor `replace-app-version-with-git` config options are specified.
- Do not try to create the App CR if it already exists.
- Do not try to remove the App CR if app deployment was skipped.
- Handle Chart.lock file if it exists and `replace-chart-version-with-git` is specified.

### Added

- Each command executed is now printed to stdout. If '--debug' is enabled, also full stdout and stderr of each command
  executed is printed

## [0.1.5] - 2021-01-15

### Changes

- Breaking: `step_unit` name was misleading, renamed now to `step_validate`
- fix: loading the config file from the root of current working dir. Note: you can safely add `chart-dir` option to the config file, if the file is placed in work dir root

## [0.1.4] - 2021-01-14

- fixed release process to correctly attach `dabs.sh` as build artefact

## [0.1.3] - 2021-01-14

- `kind` is now supported as an internal cluster creation mechanism

## [0.1.2] - 2021-01-07

### Added

- Update `apptestctl` dependency to 0.6.0

## [0.1.1] - 2020-12-22

Initial release

- added: metadata includes now `annotations` and `chartApiVersion` fields
- changed:
  - versions skip the leading 'v' now if it was present in git tag (backward compatible naming)
  - config file is loaded from `.abs/main.yaml`, not from `.abs.yaml` (for future needs)
- testing basic classes and pipelines

[Unreleased]: https://github.com/giantswarm/app-build-suite/compare/v0.1.7...HEAD
[0.1.7]: https://github.com/giantswarm/app-build-suite/compare/v0.1.6...v0.1.7
[0.1.6]: https://github.com/giantswarm/app-build-suite/compare/v0.1.5...v0.1.6
[0.1.5]: https://github.com/giantswarm/app-build-suite/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/giantswarm/app-build-suite/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/giantswarm/app-build-suite/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/giantswarm/app-build-suite/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/giantswarm/app-build-suite/releases/tag/v0.1.1
