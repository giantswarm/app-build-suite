"""This is a module that just hosts dependency injection elements."""
from dependency_injector import containers, providers

from app_build_suite.build_steps.helm import HelmBuildPipeline


class ComponentsContainer(containers.DeclarativeContainer):
    """
    A dependency injection container for easily switching build or test runtimes.
    """

    config = providers.Configuration()

    builder = providers.Selector(
        config.build_engine, helm3=providers.Singleton(HelmBuildPipeline)
    )
