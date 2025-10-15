#!/usr/bin/env pwsh

<#  
.SYNOPSIS  
    Deploys the Bifrost Integrations infrastructure to Azure using ARM templates.
.DESCRIPTION  
    This script creates a resource group, deploys the necessary resources using an ARM template,
    and retrieves deployment outputs for setting up GitHub secrets.
.NOTES  
    File Name  : deploy.ps1
    Author     : jack@gocovi.com
    Requires   : Az.Resources, Az.Websites

.LINK 
#>

param(
    [string]$ResourceGroup = "bifrost-rg",
    [string]$Location = "eastus",
    [string]$BaseName = "bifrost"
)

$ErrorActionPreference = "Stop"

# Check prerequisites
if (-not (Get-Module -ListAvailable -Name Az.Resources)) {
    Write-Host "Error: Az.Resources module not found" -ForegroundColor Red
    Write-Host ""
    Write-Host "Install instructions:"
    Write-Host "  Install-Module -Name Az -Repository PSGallery -Force"
    Write-Host ""
    Write-Host "More info: https://learn.microsoft.com/en-us/powershell/azure/install-azure-powershell"
    exit 1
}

# Import required modules
Import-Module Az.Resources
Import-Module Az.Websites

# Check if logged in
$context = Get-AzContext
if (-not $context) {
    Write-Host "Not logged in to Azure. Running Connect-AzAccount..."
    Connect-AzAccount
}

Write-Host "Creating resource group: $ResourceGroup"
New-AzResourceGroup -Name $ResourceGroup -Location $Location -Force | Out-Null

Write-Host "Deploying infrastructure..."
$deployment = New-AzResourceGroupDeployment `
    -ResourceGroupName $ResourceGroup `
    -TemplateFile "$PSScriptRoot/azuredeploy.json" `
    -baseName $BaseName

$apiAppName = $deployment.Outputs.apiFunctionAppName.Value
$apiUrl = $deployment.Outputs.apiFunctionAppUrl.Value
$swaName = $deployment.Outputs.staticWebAppName.Value
$swaUrl = $deployment.Outputs.staticWebAppUrl.Value

Write-Host ""
Write-Host "Deployment complete!" -ForegroundColor Green
Write-Host "API Function App: $apiAppName"
Write-Host "API URL: $apiUrl"
Write-Host "Static Web App: $swaName"
Write-Host "Static Web App URL: https://$swaUrl"
Write-Host ""
Write-Host "Fetching GitHub secrets..."

$apiPublishProfile = [xml](Get-AzWebAppPublishingProfile -ResourceGroupName $ResourceGroup -Name $apiAppName)
$apiPublishProfileXml = $apiPublishProfile.OuterXml

$swaApiToken = (Invoke-AzRestMethod `
        -Method POST `
        -ResourceGroupName $ResourceGroup `
        -ResourceProviderName Microsoft.Web `
        -ResourceType staticSites `
        -Name "$swaName/listSecrets" `
        -ApiVersion "2022-03-01").Content | ConvertFrom-Json | Select-Object -ExpandProperty properties | Select-Object -ExpandProperty apiKey

# Display instructions
Write-Host "=========================================="
Write-Host "GitHub Secrets Setup Instructions"
Write-Host "=========================================="
Write-Host ""
Write-Host "Go to your GitHub repository settings:"
Write-Host "Settings → Secrets and variables → Actions → New repository secret"
Write-Host ""
Write-Host "Add the following secrets:"
Write-Host ""
Write-Host "----------------------------------------"
Write-Host "Secret Name: AZURE_API_FUNCTIONAPP_PUBLISH_PROFILE"
Write-Host "----------------------------------------"
Write-Host $apiPublishProfileXml
Write-Host ""
Write-Host "----------------------------------------"
Write-Host "Secret Name: AZURE_STATIC_WEB_APPS_API_TOKEN"
Write-Host "----------------------------------------"
Write-Host $swaApiToken
Write-Host ""
Write-Host "=========================================="
Write-Host "Setup Complete!"
Write-Host "=========================================="
Write-Host ""
Write-Host "After adding these secrets to GitHub:"
Write-Host "1. Your GitHub Actions workflows will be able to deploy automatically"
Write-Host "2. Pushes to 'main' branch will trigger deployments"
Write-Host ""
Write-Host "Thank you for using Bifrost Integrations!"
Write-Host ""
