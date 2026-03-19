"""Build steps implementing helm3 based builds."""

from step_exec_lib.steps import BuildStepsFilteringPipeline

from app_build_suite.build_steps.chart_yaml_loader import ChartYamlLoader
from app_build_suite.build_steps.chart_yaml_writer import ChartYamlWriter
from app_build_suite.build_steps.giantswarm_helm_validator import GiantSwarmHelmValidator
from app_build_suite.build_steps.helm_builder_validator import HelmBuilderValidator
from app_build_suite.build_steps.helm_chart_builder import HelmChartBuilder
from app_build_suite.build_steps.helm_chart_metadata_builder import HelmChartMetadataBuilder
from app_build_suite.build_steps.helm_chart_metadata_finalizer import HelmChartMetadataFinalizer
from app_build_suite.build_steps.helm_chart_tool_linter import HelmChartToolLinter
from app_build_suite.build_steps.helm_chart_yaml_restorer import HelmChartYAMLRestorer
from app_build_suite.build_steps.helm_git_version_setter import HelmGitVersionSetter
from app_build_suite.build_steps.helm_home_url_setter import HelmHomeUrlSetter
from app_build_suite.build_steps.helm_requirements_updater import HelmRequirementsUpdater
from app_build_suite.build_steps.kube_linter import KubeLinter


class HelmBuildFilteringPipeline(BuildStepsFilteringPipeline):
    """
    Pipeline that combines all the steps required to use helm3 as a chart builder.
    """

    def __init__(self) -> None:
        super().__init__(
            [
                ChartYamlLoader(),
                HelmBuilderValidator(),
                HelmGitVersionSetter(),
                HelmHomeUrlSetter(),
                HelmChartMetadataBuilder(),
                ChartYamlWriter(),
                GiantSwarmHelmValidator(),
                HelmRequirementsUpdater(),
                HelmChartToolLinter(),
                KubeLinter(),
                HelmChartBuilder(),
                HelmChartMetadataFinalizer(),
                HelmChartYAMLRestorer(),
            ],
            "Helm 3 build engine options",
        )
