#!/usr/bin/env python3
"""
Azure Authentication Setup Script

This script helps developers authenticate to Azure interactively BEFORE starting
the development environment. It ensures Azure CLI credentials are available for
Key Vault access.

This is Step 0 for local development if your workflows use get_config() with secrets.

Usage:
    python scripts/authenticate_azure.py
    python scripts/authenticate_azure.py --vault-url https://my-vault.vault.azure.net/
"""

from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
import argparse
import os
import sys
import json
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✓ Loaded .env file")
except:
    pass  # .env is optional


def get_vault_url_from_local_settings():
    """Try to read AZURE_KEY_VAULT_URL from local.settings.json files."""
    settings_paths = [
        project_root / "workflows" / "local.settings.json",
        project_root / "client" / "api" / "local.settings.json",
    ]

    for settings_path in settings_paths:
        if settings_path.exists():
            try:
                with open(settings_path) as f:
                    settings = json.load(f)
                    vault_url = settings.get("Values", {}).get("AZURE_KEY_VAULT_URL")
                    if vault_url:
                        return vault_url
            except:
                pass

    return None


def prompt_for_vault_url():
    """Prompt user to enter Key Vault URL."""
    print("\n" + "=" * 60)
    print("  Key Vault URL Configuration")
    print("=" * 60)
    print("\nNo Key Vault URL found.")
    print("\nYou can:")
    print("  1. Enter it now (for this session only)")
    print("  2. Set AZURE_KEY_VAULT_URL in local.settings.json")
    print("  3. Set AZURE_KEY_VAULT_URL environment variable")
    print("\nExample URL format: https://my-vault.vault.azure.net/")
    print()

    vault_url = input("Enter Key Vault URL (or press Enter to skip): ").strip()

    if not vault_url:
        print("\n⚠️  Skipping Key Vault authentication (no URL provided)")
        print("\nTo configure later:")
        print("  1. Add to workflows/local.settings.json:")
        print('     "AZURE_KEY_VAULT_URL": "https://your-vault.vault.azure.net/"')
        print("  2. Or set environment variable:")
        print('     export AZURE_KEY_VAULT_URL="https://your-vault.vault.azure.net/"')
        print("\nYou can still run workflows that don't require secrets.")
        return None

    return vault_url


