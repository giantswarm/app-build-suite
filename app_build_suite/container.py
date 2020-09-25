from dependency_injector import containers, providers

from app_build_suite.build_steps import HelmGitVersionSetter, HelmBuilderValidator


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    git_version_info = providers.Factory()

    validator = providers.Selector(
        config.build_engine, helm3=providers.Singleton(HelmBuilderValidator)
    )

    version_setter = providers.Selector(
        config.build_engine, helm3=providers.Singleton(HelmGitVersionSetter)
    )
