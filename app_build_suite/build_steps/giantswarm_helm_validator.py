"""Build step: runs Giant Swarm-specific Helm chart validators."""

import argparse
import inspect
import logging
import os
from importlib import import_module
from os import listdir
from typing import List, Protocol, Set, Tuple, Type, runtime_checkable

import configargparse
from step_exec_lib.errors import ValidationError
from step_exec_lib.steps import BuildStep
from step_exec_lib.types import Context, StepType

from app_build_suite.build_steps.steps import STEP_VALIDATE

logger = logging.getLogger(__name__)


@runtime_checkable
class GiantSwarmValidator(Protocol):
    """This class is only used for type hinting of simple giant_swarm_validators below"""

    def validate(self, config: argparse.Namespace) -> bool: ...  # noqa: E704

    def get_check_code(self) -> str: ...  # noqa: E704


class GiantSwarmHelmValidator(BuildStep):
    """
    Validator that checks Helm Chart compliance according to Giant Swarm internal rules.
    """

    @property
    def steps_provided(self) -> Set[StepType]:
        return {STEP_VALIDATE}

    def initialize_config(self, config_parser: configargparse.ArgParser) -> None:
        config_parser.add_argument(
            "-g",
            "--disable-giantswarm-helm-validator",
            required=False,
            default=False,
            action="store_true",
            help="Should Giant Swarm specific validation be enabled",
        )
        config_parser.add_argument(
            "-s",
            "--disable-strict-giantswarm-validator",
            required=False,
            default=False,
            action="store_true",
            help="If strict mode is disabled, the build won't fail when a validation rule fails; otherwise, a WARN is "
            "given",
        )
        config_parser.add_argument(
            "--giantswarm-validator-ignored-checks",
            required=False,
            default="",
            help="Comma-separated list of Giant Swarm validation checks to ignore even if they fail",
        )

    def pre_run(self, config: argparse.Namespace) -> None:
        """Runs a set of Giant Swarm specific validations."""
        if config.disable_giantswarm_helm_validator:
            logger.debug("Not running Giant Swarm specific chart validation.")
            return

        gs_validators = self._load_giant_swarm_validators()

        ignore_list: List[str] = []
        ignore_str_list: List[str] = config.giantswarm_validator_ignored_checks.split(",")
        for name in ignore_str_list:
            n = name.strip()
            if n:
                ignore_list.append(n)

        for validator in gs_validators:
            validator_name = type(validator).__name__
            logger.info(f"Running Giant Swarm validator '{validator.get_check_code()}: {validator_name}'.")
            if validator.validate(config):
                logger.debug(f"Giant Swarm validator '{validator.get_check_code()}: {validator_name}' is OK.")
            else:
                msg = f"Giant Swarm validator '{validator.get_check_code()}: {validator_name}' failed its checks."
                if not config.disable_strict_giantswarm_validator and validator.get_check_code() not in ignore_list:
                    raise ValidationError(self.name, msg)
                else:
                    logger.warning(msg)

    def _load_giant_swarm_validators(self) -> List[GiantSwarmValidator]:
        gs_validators: List[GiantSwarmValidator] = []
        current_frame = inspect.currentframe()
        if current_frame is None:
            raise ValidationError(self.name, "Can't check current frame and detect current module's path.")

        cur_mod_path = os.path.dirname(os.path.abspath(inspect.getfile(current_frame)))
        validators_mod_path = os.path.join(cur_mod_path, "giant_swarm_validators")

        cur_mod_name = __name__
        validators_mod_name_prefix = cur_mod_name.replace("giantswarm_helm_validator", "giant_swarm_validators.")

        name_class_tuples: List[Tuple[str, Type]] = []

        for modname in listdir(validators_mod_path):
            if not modname.endswith(".py"):
                continue

            pkg = import_module(validators_mod_name_prefix + modname[:-3])
            name_class_tuples = name_class_tuples + inspect.getmembers(pkg, inspect.isclass)

        for _, cls in name_class_tuples:
            if isinstance(cls, type) and issubclass(cls, GiantSwarmValidator):
                new_validator = cls()
                if new_validator.get_check_code() in (c.get_check_code() for c in gs_validators):
                    raise ValidationError(
                        self.name,
                        f"Found more than 1 Giant Swarm validator with check code "
                        f"'{new_validator.get_check_code()}'. Check codes have to be unique.",
                    )
                gs_validators.append(new_validator)

        return gs_validators

    def run(self, config: argparse.Namespace, context: Context) -> None:
        pass
