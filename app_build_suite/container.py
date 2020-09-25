from dependency_injector import containers, providers

from app_build_suite.build_steps import HelmGitVersionSetter, HelmBuilderValidator


class Container(containers.DeclarativeContainer):
    validator = providers.Selector(
        lambda: "helm", helm=providers.Singleton(HelmBuilderValidator)
    )

    version_setter = providers.Selector(
        lambda: "helm", helm=providers.Singleton(HelmGitVersionSetter)
    )
