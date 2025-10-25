"""
Example workflows demonstrating invalid CRON schedules
These will be rejected by the schedule processor with warnings
"""

from bifrost import workflow, ExecutionContext


# Example 1: Invalid CRON syntax (7 fields instead of 5)
@workflow(
    name="invalid_cron_syntax",
    description="Invalid CRON Syntax Example",
    schedule="* * * * * * *",  # 7 fields - invalid!
    execution_mode="async",
    category="Testing"
)
async def invalid_cron_syntax(context: ExecutionContext):
    """This workflow will never run - invalid CRON syntax"""
    return {"status": "should_not_execute"}


# Example 2: Too frequent (every minute)
@workflow(
    name="too_frequent_schedule",
    description="Too Frequent Schedule Example",
    schedule="* * * * *",  # Every minute - too frequent!
    execution_mode="async",
    category="Testing"
)
async def too_frequent_schedule(context: ExecutionContext):
    """This workflow will log a warning - runs too frequently"""
    return {"status": "executing_too_frequently"}


# Example 3: Every 30 seconds (invalid - sub-minute)
@workflow(
    name="sub_minute_schedule",
    description="Sub-Minute Schedule Example",
    schedule="*/30 * * * * *",  # Every 30 seconds - invalid!
    execution_mode="async",
    category="Testing"
)
async def sub_minute_schedule(context: ExecutionContext):
    """This workflow will never run - sub-minute schedules not supported"""
    return {"status": "should_not_execute"}
