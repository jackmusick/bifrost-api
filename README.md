# Bifrost Integrations

**Open-source automation platform for Integration Services** - Built to democratize best-in-class tooling before venture capital gets the chance to own something we're all incredibly passionate about.

[![License: AGPL](https://img.shields.io/badge/License-AGPL-green.svg)](https://opensource.org/licenses/agpl)
[![Azure Functions](https://img.shields.io/badge/Azure%20Functions-v4-blue.svg)](https://azure.microsoft.com/en-us/services/functions/)
[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Enabled-blue.svg)](https://www.docker.com/)

---

## Table of Contents

-   [What is Bifrost Integrations?](#what-is-bifrost-integrations)
-   [Key Features](#key-features)
-   [Quick Start](#quick-start)
-   [Documentation](#documentation)
-   [Contributing](#contributing)
-   [License](#license)

---

## What is Bifrost Integrations?

Bifrost Integrations is an open-source automation platform designed to democratize best-in-class tooling for the emerging Integration Services industry - **before venture capital gets the chance to own something we're all incredibly passionate about: solving problems with automation**.

Built by someone with nearly 20 years of MSP experience and a deep passion for scaling solutions for the industry and its customers, this platform addresses a fundamental gap in the market. Just as early PSA and RMM tools transformed Managed Services, the Integration Services industry needs purpose-built tooling that truly scales automation. Existing RPA platforms are great for rapid development and provide helpful abstractions like OAuth, storage, and monitoring, but **they cannot and will not keep pace with AI-powered development** and have always been constrained by limitations that traditional programming languages do not have.

Bifrost Integrations removes those limitations while preserving the light management layer that makes RPA tools valuable - abstracting OAuth workflows, monitoring, configuration, and secret management. It's architected with multi-tenancy at its core, enabling you to scale your Integration Services business without duplicating work across customers. **This is not another RPA tool trying to be everything to everyone**; it's a platform designed specifically to help you build scalable automation businesses without the vendor lock-in.

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

Traditional RPA tools lower the barrier to entry but fall short when you need the full power of a programming language, version control, modern development practices, and AI-assisted workflows. Meanwhile, no one is building a platform truly designed to scale automation in the way early PSA and RMM tools scaled Managed Services. In my opinion, these tools are all good at different things, but they lack the flexibility to deliver solutions for both you and your customers.

Bifrost Integrations bridges this gap by giving you the power and flexibility of code with the convenience of RPA-style abstractions - all in an open-source package that you control. **It's built to ensure the next chapter of Integration Services doesn't get ravaged by venture capitalists who prioritize extraction over value creation**.

### For the Non-Developer

With AI coding tools, proper instructions, a thriving community, and training, it's never been easier to build powerful automations. Traditional RPA tools still require you to understand programming primitives like loops, variables, and conditional logic - they had their own syntax you needed to learn. While Bifrost Integrations may require a slightly higher initial investment to get started, the combination of AI-assisted development and a platform that abstracts the dangerous complexities (authentication, secrets management, API security) means **the ceiling is dramatically higher**.

AI tools like Claude Code, GitHub Copilot, and GPT Codex can help you:

-   Write workflows from natural language descriptions
-   Debug errors and explain what code is doing
-   Suggest improvements and optimizations
-   Generate boilerplate code for common patterns

The platform handles the hard parts - OAuth flows, credential encryption, multi-tenant isolation, and API authentication - so you can focus on solving business problems. With the right guidance and AI assistance, you can build automations that would have required a full development team just a few years ago, **enabling limitless possibilities for your Integration Services business**.

---

## Key Features

-   **Multi-Tenant Architecture** - Complete data isolation per organization
-   **OAuth Management** - Automated token refresh and credential storage
-   **Secrets Management** - Secure integration with Azure Key Vault
-   **Dynamic Workflows** - Python-based with full language capabilities
-   **Reusable Integrations** - Build once, use across all customers
-   **AI-Assisted Development** - Built for modern AI coding workflows
-   **Version Control** - Git-based workflow management
-   **Cost-Effective** - ~$10-35/month for small-to-medium workloads

---

## Quick Start

> **Note**: This repository contains the backend API. For the complete platform with frontend UI, see [bifrost-client](https://github.com/jackmusick/bifrost-client).

### Prerequisites

-   Python 3.11+
-   Azure Functions Core Tools v4
-   Docker (for dev container) or Azurite (for manual setup)

### Local Development (Dev Container - Recommended)

1. Open this repository in VS Code
2. Click "Reopen in Container" when prompted
3. Wait for container to build (~2 minutes)
4. Run: `func start`

The dev container includes all dependencies (Python, Azure Functions, Azurite, etc.)

### Local Development (Manual Setup)

```bash
# Install dependencies
pip install -r requirements.txt
npm install -g azure-functions-core-tools@4 --unsafe-perm true

# Start Azurite (Azure Storage Emulator)
azurite --silent &

# Configure local settings
cp local.settings.example.json local.settings.json

# Start the Functions runtime
func start
```

**Access the API:**

-   API: http://localhost:7071
-   OpenAPI Spec: http://localhost:7071/api/openapi.json
-   Health Check: http://localhost:7071/api/health

### Running Tests

```bash
# Run all tests (use ./test.sh, NOT pytest directly)
./test.sh

# Run specific test file
./test.sh tests/integration/platform/test_sdk_from_workflow.py

# Run with coverage
./test.sh --coverage
```

---

## Documentation

For detailed documentation on architecture, development, deployment, and usage:

-   **Platform Documentation**: [Coming Soon - Link to public docs]
-   **API Documentation**: https://bifrost.yourdomain.com/api/openapi.json (when deployed)
-   **Frontend Repository**: [bifrost-client](https://github.com/jackmusick/bifrost-client)
-   **Azure Functions Docs**: https://docs.microsoft.com/en-us/azure/azure-functions/

---

## Contributing

This is intended to be a community-driven project built to ensure the Integration Services industry has the tools it needs without vendor lock-in or extractive pricing. However for the time being, while I work out the kinks, contributions and issues will be closed. Stay tuned!

## License

This project is licensed under the AGPL License - see the [LICENSE](LICENSE) file for details.

**Why AGPL?** To ensure this platform remains open and available to everyone. If you modify and deploy Bifrost, you must share those modifications with the community. This prevents proprietary forks and ensures improvements benefit everyone.

---

## Why This Matters

In my opinion, the MSP industry is at a critical juncture. We've all watched as venture capital transformed software markets and tools we use and love (loved?) - not always for the better. I believe the next frontier for MSP is in the Integration Services industry where we focus on using the automation skills we've developed over the last couple of decades and build value for new and existing customers.

**This is our chance to own the tools we build our businesses on.**
