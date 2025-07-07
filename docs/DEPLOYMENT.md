# Deployment Guide

This guide provides step-by-step instructions for deploying the BVC Smartsheet-SharePoint Automation to Azure.

## Prerequisites

- Azure subscription with appropriate permissions
- Azure CLI installed and configured
- Python 3.11+ installed
- Git repository access
- Microsoft Teams with "BVC Opportunities" team (for upcoming integration)

## 1. Azure Infrastructure Setup

### 1.1 Create Resource Group

```bash
az group create --name bvc-automation-rg --location eastus
```

### 1.2 Create Storage Account

```bash
az storage account create \
  --name bvcautomationstorage \
  --resource-group bvc-automation-rg \
  --location eastus \
  --sku Standard_LRS \
  --kind StorageV2

# Get connection string
az storage account show-connection-string \
  --name bvcautomationstorage \
  --resource-group bvc-automation-rg
```

### 1.3 Create Azure Function App

```bash
# Create App Service Plan
az appservice plan create \
  --name bvc-automation-plan \
  --resource-group bvc-automation-rg \
  --sku B1 \
  --is-linux

# Create Function App
az functionapp create \
  --name bvc-automation-function \
  --resource-group bvc-automation-rg \
  --plan bvc-automation-plan \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --storage-account bvcautomationstorage
```

## 2. Azure AD App Registration

### 2.1 Create App Registration

1. Go to Azure Portal → Azure Active Directory → App registrations
2. Click "New registration"
3. Name: "BVC Automation App"
4. Supported account types: "Accounts in this organizational directory only"
5. Click "Register"

### 2.2 Configure API Permissions

1. Go to "API permissions"
2. Click "Add a permission"
3. Select "Microsoft Graph"
4. Choose "Application permissions"
5. Add the following permissions:
   - Files.ReadWrite.All
   - Sites.ReadWrite.All
   - Notes.Create.All
   - ChannelMessage.Send (for upcoming Teams integration)
   - Team.ReadBasic.All (for upcoming Teams integration)
6. Click "Grant admin consent"

### 2.3 Create Client Secret

