# Forms and Configuration Guide

This guide covers the form builder, configuration management, and customization options in the Bifrost Integrations platform.

## Table of Contents

- [Overview](#overview)
- [Form Builder](#form-builder)
- [Configuration Management](#configuration-management)
- [Dynamic Forms](#dynamic-forms)
- [Validation and Rules](#validation-and-rules)
- [Customization Options](#customization-options)
- [Best Practices](#best-practices)

---

## Overview

Bifrost Integrations provides a powerful form system that automatically generates user interfaces for workflows, combined with flexible configuration management for organization-specific settings.

### Key Features

- **Automatic Form Generation**: Forms are created automatically from workflow parameters
- **Dynamic Fields**: Dropdowns, checkboxes, and multi-select with data providers
- **Real-time Validation**: Client and server-side validation with helpful error messages
- **Conditional Logic**: Show/hide fields based on other field values
- **Configuration Management**: Organization-specific settings and secrets
- **Custom Styling**: Tailwind CSS-based theming and customization

---

## Form Builder

### Automatic Form Generation

Forms are automatically generated from workflow parameter definitions:

```python
@workflow(name="create_user")
@param("email", "email", "User email address", required=True)
@param("name", "string", "Full name", required=True,
       validation={"min_length": 1, "max_length": 100})
@param("department", "string", "Department",
       data_provider="get_departments")
@param("license_types", "list", "License types",
       data_provider="get_available_licenses")
@param("is_admin", "bool", "Administrator access", default_value=False)
@param("notes", "string", "Additional notes",
       help_text="Enter any additional information here")
async def create_user(context, email, name, department, license_types, is_admin, notes):
    # Workflow implementation
    pass
```

This automatically generates a form with:

- Email input with validation
- Text input with length constraints
- Dropdown populated from data provider
- Multi-select for license types
- Checkbox for boolean value
- Textarea with help text

### Field Types and Their Renderings

#### Text Input

```python
@param("name", "string", "Full name", required=True,
       validation={"min_length": 1, "max_length": 100})
```

Renders as:

```html
<input
	type="text"
	id="name"
	name="name"
	required
	minlength="1"
	maxlength="100"
	class="w-full px-3 py-2 border border-gray-300 rounded-md"
/>
```

#### Email Input

```python
@param("email", "email", "Email address", required=True)
```

Renders as:

```html
<input
	type="email"
	id="email"
	name="email"
	required
	class="w-full px-3 py-2 border border-gray-300 rounded-md"
/>
```

#### Number Input

```python
@param("age", "int", "Age", validation={"min": 18, "max": 120})
```

Renders as:

```html
<input
	type="number"
	id="age"
	name="age"
	min="18"
	max="120"
	class="w-full px-3 py-2 border border-gray-300 rounded-md"
/>
```

#### Boolean/Checkbox

```python
@param("is_active", "bool", "Active account", default_value=True)
```

Renders as:

```html
<input
	type="checkbox"
	id="is_active"
	name="is_active"
	checked
	class="w-4 h-4 text-blue-600 border-gray-300 rounded"
/>
```

#### Dropdown (Single Select)

```python
@param("department", "string", "Department",
       data_provider="get_departments")
```

Renders as:

```html
<select
	id="department"
	name="department"
	class="w-full px-3 py-2 border border-gray-300 rounded-md"
>
	<option value="">Select a department...</option>
	<option value="it">IT</option>
	<option value="hr">HR</option>
	<option value="finance">Finance</option>
</select>
```

#### Multi-Select

```python
@param("licenses", "list", "License types",
       data_provider="get_available_licenses")
```

Renders as:

```html
<select
	id="licenses"
	name="licenses"
	multiple
	class="w-full px-3 py-2 border border-gray-300 rounded-md"
>
	<option value="enterprise">Enterprise License</option>
	<option value="business">Business License</option>
	<option value="basic">Basic License</option>
</select>
```

#### Textarea

```python
@param("description", "string", "Description",
       help_text="Provide a detailed description")
```

Renders as:

```html
<textarea
	id="description"
	name="description"
	rows="4"
	class="w-full px-3 py-2 border border-gray-300 rounded-md"
	placeholder="Provide a detailed description"
></textarea>
```

### Form Layout and Structure

Forms are automatically structured with:

```html
<form class="space-y-6">
	<!-- Field Group -->
	<div class="space-y-1">
		<label for="email" class="block text-sm font-medium text-gray-700">
			Email address <span class="text-red-500">*</span>
		</label>
		<input type="email" id="email" name="email" required />
		<p class="text-sm text-gray-500">Enter a valid email address</p>
	</div>

	<!-- Conditional Section -->
	<div id="admin-section" class="hidden space-y-4">
		<h3 class="text-lg font-medium">Administrator Settings</h3>
		<!-- Admin-specific fields -->
	</div>

	<!-- Form Actions -->
	<div class="flex justify-end space-x-3">
		<button type="button" class="btn-secondary">Cancel</button>
		<button type="submit" class="btn-primary">Create User</button>
	</div>
</form>
```

---

## Configuration Management

### Organization Configuration

Configuration is stored at the organization level and can include:

```json
{
	"organization_id": "org-abc",
	"configuration": {
		"api_settings": {
			"base_url": "https://api.example.com",
			"timeout": 30,
			"retry_attempts": 3
		},
		"user_management": {
			"default_department": "IT",
			"require_approval": true,
			"auto_assign_licenses": false
		},
		"notifications": {
			"admin_email": "admin@example.com",
			"slack_webhook": "https://hooks.slack.com/...",
			"email_notifications": true
		},
		"security": {
			"session_timeout": 60,
			"require_mfa": true,
			"allowed_ip_ranges": ["192.168.1.0/24"]
		}
	}
}
```

### Accessing Configuration in Workflows

```python
async def configuration_example(context: OrganizationContext):
    # Get configuration values with defaults
    api_url = context.get_config("api_settings.base_url", "https://default.api.com")
    timeout = context.get_config("api_settings.timeout", 30)

    # Check if configuration exists
    if context.has_config("notifications.slack_webhook"):
        slack_webhook = context.get_config("notifications.slack_webhook")
        await send_slack_notification(slack_webhook, "Workflow completed")

    # Nested configuration access
    user_settings = context.get_config("user_management", {})
    require_approval = user_settings.get("require_approval", False)

    return {
        "api_url": api_url,
        "timeout": timeout,
        "require_approval": require_approval
    }
```

### Configuration Schema Validation

Configuration can be validated against a schema:

```python
# /workspace/config_schemas/organization_config.py
from pydantic import BaseModel, Field
from typing import Optional, List

class APISettings(BaseModel):
    base_url: str = Field(..., description="API base URL")
    timeout: int = Field(30, ge=1, le=300, description="Request timeout in seconds")
    retry_attempts: int = Field(3, ge=0, le=10, description="Number of retry attempts")

class NotificationSettings(BaseModel):
    admin_email: Optional[str] = Field(None, description="Administrator email")
    slack_webhook: Optional[str] = Field(None, description="Slack webhook URL")
    email_notifications: bool = Field(True, description="Enable email notifications")

class OrganizationConfig(BaseModel):
    api_settings: APISettings
    user_management: dict = Field(default_factory=dict)
    notifications: NotificationSettings = Field(default_factory=NotificationSettings)
    security: dict = Field(default_factory=dict)
```

### Dynamic Configuration Updates

Configuration can be updated via API or admin interface:

```python
# Update configuration
async def update_organization_config(org_id: str, config_updates: dict):
    current_config = await get_organization_config(org_id)

    # Merge updates with current config
    updated_config = merge_configs(current_config, config_updates)

    # Validate against schema
    validated_config = OrganizationConfig(**updated_config)

    # Save updated configuration
    await save_organization_config(org_id, validated_config.dict())

    # Log configuration change
    await log_configuration_change(org_id, config_updates)
```

---

## Dynamic Forms

### Data Providers for Dynamic Options

Data providers supply dynamic options for form fields:

```python
@data_provider(name="get_departments")
async def get_departments(context: OrganizationContext):
    """Get departments from organization configuration."""
    departments = context.get_config("departments", [
        {"name": "IT", "description": "Information Technology"},
        {"name": "HR", "description": "Human Resources"},
        {"name": "Finance", "description": "Finance Department"}
    ])

    return [
        {
            "label": f"{dept['name']} - {dept['description']}",
            "value": dept['name'].lower().replace(" ", "_"),
            "metadata": {
                "description": dept['description'],
                "budget_code": dept.get('budget_code', '')
            }
        }
        for dept in departments
    ]

@data_provider(name="get_available_licenses")
async def get_available_licenses(context: OrganizationContext):
    """Get available Microsoft 365 licenses."""
    graph = context.get_integration("msgraph")
    skus = await graph.get_subscribed_skus()

    licenses = []
    for sku in skus.value:
        available = sku.prepaid_units.enabled - sku.consumed_units
        if available > 0:
            licenses.append({
                "label": f"{sku.sku_part_number} ({available} available)",
                "value": sku.sku_id,
                "metadata": {
                    "available": available,
                    "price": get_license_price(sku.sku_id),
                    "features": get_license_features(sku.sku_id)
                }
            })

    return licenses
```

### Conditional Form Logic

Forms can show/hide fields based on other selections:

```python
@workflow(name="conditional_form_example")
@param("user_type", "string", "User type",
       data_provider="get_user_types")
@param("department", "string", "Department",
       data_provider="get_departments",
       depends_on=["user_type"],  # Only show for certain user types
       condition={"user_type": ["employee", "contractor"]})
@param("client_name", "string", "Client name",
       depends_on=["user_type"],
       condition={"user_type": ["external"]})
@param("access_level", "string", "Access level",
       data_provider="get_access_levels",
       depends_on=["user_type", "department"],
       condition={
           "user_type": ["employee"],
           "department": ["IT", "Security"]
       })
async def conditional_form_example(context, user_type, department=None, client_name=None, access_level=None):
    """Example workflow with conditional form fields."""
    return {
        "user_type": user_type,
        "department": department,
        "client_name": client_name,
        "access_level": access_level
    }
```

### Multi-Step Forms

Complex workflows can use multi-step forms:

```python
@workflow(name="multi_step_user_creation")
# Step 1: Basic Information
@param("email", "email", "Email address", required=True, step=1)
@param("name", "string", "Full name", required=True, step=1)
@param("department", "string", "Department", data_provider="get_departments", step=1)

# Step 2: License Assignment
@param("license_type", "string", "License type",
       data_provider="get_available_licenses", step=2)
@param("additional_services", "list", "Additional services",
       data_provider="get_additional_services", step=2)

# Step 3: Confirmation
@param("send_welcome_email", "bool", "Send welcome email", default_value=True, step=3)
@param("schedule_training", "bool", "Schedule training session", default_value=False, step=3)
async def multi_step_user_creation(context, email, name, department, license_type,
                                 additional_services, send_welcome_email, schedule_training):
    """Multi-step user creation workflow."""
    # Implementation
    pass
```

---

## Validation and Rules

### Client-Side Validation

Forms include comprehensive client-side validation:

```javascript
// Email validation
const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
if (!emailRegex.test(email)) {
	showError("email", "Please enter a valid email address");
}

// Required field validation
if (!name.trim()) {
	showError("name", "Name is required");
}

// Length validation
if (name.length < 2 || name.length > 100) {
	showError("name", "Name must be between 2 and 100 characters");
}

// Number range validation
if (age < 18 || age > 120) {
	showError("age", "Age must be between 18 and 120");
}
```

### Server-Side Validation

Additional validation on the server:

```python
from engine.shared.error_handling import ValidationError

async def validate_user_input(context, email, name, department):
    """Comprehensive server-side validation."""

    # Email format validation
    email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    if not re.match(email_regex, email):
        raise ValidationError(
            "Invalid email format",
            field="email",
            details={"provided_value": email}
        )

    # Domain validation
    allowed_domains = context.get_config("allowed_domains", [])
    if allowed_domains:
        domain = email.split('@')[1]
        if domain not in allowed_domains:
            raise ValidationError(
                f"Email domain {domain} is not allowed",
                field="email",
                details={"allowed_domains": allowed_domains}
            )

    # Name validation
    if not name or len(name.strip()) < 2:
        raise ValidationError(
            "Name must be at least 2 characters long",
            field="name"
        )

    # Department validation
    available_departments = await get_departments(context)
    department_values = [dept["value"] for dept in available_departments]
    if department not in department_values:
        raise ValidationError(
            f"Department {department} is not available",
            field="department",
            details={"available_departments": department_values}
        )
```

### Custom Validation Rules

Workflows can define custom validation logic:

```python
@workflow(name="custom_validation_example")
@param("email", "email", "Email address", required=True,
       validation={
           "custom": "validate_company_email",
           "message": "Email must use company domain"
       })
@param("project_code", "string", "Project code", required=True,
       validation={
           "custom": "validate_project_code",
           "pattern": r"^PROJ-\d{4}$",
           "message": "Project code must be in format PROJ-XXXX"
       })
async def custom_validation_example(context, email, project_code):
    """Example with custom validation."""
    pass

# Custom validation functions
async def validate_company_email(context, value):
    """Validate that email uses company domain."""
    company_domain = context.get_config("company_domain", "company.com")
    return value.endswith(f"@{company_domain}")

async def validate_project_code(context, value):
    """Validate project code format."""
    return bool(re.match(r"^PROJ-\d{4}$", value))
```

---

## Customization Options

### Form Styling and Theming

Forms use Tailwind CSS and can be customized:

```css
/* Custom form styles */
.form-container {
	@apply bg-white shadow-lg rounded-lg p-6;
}

.form-field {
	@apply mb-4;
}

.form-label {
	@apply block text-sm font-medium text-gray-700 mb-1;
}

.form-input {
	@apply w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent;
}

.form-error {
	@apply text-red-500 text-sm mt-1;
}

.form-help {
	@apply text-gray-500 text-sm mt-1;
}

.btn-primary {
	@apply bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500;
}

.btn-secondary {
	@apply bg-gray-200 text-gray-800 px-4 py-2 rounded-md hover:bg-gray-300 focus:outline-none focus:ring-2 focus:ring-gray-500;
}
```

### Custom Field Components

Create custom field components for special requirements:

```javascript
// Custom date range picker component
const DateRangePicker = ({ name, label, required, onChange }) => {
	const [startDate, setStartDate] = useState("");
	const [endDate, setEndDate] = useState("");

	const handleChange = (field, value) => {
		if (field === "start") {
			setStartDate(value);
		} else {
			setEndDate(value);
		}

		onChange({
			start: field === "start" ? value : startDate,
			end: field === "end" ? value : endDate,
		});
	};

	return (
		<div className="form-field">
			<label className="form-label">
				{label} {required && <span className="text-red-500">*</span>}
			</label>
			<div className="flex space-x-2">
				<input
					type="date"
					value={startDate}
					onChange={(e) => handleChange("start", e.target.value)}
					className="form-input flex-1"
					placeholder="Start date"
				/>
				<input
					type="date"
					value={endDate}
					onChange={(e) => handleChange("end", e.target.value)}
					className="form-input flex-1"
					placeholder="End date"
				/>
			</div>
		</div>
	);
};
```

### Form Layout Templates

Different layout templates for various use cases:

```javascript
// Compact layout for mobile
const CompactFormLayout = ({ children }) => (
	<div className="space-y-3">{children}</div>
);

// Wide layout for desktop
const WideFormLayout = ({ children }) => (
	<div className="grid grid-cols-2 gap-6">{children}</div>
);

// Tabbed layout for complex forms
const TabbedFormLayout = ({ tabs, activeTab, onTabChange, children }) => (
	<div>
		<div className="border-b border-gray-200">
			<nav className="-mb-px flex space-x-8">
				{tabs.map((tab) => (
					<button
						key={tab.id}
						onClick={() => onTabChange(tab.id)}
						className={`py-2 px-1 border-b-2 font-medium text-sm ${
							activeTab === tab.id
								? "border-blue-500 text-blue-600"
								: "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300"
						}`}
					>
						{tab.label}
					</button>
				))}
			</nav>
		</div>
		<div className="mt-6">{children}</div>
	</div>
);
```

---

## Best Practices

### 1. Form Design

**Clear and Concise Labels**

```python
# ✅ Good
@param("email", "email", "Work email address", required=True,
       help_text="Use your company email address")

# ❌ Bad
@param("email", "email", "Email", required=True)
```

**Logical Field Grouping**

```python
# Group related fields together
# Personal Information
@param("first_name", "string", "First name", required=True, group="personal")
@param("last_name", "string", "Last name", required=True, group="personal")
@param("phone", "string", "Phone number", group="personal")

# Job Information
@param("department", "string", "Department", data_provider="get_departments", group="job")
@param("job_title", "string", "Job title", group="job")
@param("start_date", "date", "Start date", group="job")
```

### 2. Configuration Management

**Use Environment-Specific Defaults**

```python
# Get configuration with environment-aware defaults
def get_config_with_env_default(context, key, default_value):
    env = context.get_config("environment", "development")
    env_defaults = {
        "development": {"api_timeout": 60},
        "staging": {"api_timeout": 30},
        "production": {"api_timeout": 15}
    }

    return context.get_config(key, env_defaults.get(env, {}).get(key, default_value))
```

**Validate Configuration Early**

```python
@workflow(name="config_validated_workflow")
async def config_validated_workflow(context):
    # Validate required configuration at workflow start
    required_configs = ["api_url", "api_key", "webhook_url"]
    missing_configs = []

    for config_key in required_configs:
        if not context.has_config(config_key):
            missing_configs.append(config_key)

    if missing_configs:
        raise ConfigurationError(
            "Missing required configuration",
            missing_keys=missing_configs
        )

    # Continue with workflow
    pass
```

### 3. User Experience

**Progressive Disclosure**

```python
# Show advanced options only when needed
@param("use_advanced_settings", "bool", "Use advanced settings", default_value=False)
@param("retry_count", "int", "Retry count", default_value=3,
       depends_on=["use_advanced_settings"],
       condition={"use_advanced_settings": True})
@param("timeout", "int", "Timeout (seconds)", default_value=30,
       depends_on=["use_advanced_settings"],
       condition={"use_advanced_settings": True})
```

**Smart Defaults**

```python
# Use intelligent defaults based on context
@param("department", "string", "Department",
       data_provider="get_departments",
       default_value=lambda context: context.get_config("default_department"))

@param("manager", "string", "Manager",
       data_provider="get_managers",
       default_value=lambda context: context.caller.manager_id if context.caller.manager_id else None)
```

### 4. Performance

**Cache Data Provider Results**

```python
@data_provider(
    name="get_departments",
    description="Get organization departments",
    cache_ttl_seconds=300  # Cache for 5 minutes
)
async def get_departments(context):
    # Expensive operation to get departments
    return await fetch_departments_from_database()
```

**Lazy Load Complex Components**

```javascript
// Load complex form components only when needed
const [showAdvancedOptions, setShowAdvancedOptions] = useState(false);

const AdvancedOptions = lazy(() => import("./AdvancedOptions"));

// In form
{
	showAdvancedOptions && (
		<Suspense fallback={<div>Loading...</div>}>
			<AdvancedOptions />
		</Suspense>
	);
}
```

This comprehensive forms and configuration system provides a flexible, user-friendly interface for workflow execution while maintaining powerful customization options for different organizational needs.
