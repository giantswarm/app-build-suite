from dependency_injector import containers, providers

from app_build_suite.build_steps.helm import HelmBuildPipeline


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    builder = providers.Selector(
        config.build_engine, helm3=providers.Singleton(HelmBuildPipeline)
    )
