from abc import ABC

from app_build_suite.build_steps.base_test_runner import (
    BaseTestRunnersFilteringPipeline,
    TestInfoProvider,
    BaseTestRunner,
    FunctionalTestRunner,
)


class PytestTestFilteringPipeline(BaseTestRunnersFilteringPipeline):
    def __init__(self):
        super().__init__(
            [
                TestInfoProvider(),
                PytestFunctionalTestRunner(self._cluster_manager),
            ],
            "Pytest test options",
        )


class PytestTestRunner(BaseTestRunner, ABC):
    def run_tests(self):
        pass


class PytestFunctionalTestRunner(FunctionalTestRunner, PytestTestRunner):
    pass
