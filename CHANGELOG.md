# Changelog

Based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), following [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]

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

[Unreleased]: https://github.com/giantswarm/app-build-suite/compare/v0.1.2...HEAD
[0.1.2]: https://github.com/giantswarm/app-build-suite/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/giantswarm/app-build-suite/releases/tag/v0.1.1
