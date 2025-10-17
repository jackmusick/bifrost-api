"""
Test Execution Scenarios
Example workflows for testing execution refactor features:
1. Terminating errors (ensure proper error handling)
2. Massive logs (test blob storage)
3. HTML result (test result rendering)
"""

from bifrost import workflow


@workflow(
    name="test_terminating_error",
    description="Test workflow that throws a terminating error to verify error handling",
    category="Testing"
)
async def test_terminating_error(context):
    """
    Throws an exception to test that:
    1. The execution is properly marked as Failed
    2. The error message is captured
    3. The execution never gets stuck in Running status
    """
    context.info("Starting terminating error test")
    context.info("This workflow will intentionally fail...")

    # Simulate some work before the error
    context.debug("Doing some work before the error")

    # Throw terminating error
    raise ValueError(
        "This is a test terminating error! The execution should be marked as Failed.")


@workflow(
    name="test_massive_logs",
    description="Test workflow that generates massive logs to verify blob storage",
    category="Testing"
)
async def test_massive_logs(context):
    """
    Generates 1000+ log entries to test:
    1. Logs are stored in blob storage (not in table column)
    2. Logs are retrieved and displayed correctly in UI
    3. Performance is acceptable with large log volumes
    """
    context.info("Starting massive logs test")
    context.info("Generating 1000 log entries...")

    # Generate lots of logs
    for i in range(1000):
        if i % 100 == 0:
            context.info(f"Progress: {i}/1000 logs generated")
        elif i % 50 == 0:
            context.warning(f"Checkpoint at log {i}")
        elif i % 10 == 0:
            context.debug(f"Debug log entry {i}", data={
                              "iteration": i, "timestamp": "2025-01-01"})
        else:
            context.debug(f"Log entry {i}")

    context.info("All 1000 logs generated successfully!")

    return {
        "success": True,
        "totalLogs": 1000,
        "message": "Massive logs test completed. Check the logs tab to see all entries."
    }


@workflow(
    name="test_html_result",
    description="Test workflow that returns a pretty HTML result for user-facing display",
    category="Testing"
)
async def test_html_result(context):
    """
    Returns formatted HTML to test:
    1. HTML results are rendered correctly in UI
    2. Styling works properly
    3. Tables, lists, and formatting display nicely
    """
    context.info("Starting HTML result test")
    context.info("Generating user-facing HTML report...")

    # Generate a pretty HTML report using Tailwind classes
    html_result = """
    <div>
        <h1 class="text-3xl font-bold text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400 pb-2">
            🎉 User Onboarding Report
        </h1>

        <div class="bg-blue-50 dark:bg-blue-950 border-l-4 border-blue-600 dark:border-blue-400 p-4 my-4 rounded">
            <p class="m-0 text-sm text-blue-900 dark:text-blue-100">
                <strong>Status:</strong> <span class="text-green-600 dark:text-green-400">✅ Completed Successfully</span>
            </p>
        </div>

        <h2 class="text-2xl font-semibold mt-6 mb-2">Summary</h2>
        <p class="mb-4 text-foreground">Successfully onboarded <strong>5 new users</strong> to the organization.</p>

        <h2 class="text-2xl font-semibold mt-6 mb-2">Users Created</h2>
        <table class="w-full border-collapse my-4">
            <thead>
                <tr class="bg-muted">
                    <th class="border border-border p-3 text-left">Name</th>
                    <th class="border border-border p-3 text-left">Email</th>
                    <th class="border border-border p-3 text-left">Status</th>
                </tr>
            </thead>
            <tbody class="text-foreground">
                <tr>
                    <td class="border border-border p-3">John Doe</td>
                    <td class="border border-border p-3">john.doe@example.com</td>
                    <td class="border border-border p-3">
                        <span class="text-green-600 dark:text-green-400">✅ Active</span>
                    </td>
                </tr>
                <tr>
                    <td class="border border-border p-3">Jane Smith</td>
                    <td class="border border-border p-3">jane.smith@example.com</td>
                    <td class="border border-border p-3">
                        <span class="text-green-600 dark:text-green-400">✅ Active</span>
                    </td>
                </tr>
                <tr>
                    <td class="border border-border p-3">Bob Johnson</td>
                    <td class="border border-border p-3">bob.johnson@example.com</td>
                    <td class="border border-border p-3">
                        <span class="text-green-600 dark:text-green-400">✅ Active</span>
                    </td>
                </tr>
                <tr>
                    <td class="border border-border p-3">Alice Williams</td>
                    <td class="border border-border p-3">alice.williams@example.com</td>
                    <td class="border border-border p-3">
                        <span class="text-yellow-600 dark:text-yellow-400">⏳ Pending</span>
                    </td>
                </tr>
                <tr>
                    <td class="border border-border p-3">Charlie Brown</td>
                    <td class="border border-border p-3">charlie.brown@example.com</td>
                    <td class="border border-border p-3">
                        <span class="text-yellow-600 dark:text-yellow-400">⏳ Pending</span>
                    </td>
                </tr>
            </tbody>
        </table>

        <h2 class="text-2xl font-semibold mt-6 mb-2">Actions Completed</h2>
        <ul class="space-y-1 mb-4 text-foreground">
            <li>✅ Created Azure AD accounts</li>
            <li>✅ Assigned Microsoft 365 licenses</li>
            <li>✅ Added users to default Teams channels</li>
            <li>✅ Sent welcome emails with login instructions</li>
            <li>✅ Created user profile pages</li>
        </ul>

        <div class="bg-yellow-50 dark:bg-yellow-950 border-l-4 border-yellow-600 dark:border-yellow-400 p-4 my-6 rounded">
            <p class="m-0 text-sm text-yellow-900 dark:text-yellow-100">
                <strong>⚠️ Note:</strong> 2 users are pending activation. They will receive activation emails within 24 hours.
            </p>
        </div>

        <h2 class="text-2xl font-semibold mt-6 mb-2">Next Steps</h2>
        <ol class="space-y-1 mb-4 list-decimal list-inside text-foreground">
            <li>Monitor pending user activations</li>
            <li>Follow up with users who haven't completed setup</li>
            <li>Schedule onboarding training session</li>
        </ol>

        <hr class="border-t border-border my-8">

        <p class="text-xs text-muted-foreground">
            <em>Report generated on January 17, 2025 at 3:45 PM</em>
        </p>
    </div>
    """

    context.info("HTML report generated successfully")

    # Return the HTML string directly
    # The execution logger will detect it starts with < and set resultType='html'
    return html_result
