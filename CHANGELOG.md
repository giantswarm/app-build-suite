# Changelog

Based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), following [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]

- added: metadata includes now `annotations` and `chartApiVersion` fields
- changed:
  - versions skip the leading 'v' now if it was present in git tag (backward compatible naming)
- **breaking change**:
  - config file is now loaded from `.abs/main.yaml`, not from `.abs.yaml` (for future needs)

### added

- Initial commit
