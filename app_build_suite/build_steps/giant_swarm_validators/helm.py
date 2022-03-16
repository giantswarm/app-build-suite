import argparse
import os

from app_build_suite.build_steps.helm_consts import VALUES_SCHEMA_JSON


class HasValuesSchema:
    def validate(self, config: argparse.Namespace) -> bool:
        return os.path.exists(os.path.join(config.chart_dir, VALUES_SCHEMA_JSON))
