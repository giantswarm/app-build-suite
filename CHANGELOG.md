# Changelog

Based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), following [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/giantswarm/app-build-suite/compare/v0.1.5...HEAD
[0.1.5]: https://github.com/giantswarm/app-build-suite/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/giantswarm/app-build-suite/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/giantswarm/app-build-suite/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/giantswarm/app-build-suite/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/giantswarm/app-build-suite/releases/tag/v0.1.1