def authenticate_azure(vault_url: str = None):
    """
    Authenticate to Azure and test Key Vault access.

    This will trigger interactive authentication if needed (via browser or device code).

    Args:
        vault_url: Optional Key Vault URL. If not provided, tries to find it or prompts user.
    """
    print("\n" + "=" * 60)
    print("  Azure Authentication Setup")
    print("=" * 60 + "\n")

    print("This script will:")
    print("  1. Authenticate you to Azure (may open browser)")
    print("  2. Test your Key Vault access")
    print("  3. Verify permissions")
    print()

    # Try to get vault URL from multiple sources
    if not vault_url:
        # Try environment variable first
        vault_url = os.environ.get("AZURE_KEY_VAULT_URL")

        if vault_url:
            print(f"✓ Found Key Vault URL in environment: {vault_url}")
        else:
            # Try local.settings.json files
            vault_url = get_vault_url_from_local_settings()

            if vault_url:
                print(f"✓ Found Key Vault URL in local.settings.json: {vault_url}")
            else:
                # Prompt user
                vault_url = prompt_for_vault_url()

                if not vault_url:
                    # User chose to skip
                    sys.exit(0)

    print()

    # Step 1: Authenticate with Azure
    print("Step 1: Authenticating to Azure...")
    print("  Using DefaultAzureCredential")
    print("  This may:")
    print("    - Use existing Azure CLI credentials (az login)")
    print("    - Open a browser window for interactive login")
    print("    - Prompt for device code")
    print()

    try:
        credential = DefaultAzureCredential()
        print("✓ Azure credential created successfully")
    except Exception as e:
        print(f"❌ Failed to create Azure credential: {e}")
        print("\nTroubleshooting:")
        print("  1. Install Azure CLI: https://docs.microsoft.com/cli/azure/install-azure-cli")
        print("  2. Run: az login")
        print("  3. Try this script again")
        sys.exit(1)

    # Step 2: Create Key Vault client
    print("\nStep 2: Connecting to Key Vault...")
    print(f"  Vault URL: {vault_url}")

    try:
        client = SecretClient(vault_url=vault_url, credential=credential)
        print("✓ Key Vault client created successfully")
    except Exception as e:
        print(f"❌ Failed to create Key Vault client: {e}")
        print("\nTroubleshooting:")
        print("  1. Verify the Key Vault URL is correct")
        print("  2. Check that the Key Vault exists")
        print("  3. Ensure you have network access")
        sys.exit(1)

    # Step 3: Test list permissions
    print("\nStep 3: Testing Key Vault permissions...")
    print("  Attempting to list secrets (requires 'list' permission)...")

    try:
        secrets = client.list_properties_of_secrets()
        secret_names = [s.name for s in secrets]
        secret_count = len(secret_names)

        print(f"✓ Successfully listed secrets")
        print(f"  Found {secret_count} secret(s) in Key Vault")

        if secret_count > 0:
            print(f"\n  Secrets found:")
            for name in secret_names[:5]:  # Show first 5
                print(f"    - {name}")
            if secret_count > 5:
                print(f"    ... and {secret_count - 5} more")
        else:
            print("\n  ℹ️  No secrets found in Key Vault (this is okay for initial setup)")

    except Exception as e:
        error_str = str(e)

        if "403" in error_str or "Forbidden" in error_str:
            print("❌ Permission Denied (403 Forbidden)")
            print("\n  You are authenticated but don't have permission to list secrets.")
            print("\n  Solution:")
            print("    Ask your Azure administrator to grant you:")
            print("    - Role: 'Key Vault Secrets User' (for read-only)")
            print("    - Or: 'Key Vault Secrets Officer' (for full access)")
            print("\n  For local development, run:")
            print(f"    az keyvault set-policy --name <vault-name> \\")
            print(f"      --upn <your-email> \\")
            print(f"      --secret-permissions get list")
            sys.exit(1)

        elif "401" in error_str or "Authentication" in error_str:
            print("❌ Authentication Failed (401 Unauthorized)")
            print("\n  Solution:")
            print("    1. Run: az login")
            print("    2. Verify: az account show")
            print("    3. Try this script again")
            sys.exit(1)

        else:
            print(f"❌ Error: {e}")
            print("\n  Troubleshooting:")
            print("    1. Verify Key Vault URL is correct")
            print("    2. Check network connectivity")
            print("    3. Ensure Key Vault exists")
            print(f"    4. Verify you have access to the vault")
            sys.exit(1)

    # Step 4: Test get permission
    print("\nStep 4: Testing secret retrieval...")
    print("  Attempting to get a secret (requires 'get' permission)...")

    try:
        # Try to get first available secret, or use test name
        test_secret_name = secret_names[0] if secret_names else "test-connection"
        secret = client.get_secret(test_secret_name)
        print(f"✓ Successfully retrieved secret '{test_secret_name}'")
        print(f"  Value length: {len(secret.value)} characters")
    except Exception as e:
        error_str = str(e)

        if "404" in error_str or "NotFound" in error_str:
            print(f"  ℹ️  Secret '{test_secret_name}' not found")
            print("  You have 'get' permission (this is okay)")
        elif "403" in error_str:
            print("  ⚠️  Permission denied for 'get' operation")
            print("  You can list but not retrieve secrets")
            print("  You may need additional permissions")
        else:
            print(f"  ⚠️  Could not test 'get' permission: {e}")

    # Success!
    print("\n" + "=" * 60)
    print("  ✅ Azure Authentication Complete")
    print("=" * 60)
    print("\n✅ You are authenticated and can access Key Vault!")
    print("\nYour credentials are cached. You can now:")
    print("  - Start the development environment")
    print("  - Access secrets in workflows via get_config()")
    print("  - Use Key Vault without additional prompts")
    print("\nNext steps:")
    print("  1. Start workflows: cd workflows && func start")
    print("  2. Start client API: cd client/api && func start")
    print("  3. Test workflows that use secrets")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Authenticate to Azure and setup Key Vault access for local development",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-detect Key Vault URL from local.settings.json or environment
  python scripts/authenticate_azure.py

  # Specify vault URL directly
  python scripts/authenticate_azure.py --vault-url https://my-vault.vault.azure.net/

  # Set environment variable first
  export AZURE_KEY_VAULT_URL=https://my-vault.vault.azure.net/
  python scripts/authenticate_azure.py

Recommended workflow:
  1. Run this script BEFORE starting your dev environment
  2. Authenticate interactively when prompted
  3. Start your application (credentials are cached)
        """
    )
    parser.add_argument(
        "--vault-url",
        help="Azure Key Vault URL (e.g., https://my-vault.vault.azure.net/)"
    )

    args = parser.parse_args()

    try:
        authenticate_azure(vault_url=args.vault_url)
    except KeyboardInterrupt:
        print("\n\n⚠️  Authentication interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
