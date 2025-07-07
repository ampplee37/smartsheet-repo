# Azure Function GitHub Actions Deployment Script (PowerShell)
# This script sets up automatic deployment from GitHub to Azure Functions

param(
    [Parameter(Mandatory=$true)]
    [string]$FunctionAppName,
    
    [Parameter(Mandatory=$true)]
    [string]$ResourceGroup
)

Write-Host "🚀 Setting up Azure Function GitHub Actions Deployment" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green

# Check if git is initialized
if (-not (Test-Path ".git")) {
    Write-Host "❌ Git repository not found. Please run 'git init' first." -ForegroundColor Red
    exit 1
}

# Check if Azure CLI is installed
try {
    $null = Get-Command az -ErrorAction Stop
} catch {
    Write-Host "❌ Azure CLI not found. Please install it first:" -ForegroundColor Red
    Write-Host "   https://docs.microsoft.com/en-us/cli/azure/install-azure-cli" -ForegroundColor Yellow
    exit 1
}

# Check if user is logged in to Azure
try {
    $null = az account show 2>$null
} catch {
    Write-Host "❌ Not logged in to Azure. Please run 'az login' first." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Prerequisites check passed" -ForegroundColor Green

# Update the workflow file with the correct function app name
$workflowPath = ".github/workflows/deploy-azure-function.yml"
if (Test-Path $workflowPath) {
    (Get-Content $workflowPath) -replace "your-function-app-name", $FunctionAppName | Set-Content $workflowPath
    Write-Host "✅ Updated workflow file with function app name: $FunctionAppName" -ForegroundColor Green
} else {
    Write-Host "❌ Workflow file not found at $workflowPath" -ForegroundColor Red
    exit 1
}

# Get subscription
$subscription = az account show --query name -o tsv
Write-Host "Using subscription: $subscription" -ForegroundColor Cyan

# Generate publish profile
Write-Host "📋 Generating publish profile..." -ForegroundColor Yellow
$publishProfile = az functionapp deployment list-publishing-profiles --name $FunctionAppName --resource-group $ResourceGroup --xml

# Encode the publish profile for GitHub Secrets
$encodedProfile = [Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes($publishProfile))

Write-Host "✅ Generated publish profile" -ForegroundColor Green

# Instructions for setting up GitHub repository
Write-Host ""
Write-Host "📝 Next Steps:" -ForegroundColor Cyan
Write-Host "==============" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Create a new GitHub repository (if not already done):" -ForegroundColor White
Write-Host "   https://github.com/new" -ForegroundColor Yellow
Write-Host ""
Write-Host "2. Add your local repository to GitHub:" -ForegroundColor White
Write-Host "   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git" -ForegroundColor Yellow
Write-Host "   git branch -M main" -ForegroundColor Yellow
Write-Host "   git add ." -ForegroundColor Yellow
Write-Host "   git commit -m 'Initial commit with Azure Function'" -ForegroundColor Yellow
Write-Host "   git push -u origin main" -ForegroundColor Yellow
Write-Host ""
Write-Host "3. Set up GitHub Secrets:" -ForegroundColor White
Write-Host "   Go to your GitHub repository → Settings → Secrets and variables → Actions" -ForegroundColor Yellow
Write-Host "   Add a new repository secret:" -ForegroundColor Yellow
Write-Host "   - Name: AZURE_FUNCTIONAPP_PUBLISH_PROFILE" -ForegroundColor Yellow
Write-Host "   - Value: (paste the encoded profile below)" -ForegroundColor Yellow
Write-Host ""
Write-Host "Encoded publish profile:" -ForegroundColor White
Write-Host $encodedProfile -ForegroundColor Green
Write-Host ""
Write-Host "4. Set up environment variables in Azure Function App:" -ForegroundColor White
Write-Host "   Go to Azure Portal → Your Function App → Configuration → Application settings" -ForegroundColor Yellow
Write-Host "   Add these environment variables:" -ForegroundColor Yellow
Write-Host "   - BVC_ONENOTE_INGEST_BOT_ID" -ForegroundColor Yellow
Write-Host "   - BVC_ONENOTE_INGEST_BOT_KEY" -ForegroundColor Yellow
Write-Host "   - BVC_BOT_REFRESH_TOKEN" -ForegroundColor Yellow
Write-Host "   - BVC_BOT_CLIENT_SECRET" -ForegroundColor Yellow
Write-Host "   - SMTSHEET_TOKEN" -ForegroundColor Yellow
Write-Host "   - STORAGE_CONNECTION_STRING (optional)" -ForegroundColor Yellow
Write-Host "   - FUNCTION_KEY (optional)" -ForegroundColor Yellow
Write-Host "   - TENANT_ID (optional)" -ForegroundColor Yellow
Write-Host "   - CLIENT_ID (optional)" -ForegroundColor Yellow
Write-Host "   - CLIENT_SECRET (optional)" -ForegroundColor Yellow
Write-Host ""
Write-Host "5. Test the deployment:" -ForegroundColor White
Write-Host "   Make a small change to any file and push to GitHub:" -ForegroundColor Yellow
Write-Host "   git add ." -ForegroundColor Yellow
Write-Host "   git commit -m 'Test deployment'" -ForegroundColor Yellow
Write-Host "   git push" -ForegroundColor Yellow
Write-Host ""
Write-Host "6. Monitor the deployment:" -ForegroundColor White
Write-Host "   Go to your GitHub repository → Actions tab" -ForegroundColor Yellow
Write-Host "   You should see the deployment workflow running" -ForegroundColor Yellow
Write-Host ""
Write-Host "🎉 Setup complete! Your function will now deploy automatically on every push to main branch." -ForegroundColor Green 