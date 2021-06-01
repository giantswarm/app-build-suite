from step_exec_lib.types import StepType, STEP_ALL

STEP_BUILD = StepType("build")
STEP_METADATA = StepType("metadata")
STEP_VALIDATE = StepType("validate")
STEP_STATIC_CHECK = StepType("static_check")
ALL_STEPS = {
    STEP_ALL,
    STEP_BUILD,
    STEP_METADATA,
    STEP_VALIDATE,
    STEP_STATIC_CHECK,
}
