# Forms

- The selection between global and organization is redundant as that should be handled by switching scopes like everything else.
- Static dropdowns don't allow the form creator to specify dropdown options. These options should be available to the end-user running the form.

## Form Context

- Create a `context` object to be used through out the form
- We should be able to select a workflow that runs as soon as the form launches
- When the workflow finishes (show a loading state while it's running), the data is available in `context.workflow_result`
- Query parameters are available in `context.params` (/execute/{form_id}?foo=bar -> context.params.foo)
- When we make selections on the form, those values get stored in a `context.field.{field_name}`.

## Dynamic Visibility

- Use Javascript to set form visibility. This is so we can say something like: context.field.first_name !== null
- Fields are evaluated on any change.

## More Components

- Text/Markdown -- non-input component that allows us to display information
- HTML box (we should have support for this with our HTML result in workflows)
	Our HTML component SHOULD except props already I think, so I would think we could pass the ENTIRE context so that our HTML could have something like ${context.field.first_name}.
- Date/Time
- Radio Buttons
- Files Upload (generates a SaaS URI for posting, saas URI is sent to the workflow)
	- Multi-select dropdown of allowed file types, only show common file types but let them type and enter to add a custom type
	- Multiple files can be allowed
	- Always returns as a list of files even if single

# Workflows via HTTP

- This will be the start of our settings page, maybe under a "Workflows" or "Security". Open to ideas here!
- We need to be able to generate a "global" `x-workflows-key`.
- We need to be able to generate a per-workflow "x-workflows-key".
- When this workflow is called with this key, we will validate that it is either a global key or a workflow key. If it is, we will authenticate the request against the GLOBAL scope (like Platform Admin).
- Both workflow and global keys should be able to be regenerated.
- HTTP should be togglable and toggle off.
- This means we'll need to update the dialog we have for HTTP (badge on workflow) with our new options. It's currently setup assuming for x-function-key.
- This will involve allowing anonymous posting/getting of /api/workflows/*
- Will will need a decorator for this new construct (something like @has_workflow_key) and ensure all other scenarios are properly secured with a decorator since we WON'T be protecting it anymore with staticwebapp.config.json

# Workflows via CRON

- Confirm cron functionality in workflows
- Display schedule in UI
- Test and ensure functional (not sure how)

# Async Workflows

- Workflows have an option to be async
- This is currently a prop in @workflow but I'm thinking we just need make the prop the default option, but have the option to change it when running workflows directly
- When tying workflows to forms, we'll also want this option
- Queued/async workflows have the option to return a result immediately to the UI. Will need help thinking through this.
- Ensure proper queuing of these jobs -- we should have a worker function that can pickup all of the context and everything sent and essentially delegate it to a queue
- Be sure we're not duplicating logic. It seems like if we're triggering things off of the same details, we should basically make sure the queue worker and the syncronous workflow execute with the same function
- The UI should essentially present a "Queued" status
- Add a refresh icon and refresh every unfinished jobs every 5-10 seconds while we're on the page. This can happen regardless of whether something was async or not. Avoid "refreshing". Use React's memorize feature to provide a realtime-like experience without flashing.

# Front End Polish

All pages with tables and cards should have:

- A full text box search
- Load when entering the page
- Reload when changing global scope (forms should be doing this) UNLESS it's unscoped
- Ensure History paginates -- we could have a million execution logs

## Branding

- Platform Admins should be able to upload a custom square and rectangle logo (all image formats including SVG)
- The square logo replaces the one in side bar
- The rectangle appears above the title in the form
- We should be able to change the primary color of ShadCN this way too
- Images should be a small dropdown
- This goes in the settings app under a Branding tab

## Execution Logs / History

- We should have a few indexes at this point. We need an efficient way to search by user, workflow, status and even a date range (think this is possible with row key)

# Backend

- We should be able to maintain a system 'workspace' folder that is available to the user just like their /workspace folder. This would auto import just the same. When developing the platform, this is now where our example and test workflows will go.
- These should be labeled as system workflows in the UI and be hidden by default. The platform admin would be able to toggle them as visible.
- We should have a simple, shared 'utilities' that we can build-in for the user. They should be able to do something like `from bifrost import utils`. This can go in shared\utilities and we'll need to export this with bifrost.py and bifrost.pyi. This `utilities` folder should be a place to drop libraries into that we've created. For example, I created a library for openapi2python. I should be able to have an openapi2python.py folder and import it like: `from bifrost import openapi2python`.


# Authentication

- We need to store the user's Entra ID user ID from authorization when creating and if it doesn't exist on the user as they get logged in and matched by email.
- The user should now be matched first by Entra ID user ID and then by email rather than just email.
- This prevents a username change from breaking the entire system, creating a duplicate user.