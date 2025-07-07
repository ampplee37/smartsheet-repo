#!/bin/bash

# Azure Function GitHub Actions Deployment Script
# This script sets up automatic deployment from GitHub to Azure Functions

set -e

echo "🚀 Setting up Azure Function GitHub Actions Deployment"
echo "=================================================="

# Check if git is initialized
if [ ! -d ".git" ]; then
    echo "❌ Git repository not found. Please run 'git init' first."
    exit 1
fi

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "❌ Azure CLI not found. Please install it first:"
    echo "   https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if user is logged in to Azure
if ! az account show &> /dev/null; then
    echo "❌ Not logged in to Azure. Please run 'az login' first."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Get function app name
read -p "Enter your Azure Function App name: " FUNCTION_APP_NAME

# Update the workflow file with the correct function app name
sed -i "s/your-function-app-name/$FUNCTION_APP_NAME/g" .github/workflows/deploy-azure-function.yml

echo "✅ Updated workflow file with function app name: $FUNCTION_APP_NAME"

# Get resource group
read -p "Enter your Azure Resource Group name: " RESOURCE_GROUP

# Get subscription
SUBSCRIPTION=$(az account show --query name -o tsv)
echo "Using subscription: $SUBSCRIPTION"

# Generate publish profile
echo "📋 Generating publish profile..."
PUBLISH_PROFILE=$(az functionapp deployment list-publishing-profiles \
    --name $FUNCTION_APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --xml)

# Encode the publish profile for GitHub Secrets
ENCODED_PROFILE=$(echo "$PUBLISH_PROFILE" | base64 -w 0)

echo "✅ Generated publish profile"

# Instructions for setting up GitHub repository
echo ""
echo "📝 Next Steps:"
echo "=============="
echo ""
echo "1. Create a new GitHub repository (if not already done):"
echo "   https://github.com/new"
echo ""
echo "2. Add your local repository to GitHub:"
echo "   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git"
echo "   git branch -M main"
echo "   git add ."
echo "   git commit -m 'Initial commit with Azure Function'"
echo "   git push -u origin main"
echo ""
echo "3. Set up GitHub Secrets:"
echo "   Go to your GitHub repository → Settings → Secrets and variables → Actions"
echo "   Add a new repository secret:"
echo "   - Name: AZURE_FUNCTIONAPP_PUBLISH_PROFILE"
echo "   - Value: (paste the encoded profile below)"
echo ""
echo "Encoded publish profile:"
echo "$ENCODED_PROFILE"
echo ""
echo "4. Set up environment variables in Azure Function App:"
echo "   Go to Azure Portal → Your Function App → Configuration → Application settings"
echo "   Add these environment variables:"
echo "   - BVC_ONENOTE_INGEST_BOT_ID"
echo "   - BVC_ONENOTE_INGEST_BOT_KEY"
echo "   - BVC_BOT_REFRESH_TOKEN"
echo "   - BVC_BOT_CLIENT_SECRET"
echo "   - SMTSHEET_TOKEN"
echo "   - STORAGE_CONNECTION_STRING (optional)"
echo "   - FUNCTION_KEY (optional)"
echo "   - TENANT_ID (optional)"
echo "   - CLIENT_ID (optional)"
echo "   - CLIENT_SECRET (optional)"
echo ""
echo "5. Test the deployment:"
echo "   Make a small change to any file and push to GitHub:"
echo "   git add ."
echo "   git commit -m 'Test deployment'"
echo "   git push"
echo ""
echo "6. Monitor the deployment:"
echo "   Go to your GitHub repository → Actions tab"
echo "   You should see the deployment workflow running"
echo ""
echo "🎉 Setup complete! Your function will now deploy automatically on every push to main branch." 