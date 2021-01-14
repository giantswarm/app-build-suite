from typing import NewType

TestType = NewType("TestType", str)

TEST_SMOKE = TestType("smoke")
TEST_FUNCTIONAL = TestType("functional")
TEST_PERFORMANCE = TestType("performance")
TEST_COMPATIBILITY = TestType("compatibility")
TEST_TYPE_ALL = [TEST_SMOKE, TEST_FUNCTIONAL]


def config_option_cluster_type_for_test_type(test_type: TestType) -> str:
    return f"--{test_type}-tests-cluster-type"
