# End-to-End Integration Tests

These tests run against a real Azure Functions instance with Azurite and Key Vault emulator.

## Setup

1. Start the services:

    ```bash
    cd /Users/jack/GitHub/bifrost-integrations
    docker-compose up -d
    ```

2. Initialize tables and seed data:

    ```bash
    cd api
    python shared/init_tables.py
    python seed_data.py
    ```

3. Run the tests:
    ```bash
    pytest tests/integration_e2e/ -v
    ```

## How These Tests Work

Instead of mocking internal authentication logic, these tests:

1. Make real HTTP requests to `http://localhost:7071/api/*`
2. Use the `X-MS-Client-Principal` header (what Azure Static Web Apps sends)
3. Test against actual seeded data in Azurite
4. Verify real responses from the running Functions app

This is exactly how the system runs in production, making these the most realistic integration tests.

## Test Data

Test users created by `seed_data.py`:

-   **Platform Admin**: `jack@gocovi.com` (UserType: PLATFORM, IsPlatformAdmin: True)
-   **Org User**: `jack@gocovi.dev` (UserType: ORG, assigned to Covi Development org)

Organizations:

-   **Covi Development**: Has forms, configs, and user assignments
-   **Contoso Ltd**: Secondary org for isolation testing
