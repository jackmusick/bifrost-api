# Getting Started

Welcome to Bifrost Integrations - an open-source automation platform built to democratize best-in-class tooling for the Integration Services industry.

## Table of Contents

-   [What is Bifrost Integrations?](#what-is-bifrost-integrations)
-   [Quick Start](#quick-start)
-   [Key Concepts](#key-concepts)
-   [Your First Workflow](#your-first-workflow)
-   [Common Use Cases](#common-use-cases)
-   [Next Steps](#next-steps)

---

## What is Bifrost Integrations?

Bifrost Integrations is an open-source automation platform designed to democratize best-in-class tooling for the emerging Integration Services industry - before venture capital gets the chance to own something we're all incredibly passionate about: solving problems with automation.

Built by someone with nearly 20 years of MSP experience and a deep passion for scaling solutions for the industry and its customers, this platform addresses a fundamental gap in the market. Just as early PSA and RMM tools transformed managed services, the Integration Services industry needs purpose-built tooling that truly scales automation. Existing RPA platforms are great for rapid development and provide helpful abstractions like OAuth, storage, and monitoring, but they cannot and will not keep pace with AI-powered development and have always been constrained by limitations that traditional programming languages do not have.

Bifrost Integrations removes those limitations while preserving the light management layer that makes RPA tools valuable - abstracting OAuth workflows, monitoring, configuration, and secret management. It's architected with multi-tenancy at its core, enabling you to scale your Integration Services business without duplicating work across customers. This is not another RPA tool trying to be everything to everyone; it's a platform designed specifically to help you build scalable automation businesses the right way.

### What You Can Do with Bifrost Integrations

**Develop with Your Favorite Tools**

-   Use VS Code, Claude Code, and Git for version control
-   Build with Python and modern development workflows
-   Test locally before deploying to production

**Build Reusable Integrations**

-   Create integration modules for common platforms (NinjaOne, HaloPSA, Pax8, Microsoft CSP)
-   Abstract authentication, pagination, and API complexity
-   Share functionality across all your workflows

**Centralized Connection Management**

-   Automated OAuth refresh flows
-   Key/value configuration storage per organization
-   Secure secrets management with Azure Key Vault

**Dynamic Forms and Workflows**

-   Create flexible forms for you and your customers
-   Build context-aware workflows that adapt based on organization and user
-   Generate form inputs programmatically from data providers

**Multi-Tenant Architecture**

-   Scope functionality globally or to specific organizations
-   Deliver value to customers without code duplication or redeployment
-   Complete data isolation between tenants

### Why Bifrost Integrations Exists

Traditional RPA tools lower the barrier to entry but fall short when you need the full power of a programming language, version control, modern development practices, and AI-assisted workflows. Meanwhile, no one is building a platform truly designed to scale automation in the way early PSA and RMM tools scaled managed services.

Bifrost Integrations bridges this gap by giving you the power and flexibility of code with the convenience of RPA-style abstractions - all in an open-source package that you control. It's built to ensure the next chapter of Integration Services doesn't get ravaged by venture capitalists who prioritize extraction over value creation.

### For the Non-Developer

With AI coding tools, proper instructions, a thriving community, and training, it's never been easier to build powerful automations. Traditional RPA tools still require you to understand programming primitives like loops, variables, and conditional logic - they had their own syntax you needed to learn. While Bifrost Integrations may require a slightly higher initial investment to get started, the combination of AI-assisted development and a platform that abstracts the dangerous complexities (authentication, secrets management, API security) means the ceiling is dramatically higher.

AI tools like Claude Code, GitHub Copilot, and GPT Codex can help you:

-   Write workflows from natural language descriptions
-   Debug errors and explain what code is doing
-   Suggest improvements and optimizations
-   Generate boilerplate code for common patterns

The platform handles the hard parts - OAuth flows, credential encryption, multi-tenant isolation, and API authentication - so you can focus on solving business problems. With the right guidance and AI assistance, you can build automations that would have required a full development team just a few years ago, enabling limitless possibilities for your Integration Services business.

---

## Quick Start

### Prerequisites

-   Python 3.11 or higher
-   Azure Functions Core Tools (v4.x)
-   Git

### Installation

This section is a WIP. The intention is that you can deploy the full environment to a resource group in Microsoft Azure. Since the platform runs on nearly-free services, your run costs should be less than $20.00/month.

---

## Key Concepts

### Scope

Items inside the platform can be scoped either globally or by organization. Some examples:

-   Execution History
-   Key/value configuration
-   OAuth Connections
-   Secrets

When a person executes a workflow directly (Platform Admins only) or via a Form, the triggering code has access to this scope and can make decisions based on it. In addition, `get_config` and `get_oauth_connection` will automatically retrieve information from the executor's organization or globally if it doesn't exist. This way you can create matching configurations, secrets and OAuth providers for multiple customers, or just set it globally.

### Decorators

Bifrost Integrations uses Python decorators to define workflows, parameters, and data providers. These decorators register your functions with the platform and automatically generate forms, validation, and API endpoints.

**Important:** The `@workflow` and `@data_provider` decorators serve different purposes and should not be combined on the same function:

-   Use `@workflow` for executable automation logic
-   Use `@data_provider` for functions that return dropdown options

While technically possible to apply both decorators to the same function, this would be confusing and is not recommended. Keep workflows and data providers as separate, focused functions.

#### @workflow Decorator

The `@workflow` decorator registers a function as an executable workflow in the platform.

```python
@workflow(
    # Identity
    name="user_onboarding",                    # Unique identifier (snake_case)
    description="Onboard new M365 user",       # Human-readable description
    category="user_management",                # Category for organization
    tags=["m365", "user"],                     # Optional tags for filtering

    # Execution
    execution_mode="sync",                     # "sync" | "async" | "scheduled"
    timeout_seconds=300,                       # Max execution time (default: 300)

    # Scheduling (optional)
    schedule="0 9 * * 1",                      # Cron expression for scheduled workflows

    # Access Control
    requires_org=True,                         # Requires organization context (default: True)
    expose_in_forms=True,                      # Show in UI forms (default: True)
    requires_approval=False,                   # Requires approval before execution
    required_permission="canExecuteWorkflows"  # Permission required to execute
)
async def onboard_user(context: OrganizationContext, ...):
    # Workflow implementation
    pass
```

**Common Parameters:**

-   `name`: Unique workflow identifier (snake_case, required)
-   `description`: Human-readable description (required)
-   `category`: Category for organization (default: "General")
-   `execution_mode`: "sync" (immediate), "async" (background), or "scheduled" (cron)
-   `schedule`: Cron expression for scheduled workflows (e.g., "0 9 \* \* 1" = Mondays at 9 AM)
-   `timeout_seconds`: Maximum execution time before timeout (default: 300)

#### @param Decorator

The `@param` decorator defines input parameters for workflows with automatic validation and form generation.

```python
@param(
    name="email",                              # Parameter name (must match function arg)
    type="email",                              # Parameter type
    label="Email Address",                     # Display label for UI
    required=True,                             # Is this parameter required?
    validation={"pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"},
    data_provider="get_available_domains",     # Dynamic options from data provider
    default_value="user@example.com",          # Default value
    help_text="User's email address"           # Help text for UI
)
```

**Valid Parameter Types:**

-   `string`: Text input
-   `int`: Integer number
-   `float`: Decimal number
-   `bool`: True/False checkbox
-   `email`: Email address (with validation)
-   `json`: JSON object
-   `list`: Array of values

**Validation Options:**

-   `pattern`: Regular expression for string validation
-   `min`/`max`: Range validation for numbers
-   `min_length`/`max_length`: Length validation for strings

**Example with Multiple Parameters:**

```python
@workflow(name="create_user", description="Create new user", category="user_management")
@param("first_name", type="string", label="First Name", required=True)
@param("last_name", type="string", label="Last Name", required=True)
@param("email", type="email", label="Email", required=True)
@param("license", type="string", label="License", data_provider="get_available_licenses")
@param("send_welcome", type="bool", label="Send Welcome Email", default_value=True)
async def create_user(context, first_name, last_name, email, license, send_welcome=True):
    # Implementation
    pass
```

#### @data_provider Decorator

The `@data_provider` decorator creates functions that return dynamic options for form dropdowns.

```python
@data_provider(
    name="get_available_licenses",             # Unique identifier (snake_case)
    description="Returns available M365 licenses",
    category="m365",                           # Category for organization
    cache_ttl_seconds=300                      # Cache for 5 minutes
)
async def get_available_licenses(context: OrganizationContext):
    """Get list of available Microsoft 365 licenses."""

    # Could fetch from Microsoft Graph API
    # graph = context.get_integration('msgraph')
    # skus = await graph.subscribed_skus.get()

    return [
        {
            "label": "Microsoft 365 E3",       # Display text
            "value": "SPE_E3",                 # Value passed to workflow
            "metadata": {                      # Optional metadata
                "available": 20,
                "total": 50
            }
        },
        {
            "label": "Microsoft 365 E5",
            "value": "SPE_E5",
            "metadata": {"available": 3, "total": 5}
        }
    ]
```

**Data Provider Response Format:**
Each item in the returned list should have:

-   `label` (required): Display text shown in UI
-   `value` (required): Value passed to the workflow
-   `metadata` (optional): Additional data (shown in UI tooltips)

### Context

The `OrganizationContext` object is passed to every workflow and provides access to organization data, configuration, secrets, and integrations.

#### Organization Properties

```python
# Organization information
context.org_id          # Organization ID (e.g., "acme-corp")
context.org_name        # Organization display name (e.g., "Acme Corporation")
context.tenant_id       # Microsoft 365 tenant ID (if linked)

# Execution metadata
context.execution_id         # Unique execution ID
context.executed_by          # User ID who triggered execution
context.executed_by_email    # Email of triggering user
context.executed_by_name     # Display name of triggering user
```

#### Configuration Access

```python
# Get organization-specific configuration (with global fallback)
api_url = context.get_config("api_url", default="https://api.example.com")
api_key = context.get_config("api_key")  # Raises KeyError if not found

# Check if configuration exists
if context.has_config("api_key"):
    api_key = context.get_config("api_key")
```

Configuration values are automatically resolved from:

1. Organization-specific config (if exists)
2. Global config (fallback)
3. Default value (if provided)

**Secret References:**
If a config value has type `secret_ref`, it will automatically retrieve the actual secret from Azure Key Vault:

```python
# Config entry: {"Type": "secret_ref", "Value": "api-key-secret"}
# Returns actual secret value from Key Vault
api_key = context.get_config("api_key")
```

#### OAuth Connections

```python
# Get OAuth credentials for a connection
creds = await context.get_oauth_connection("HaloPSA")

# Use credentials in API calls
headers = {"Authorization": f"{creds.token_type} {creds.access_token}"}
response = requests.get("https://api.example.com/data", headers=headers)

# Or use the helper method
headers = {"Authorization": creds.get_auth_header()}

# Check if token is expired
if creds.is_expired():
    context.log("warning", "OAuth token is expired - refresh needed")
```

OAuth connections follow org → GLOBAL fallback pattern, just like configuration.

#### State Tracking & Logging

State tracking features persist data to the execution record, making it available in the UI for debugging, auditing, and understanding workflow behavior. This is different from regular Python variables which disappear when the workflow completes.

**Why does this matter?**

When you're running automation for customers, things will go wrong. A workflow that worked perfectly yesterday might fail today because:

-   An API changed
-   A user account was locked
-   Network connectivity issues
-   Rate limiting kicked in
-   A third-party service is down

Without state tracking, when a customer calls and says "my user onboarding didn't work," you have no visibility into what happened. Did the workflow even run? Did it fail at user creation or license assignment? What were the inputs?

With state tracking, you can:

1. **See exactly what happened** - Open the execution record in the UI and see logs, checkpoints, and variables
2. **Debug without access to customer data** - The execution record shows you everything you need
3. **Prove what was done** - Show customers exactly what steps completed successfully
4. **Bill accurately** - Track how many users were processed, licenses assigned, etc.
5. **Improve workflows** - See patterns in failures across multiple executions

**Why use state tracking instead of regular variables?**

Regular Python variables:

```python
# Only exists during execution, disappears when workflow completes
user_id = "user-123"
users_processed = 42
```

State tracking (persisted to database):

```python
# Stored in execution record, visible in UI after workflow completes
context.set_variable("user_id", "user-123")
context.set_variable("users_processed", 42)
```

**Logging - Track workflow progress**

```python
# Log messages are persisted and shown in execution history UI
context.log("info", "User created successfully", {"user_id": user_id})
context.log("warning", "License capacity low", {"available": 2})
context.log("error", "Failed to send email", {"error": str(e)})

# Logs appear in:
# - Execution history page in the UI
# - Azure Functions logs
# - Execution detail view for troubleshooting
```

**Checkpoints - Debug failed workflows**

Checkpoints save snapshots of workflow state at specific points. When a workflow fails, you can see exactly what data existed at each checkpoint.

**Real-world scenario:** You're onboarding 50 new users for a customer. User #37 fails. Without checkpoints, you have no idea why. With checkpoints, you can see exactly what happened for that specific user.

```python
# Save checkpoint at the start
context.save_checkpoint("workflow_start", {
    "email": email,
    "department": department
})

# Create user in M365
user = await create_m365_user(email)

# Save checkpoint after user creation (before license assignment)
context.save_checkpoint("user_created", {
    "user_id": user["id"],
    "email": email,
    "upn": user["userPrincipalName"]
})

# Assign license (might fail)
await assign_license(user["id"], license_sku)

# Save final checkpoint
context.save_checkpoint("license_assigned", {
    "user_id": user["id"],
    "license": license_sku
})

# If workflow fails at license assignment, you can:
# 1. Open execution record in UI
# 2. See checkpoint "workflow_start" - confirms workflow ran with correct inputs
# 3. See checkpoint "user_created" - user was created successfully, got ID and UPN
# 4. See checkpoint "license_assigned" is missing - failure happened during license assignment
# 5. Check logs around that time - see error: "No available licenses for SKU SPE_E3"
# 6. Fix: Purchase more licenses, then re-run just the license assignment for that user
```

**Variables - Share data across workflow steps**

Use variables to store data that needs to be visible in the execution record or accessed in the UI after completion.

**Real-world scenario:** You're running a scheduled workflow that syncs 200 users from HaloPSA to M365 every night. The workflow processes each user, and some might fail. Variables let you track what happened so you can report it.

```python
# Initialize counters
context.set_variable("users_processed", 0)
context.set_variable("users_created", 0)
context.set_variable("users_updated", 0)
context.set_variable("users_failed", 0)
context.set_variable("failed_emails", [])

# Process each user
for user in halo_users:
    try:
        # Check if user exists
        existing = await m365.get_user(user["email"])

        if existing:
            # Update existing user
            await m365.update_user(existing["id"], user)
            count = context.get_variable("users_updated", default=0)
            context.set_variable("users_updated", count + 1)
        else:
            # Create new user
            await m365.create_user(user)
            count = context.get_variable("users_created", default=0)
            context.set_variable("users_created", count + 1)

        # Track total processed
        total = context.get_variable("users_processed", default=0)
        context.set_variable("users_processed", total + 1)

    except Exception as e:
        # Track failures
        failed_count = context.get_variable("users_failed", default=0)
        context.set_variable("users_failed", failed_count + 1)

        failed_list = context.get_variable("failed_emails", default=[])
        failed_list.append(user["email"])
        context.set_variable("failed_emails", failed_list)

        context.log("error", f"Failed to process {user['email']}", {"error": str(e)})

# After workflow completes, you can see in the execution record:
# - users_processed: 200
# - users_created: 15
# - users_updated: 182
# - users_failed: 3
# - failed_emails: ["user1@example.com", "user2@example.com", "user3@example.com"]
#
# This lets you:
# 1. Report to customer: "Synced 200 users, created 15, updated 182, 3 failures"
# 2. Follow up on the 3 failed users
# 3. Bill accurately for work performed
# 4. Track trends over time (are failures increasing?)
```

**When to use state tracking vs regular variables:**

Use regular Python variables when:

-   Data is only needed during execution
-   You don't need to debug or audit the value later
-   It's temporary calculation data

Use state tracking when:

-   You want to see the value in the execution history UI
-   You need to debug failed workflows
-   You want to track metrics or counters
-   You're building multi-step workflows where state needs to be visible
-   You need audit trails for compliance

#### Integrations (Coming Soon)

Integrations provide pre-authenticated clients for external services. These are not yet implemented but will follow this pattern:

```python
# Microsoft Graph integration
graph = context.get_integration("msgraph")
users = await graph.users.list()
user = await graph.users.create(email="new@example.com", name="New User")

# HaloPSA integration
halo = context.get_integration("halopsa")
tickets = await halo.tickets.list(status="open")
ticket = await halo.tickets.create(title="New Ticket", priority="high")
```

### Data Providers

Data providers return dynamic options for workflow parameters. They're useful for:

-   Populating dropdowns with real-time data
-   Filtering options based on organization context
-   Providing metadata for UI tooltips

**Purpose:**

-   Decouple workflow logic from option generation
-   Cache expensive API calls
-   Provide context-aware options

**How They Work:**

1. Define a data provider with `@data_provider`
2. Reference it in a workflow parameter with `data_provider="provider_name"`
3. The platform automatically calls the data provider when rendering the form
4. Results are cached based on `cache_ttl_seconds`

**Example: License Selection**

```python
# Data provider (in engine/data_providers/license_providers.py)
@data_provider(
    name="get_available_licenses",
    description="Returns available M365 licenses",
    category="m365",
    cache_ttl_seconds=300  # Cache for 5 minutes
)
async def get_available_licenses(context):
    # In production, would call Microsoft Graph API
    # graph = context.get_integration('msgraph')
    # skus = await graph.subscribed_skus.get()

    return [
        {
            "label": "Microsoft 365 E3",
            "value": "SPE_E3",
            "metadata": {"available": 20, "total": 50}
        },
        {
            "label": "Microsoft 365 E5",
            "value": "SPE_E5",
            "metadata": {"available": 3, "total": 5}
        }
    ]

# Workflow using the data provider
@workflow(name="assign_license", description="Assign M365 license", category="m365")
@param("user_email", type="email", label="User Email", required=True)
@param("license_sku", type="string", label="License",
       data_provider="get_available_licenses",  # References the data provider
       required=True)
async def assign_license(context, user_email, license_sku):
    # license_sku will be "SPE_E3" or "SPE_E5" (the value, not the label)
    context.log("info", f"Assigning license {license_sku} to {user_email}")
    # Implementation...
```

**Built-in Data Providers:**

Bifrost Integrations includes several built-in data providers:

-   `get_available_licenses`: Microsoft 365 licenses
-   `get_departments`: Organization departments
-   `get_office_locations`: Office locations
-   `get_priority_levels`: Ticket priority levels (Low, Medium, High, Critical)
-   `get_ticket_categories`: IT ticket categories
-   `get_countries`: Country list for address forms

---

## Your First Workflow

Let's create a simple "Hello World" workflow to understand the basics. This example demonstrates:

-   Creating a workflow with parameters
-   Using data providers for dropdown options
-   Logging and state tracking
-   Returning results

### Step 1: Create the Workflow File

Create a new file at `workflows/workspace/workflows/hello_world.py`:

```python
"""
Hello World Workflow
A simple greeting workflow demonstrating core platform features
"""

from engine.shared.decorators import workflow, param
from engine.shared.context import OrganizationContext


@workflow(
    name="hello_world",
    description="Generate a personalized greeting in multiple languages",
    category="Examples",
    tags=["demo", "getting-started"]
)
@param(
    name="name",
    type="string",
    label="Name",
    required=True,
    help_text="Name of the person to greet"
)
@param(
    name="language",
    type="string",
    label="Language",
    default_value="english",
    data_provider="get_greeting_languages",
    help_text="Language for the greeting"
)
async def hello_world(context: OrganizationContext, name: str, language: str = "english"):
    """
    Generate a personalized greeting in the specified language.

    Args:
        context: Organization context with org info and utilities
        name: Name to greet
        language: Language for greeting (english, spanish, french, german)

    Returns:
        dict: Greeting message with metadata
    """

    # Log the execution start
    context.log("info", f"Generating greeting for {name}", {
        "language": language,
        "org_id": context.org_id
    })

    # Save checkpoint for debugging
    context.save_checkpoint("greeting_start", {
        "name": name,
        "language": language
    })

    # Generate greeting based on language
    greetings = {
        "english": f"Hello, {name}!",
        "spanish": f"¡Hola, {name}!",
        "french": f"Bonjour, {name}!",
        "german": f"Hallo, {name}!"
    }

    greeting = greetings.get(language, greetings["english"])

    # Build result
    result = {
        "greeting": greeting,
        "language": language,
        "organization": context.org_name,
        "executed_by": context.executed_by_email
    }

    # Log successful completion
    context.log("info", "Greeting generated successfully", result)

    # Save final checkpoint
    context.save_checkpoint("greeting_complete", result)

    return result
```

### Step 2: Create a Data Provider

Create a new file at `workflows/engine/data_providers/greeting_providers.py`:

```python
"""
Greeting Data Providers
Data providers for the hello world workflow
"""

from engine.shared.decorators import data_provider
from engine.shared.context import OrganizationContext


@data_provider(
    name="get_greeting_languages",
    description="Returns available greeting languages",
    category="examples",
    cache_ttl_seconds=3600  # Cache for 1 hour
)
async def get_greeting_languages(context: OrganizationContext):
    """
    Get list of available greeting languages.

    Args:
        context: Organization context

    Returns:
        List of language options
    """

    languages = [
        {
            "label": "English",
            "value": "english",
            "metadata": {"flag": "🇺🇸", "native_name": "English"}
        },
        {
            "label": "Spanish",
            "value": "spanish",
            "metadata": {"flag": "🇪🇸", "native_name": "Español"}
        },
        {
            "label": "French",
            "value": "french",
            "metadata": {"flag": "🇫🇷", "native_name": "Français"}
        },
        {
            "label": "German",
            "value": "german",
            "metadata": {"flag": "🇩🇪", "native_name": "Deutsch"}
        }
    ]

    context.log("info", f"Retrieved {len(languages)} greeting languages")

    return languages
```

### Step 3: Test the Workflow

**Local Development:**

Start the development environment:

```bash
./start-dev.sh
```

Test the workflow via API (local):

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: test-org-active" \
  -H "x-functions-key: test" \
  -d '{
    "name": "Alice",
    "language": "spanish"
  }' \
  http://localhost:7071/api/workflows/hello_world
```

**Production:**

Test against your deployed instance:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Organization-Id: your-org-id" \
  -H "x-functions-key: your-api-key" \
  -d '{
    "name": "Alice",
    "language": "spanish"
  }' \
  https://run.yourcompany.com/api/workflows/hello_world
```

**Expected Response:**

```json
{
    "greeting": "¡Hola, Alice!",
    "language": "spanish",
    "organization": "Your Organization",
    "executed_by": "user@yourcompany.com"
}
```

### Step 4: Execute via Web Interface

**Local Development:**

1. Open https://localhost:5173 in your browser
2. Navigate to "Workflows"
3. Find "Hello World" in the Examples category
4. Click "Execute"
5. Fill in the form:
    - Name: "Alice"
    - Language: Select "Spanish" from dropdown
6. Click "Run Workflow"

**Production:**

1. Open https://run.yourcompany.com in your browser
2. Log in with your credentials
3. Navigate to "Workflows"
4. Find "Hello World" in the Examples category
5. Click "Execute" and fill in the form

You'll see the execution progress and results in real-time, including:

-   Execution logs
-   Checkpoints saved during execution
-   Final result with greeting message
-   Execution metadata (who ran it, when, duration)

---

## Common Use Cases

### User Management

Automate user lifecycle management across multiple systems:

```python
from engine.shared.decorators import workflow, param
from engine.shared.context import OrganizationContext


@workflow(
    name="onboard_new_user",
    description="Complete user onboarding process",
    category="user_management",
    tags=["onboarding", "m365", "automation"]
)
@param(
    name="email",
    type="email",
    label="User Email",
    required=True,
    help_text="Email address for the new user"
)
@param(
    name="first_name",
    type="string",
    label="First Name",
    required=True
)
@param(
    name="last_name",
    type="string",
    label="Last Name",
    required=True
)
@param(
    name="department",
    type="string",
    label="Department",
    data_provider="get_departments",
    required=True
)
@param(
    name="license_sku",
    type="string",
    label="License",
    data_provider="get_available_licenses",
    required=True
)
async def onboard_new_user(
    context: OrganizationContext,
    email: str,
    first_name: str,
    last_name: str,
    department: str,
    license_sku: str
):
    """Complete onboarding workflow for new user."""

    # Log start
    context.log("info", f"Starting onboarding for {email}")

    # In production, would use integrations (not yet implemented):
    # graph = context.get_integration("msgraph")
    # user = await graph.users.create(
    #     email=email,
    #     first_name=first_name,
    #     last_name=last_name,
    #     department=department
    # )
    # await graph.users.assign_license(user["id"], license_sku)

    # For now, return mock result
    result = {
        "user_id": f"user-{email.split('@')[0]}",
        "email": email,
        "display_name": f"{first_name} {last_name}",
        "department": department,
        "license": license_sku,
        "status": "completed"
    }

    context.log("info", "User onboarding completed", result)

    return result
```

### Scheduled License Audit

Monitor and optimize Microsoft 365 license usage with automated scheduled workflows:

```python
from engine.shared.decorators import workflow
from engine.shared.context import OrganizationContext


@workflow(
    name="license_audit",
    description="Audit Microsoft 365 license usage and send report",
    category="automation",
    execution_mode="scheduled",
    schedule="0 9 * * 1",  # Every Monday at 9 AM
    tags=["m365", "licenses", "reporting"]
)
async def license_audit(context: OrganizationContext):
    """
    Automated license audit workflow.
    Runs every Monday at 9 AM to check license usage.
    """

    context.log("info", "Starting license audit")

    # In production, would use Microsoft Graph:
    # graph = context.get_integration("msgraph")
    # licenses = await graph.subscribed_skus.list()

    # Mock license data for example
    licenses = [
        {"sku": "M365 E3", "total": 50, "consumed": 48, "available": 2},
        {"sku": "M365 E5", "total": 10, "consumed": 7, "available": 3},
        {"sku": "M365 Business", "total": 25, "consumed": 15, "available": 10}
    ]

    # Find licenses with low availability (< 20%)
    low_licenses = [
        lic for lic in licenses
        if (lic["available"] / lic["total"]) < 0.2
    ]

    # Get admin email from configuration
    admin_email = context.get_config("admin_email", default="admin@company.com")

    # Log findings
    context.log("warning" if low_licenses else "info",
                f"Found {len(low_licenses)} licenses with low availability",
                {"low_licenses": low_licenses})

    # In production, would send email:
    # if low_licenses:
    #     await send_email(
    #         to=admin_email,
    #         subject="License Capacity Warning",
    #         body=format_license_report(low_licenses)
    #     )

    return {
        "total_skus": len(licenses),
        "low_availability_count": len(low_licenses),
        "admin_notified": len(low_licenses) > 0
    }
```

### OAuth-Enabled API Integration

Use OAuth connections to interact with external APIs:

```python
from engine.shared.decorators import workflow, param
from engine.shared.context import OrganizationContext
import aiohttp


@workflow(
    name="fetch_halo_tickets",
    description="Fetch open tickets from HaloPSA",
    category="integration",
    tags=["halopsa", "tickets"]
)
@param(
    name="status",
    type="string",
    label="Ticket Status",
    default_value="open",
    help_text="Filter tickets by status"
)
async def fetch_halo_tickets(context: OrganizationContext, status: str = "open"):
    """Fetch tickets from HaloPSA using OAuth connection."""

    # Get OAuth credentials for HaloPSA
    creds = await context.get_oauth_connection("HaloPSA")

    # Check if token is expired
    if creds.is_expired():
        context.log("warning", "OAuth token is expired - may need refresh")

    # Make API request
    halo_url = context.get_config("halopsa_url")
    headers = {"Authorization": creds.get_auth_header()}

    async with aiohttp.ClientSession() as session:
        async with session.get(
            f"{halo_url}/api/tickets",
            headers=headers,
            params={"status": status}
        ) as response:
            if response.status == 200:
                tickets = await response.json()
                context.log("info", f"Fetched {len(tickets)} tickets")
                return {"tickets": tickets, "count": len(tickets)}
            else:
                error_msg = f"API request failed: {response.status}"
                context.log("error", error_msg)
                raise Exception(error_msg)
```

---

## Next Steps

### Explore the Platform

1. **Browse Example Workflows**

    - Check [workflows/workspace/examples/](../../workflows/workspace/examples/) for working examples
    - Review [workflows/workspace/workflows/](../../workflows/workspace/workflows/) for production patterns
    - Study the built-in data providers in [workflows/engine/data_providers/](../../workflows/engine/data_providers/)

2. **Review Core Documentation**

    - [Local Development Guide](../../workflows/docs/local-development.md) - Set up your dev environment
    - [Workspace API Reference](../../workflows/docs/workspace-api.md) - Complete API documentation
    - [Migration Guide](../../workflows/docs/migration-guide.md) - Upgrade between versions

3. **Configure OAuth Connections**

    - Set up OAuth connections for HaloPSA, Microsoft Graph, or custom APIs
    - Test OAuth flows in the admin UI
    - Use `context.get_oauth_connection()` in your workflows

4. **Set Up Organization Config**
    - Add key/value configuration for your organization
    - Store secrets in Azure Key Vault
    - Use `context.get_config()` to access configuration

### Build Your Own Workflows

1. **Plan Your Workflow**

    - Define inputs (parameters)
    - Map out steps and decision points
    - Identify external integrations needed
    - Plan error handling strategy

2. **Create Workflow File**

    - Add file to `workflows/workspace/workflows/your_workflow.py`
    - Use `@workflow` decorator with appropriate metadata
    - Define parameters with `@param` decorators
    - Implement async function with `OrganizationContext`

3. **Create Data Providers (if needed)**

    - Add file to `workflows/engine/data_providers/your_providers.py`
    - Use `@data_provider` decorator
    - Return list of `{label, value, metadata}` objects
    - Set appropriate cache TTL

4. **Test Locally**

    - Start local dev environment with `./start-dev.sh`
    - Test via web UI at https://localhost:5173
    - Test via API with curl or Postman
    - Check logs and execution history

5. **Deploy to Production**
    - Commit changes to Git
    - Deploy to Azure using GitHub Actions
    - Test in production environment
    - Monitor execution logs

### Advanced Features

**Scheduled Workflows**

-   Use `execution_mode="scheduled"` with `schedule` parameter
-   Schedule uses cron expression format (e.g., `"0 9 * * 1"` = Mondays at 9 AM)
-   Scheduled workflows run automatically in production

**Context Features**

-   `context.log()` - Log messages with levels (info, warning, error)
-   `context.save_checkpoint()` - Save state snapshots for debugging
-   `context.set_variable()` / `context.get_variable()` - Store execution state
-   `context.get_config()` - Access org-specific or global configuration
-   `context.get_oauth_connection()` - Get OAuth credentials with auto-refresh

**Form Customization**

-   Use `help_text` to guide users
-   Add `validation` rules for input constraints
-   Use `data_provider` for dynamic dropdowns
-   Set `default_value` for common scenarios

**Security & Access Control**

-   `requires_org=True` - Require organization context
-   `expose_in_forms=True` - Show in UI (set False for internal workflows)
-   `requires_approval=True` - Require approval before execution
-   `required_permission` - Specify permission needed to execute

### Get Help

-   **Documentation**: [workflows/docs/](../../workflows/docs/) for technical guides
-   **Examples**: [workflows/workspace/examples/](../../workflows/workspace/examples/) for working code
-   **Troubleshooting**: [workflows/docs/troubleshooting.md](../../workflows/docs/troubleshooting.md) for common issues
-   **GitHub Issues**: [Create an issue](https://github.com/your-org/bifrost-integrations/issues) for bugs or feature requests
-   **Community**: Join the discussion and get help from other users

---

## Platform Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Integrations  │
│   (React)       │    │   (Azure        │    │   (External     │
│                 │    │   Functions)    │    │   APIs)         │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ • Form Builder  │◄──►│ • Workflow      │◄──►│ • Microsoft     │
│ • Execution UI  │    │   Engine        │    │   Graph         │
│ • Monitoring    │    │ • Context API   │    │ • HaloPSA       │
│ • User Management│   │ • Security      │    │ • Custom APIs   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Data Layer    │
                    │                 │
                    │ • Azure Tables  │
                    │ • Key Vault     │
                    │ • Audit Logs    │
                    └─────────────────┘
```

### Security Architecture

-   **Multi-Tenant Isolation**: Complete data separation between organizations
-   **Role-Based Access Control**: Granular permissions for users and workflows
-   **Secure Credential Management**: Key Vault integration for secrets
-   **Audit Logging**: Complete audit trail of all actions
-   **Import Restrictions**: Workspace code isolation from system internals

Welcome to Bifrost Integrations! You're now ready to build powerful automation workflows. 🚀
