import argparse
import os


class HasValuesSchema:

    _VALUES_SCHEMA_JSON = "values.schema.json"

    def validate(self, config: argparse.Namespace) -> bool:
        return os.path.exists(os.path.join(config.chart_dir, self._VALUES_SCHEMA_JSON))