1. Go to "Certificates & secrets"
2. Click "New client secret"
3. Add description and select expiration
4. Copy the secret value (you won't see it again)

### 2.4 Bot Registration for OneNote (Delegated Auth)

For OneNote operations, you'll also need a separate bot registration:

1. Create another app registration: "BVC OneNote Bot"
2. Configure API permissions:
   - Notes.ReadWrite.All
   - User.Read
3. Create client secret
4. Set up delegated authentication flow

## 3. Environment Configuration

### 3.1 Set Application Settings

```bash
# Set environment variables in Function App
az functionapp config appsettings set \
  --name bvc-automation-function \
  --resource-group bvc-automation-rg \
  --settings \
    CLIENT_ID="your_client_id" \
    CLIENT_SECRET="your_client_secret" \
    TENANT_ID="your_tenant_id" \
    SMTSHEET_TOKEN="your_smartsheet_token" \
    SMTSHEET_ID="your_smartsheet_id" \
    SMT_SALES_STAGE="your_sales_stage_column_id" \
    SMT_PROJECT_TYPE="your_project_type_column_id" \
    SMT_PROJECT_ID="your_project_id_column_id" \
    STORAGE_CONNECTION_STRING="your_storage_connection_string" \
    SHAREPOINT_SITE_ID="your_sharepoint_site_id" \
    BVC_ONENOTE_INGEST_BOT_ID="your_bot_client_id" \
    BVC_ONENOTE_INGEST_BOT_KEY="your_bot_client_secret" \
    BVC_BOT_REFRESH_TOKEN="your_bot_refresh_token" \
    BVC_BOT_CLIENT_SECRET="your_bot_client_secret" \
    FUNCTION_KEY="your_function_key"
```

### 3.2 Smartsheet Column IDs

You'll need to identify the following Smartsheet column IDs:
- Sales Stage column (e.g., "Closed Won")
- Project Type column
- Project ID column
- Customer Name column
- Project Name column
- Description column
- Customer Contact column
- Site Address column

Use the provided `test_smartsheet_webhook.py` script to identify these column IDs.

## 4. Template Setup

### 4.1 Create Template Mappings

Set up the Azure Table "TemplateMapping" with your project categories:

```bash
# Use the provided script to set up templates
python scripts/setup_template_mapping.py
```

### 4.2 Project Metadata Setup

Set up the BVCSSProjects table with project metadata:

```bash
# Use the provided script to set up project metadata
python setup_azure_table.py
```

## 5. Deployment

### 5.1 Using Azure Functions Core Tools

```bash
# Install Azure Functions Core Tools
npm install -g azure-functions-core-tools@4

# Login to Azure
az login

# Deploy function
func azure functionapp publish bvc-automation-function
```

### 5.2 Using GitHub Actions

1. Set up GitHub repository secrets
2. Push to main branch to trigger deployment

## 6. Testing

### 6.1 Local Testing

```bash
# Start function locally
func start

# Test webhook (in another terminal)
python test_smartsheet_webhook.py

# Test health endpoint
curl http://localhost:7071/api/health
```

### 6.2 Production Testing

1. Update a row in Smartsheet to "Closed Won"
2. Monitor Azure Function logs
3. Verify SharePoint folder creation
4. Verify OneNote notebook and page creation

## 7. Monitoring and Troubleshooting

### 7.1 Application Insights

1. Go to Application Insights resource
2. Monitor Live Metrics, Performance, Failures, Logs

### 7.2 Function Logs

```bash
# View function logs
az webapp log tail \
  --name bvc-automation-function \
  --resource-group bvc-automation-rg
```

### 7.3 Health Monitoring

The function includes a health check endpoint that verifies:
- Configuration validity
- Storage connection
- Graph API authentication

## 8. Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify Azure AD app permissions
   - Check client secret expiration
   - Ensure admin consent is granted
   - Verify bot refresh token is valid

2. **Storage Connection Issues**
   - Verify connection string
   - Check storage account access
   - Ensure tables exist and are populated

3. **Webhook Failures**
   - Verify function key in callback URL
   - Check function logs
   - Test webhook manually

4. **OneNote Creation Failures**
   - Check bot authentication
   - Verify site permissions
   - Monitor for 403 errors (system automatically retries)

5. **Template Copy Failures**
   - Verify template folder IDs in Azure Tables
   - Check SharePoint permissions
   - Monitor Graph API rate limits

### Retry Logic

The system includes automatic retry logic for:
- OneNote section creation (403 provisioning delays)
- Graph API transient failures
- Network connectivity issues

Retry configuration is in `src/config.py`:
- `MAX_RETRIES`: 3 (default)
- `RETRY_DELAY`: 5 seconds (base delay for exponential backoff)

## 9. Upcoming Features

### Microsoft Teams Integration

The system is being extended to include Microsoft Teams integration:

1. **Team Channel Posts**: Automatically post project information to the "Opportunities" team channel
2. **Rich Formatting**: Include project details in a formatted message
3. **Notifications**: Team members receive notifications about new opportunities

### Required Permissions for Teams Integration

When implementing Teams integration, ensure the app has:
- `ChannelMessage.Send`
- `Team.ReadBasic.All`
- `Channel.ReadBasic.All`

### Implementation Notes

- Teams integration will use the same project data as OneNote pages
- Messages will be formatted for better readability
- Integration will follow the same retry patterns as OneNote operations

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify Azure AD app permissions
   - Check client secret expiration
   - Ensure admin consent is granted

2. **Storage Connection Issues**
   - Verify connection string
   - Check storage account access
   - Ensure table exists

3. **Webhook Failures**
   - Verify function key in callback URL
   - Check function logs
   - Test webhook manually 