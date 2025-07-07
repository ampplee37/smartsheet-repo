# BVC Smartsheet-SharePoint Automation

Automated workflow that creates SharePoint folder structures, OneNote notebooks, and Microsoft Teams posts when deals are closed in Smartsheet.

## Architecture Overview

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌─────────────┐
│  Smartsheet │───▶│ Azure Function│───▶│ Graph API   │───▶│ SharePoint  │
│  Webhook    │    │  (Python)    │    │ (MS Graph)  │    │ + OneNote   │
└─────────────┘    └──────────────┘    └─────────────┘    └─────────────┘
                          │                                    │
                          ▼                                    ▼
                   ┌──────────────┐                    ┌─────────────┐
                   │ Azure Tables │                    │ Microsoft   │
                   │ (Templates)  │                    │ Teams       │
                   └──────────────┘                    └─────────────┘
```

## Features

- **Automated Folder Creation**: When a deal is marked as "Closed Won" in Smartsheet, automatically creates standardized folder structures in SharePoint
- **OneNote Integration**: Creates project-specific OneNote notebooks with sections and pages containing project data
- **Microsoft Teams Integration**: Posts project information to the "Opportunities" team channel (coming soon)
- **Template Management**: Uses Azure Tables to map project categories to template folders
- **Webhook Processing**: Real-time processing of Smartsheet row updates
- **Error Handling**: Comprehensive logging and retry mechanisms with exponential backoff
- **Resilient Operations**: Automatic retry logic for transient failures (403 errors, provisioning delays)

## Current Status

### ✅ Implemented Features
- SharePoint folder structure creation from templates
- OneNote notebook creation with " - Public" naming convention
- OneNote section and page creation with project data tables
- Retry logic for OneNote section creation (handles 403 provisioning delays)
- Comprehensive error handling and logging
- Azure Function deployment and monitoring

### 🚧 Upcoming Features
- **Microsoft Teams Integration**: Automatically post project information to the "Opportunities" team channel
  - Same data as OneNote page table
  - Rich formatting with project details
  - Automatic notifications to team members

## Prerequisites

- Python 3.11+
- Azure subscription
- Smartsheet account with API access
- SharePoint site with appropriate permissions
- Microsoft Teams with "Opportunities" team (for upcoming integration)

## Setup Instructions

### 1. Local Development Environment

```bash
# Clone the repository
git clone <your-repo-url>
cd bvc-smartsheet-sharepoint-automation

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file in the root directory:

```env
# Azure AD Configuration
CLIENT_ID=your_azure_app_client_id
CLIENT_SECRET=your_azure_app_client_secret
TENANT_ID=your_azure_tenant_id

# Smartsheet Configuration
SMTSHEET_TOKEN=your_smartsheet_api_token
SMTSHEET_ID=your_smartsheet_id
SMT_SALES_STAGE=your_sales_stage_column_id
SMT_PROJECT_TYPE=your_project_type_column_id
SMT_PROJECT_ID=your_project_id_column_id

# Azure Storage Configuration
STORAGE_CONNECTION_STRING=your_azure_storage_connection_string

# SharePoint Configuration
SHAREPOINT_SITE_ID=your_sharepoint_site_id

# Bot Authentication for OneNote (Delegated Auth)
BVC_ONENOTE_INGEST_BOT_ID=your_bot_client_id
BVC_ONENOTE_INGEST_BOT_KEY=your_bot_client_secret
BVC_BOT_REFRESH_TOKEN=your_bot_refresh_token
BVC_BOT_CLIENT_SECRET=your_bot_client_secret

# Azure Function Configuration
FUNCTION_KEY=your_function_key
```

### 3. Azure Setup

#### App Registration
1. Go to Azure Portal → Azure Active Directory → App registrations
2. Create new registration: "BVC Automation App"
3. Grant permissions:
   - Files.ReadWrite.All
   - Sites.ReadWrite.All
   - Notes.Create.All
   - ChannelMessage.Send (for upcoming Teams integration)
4. Create client secret and note the values

#### Storage Account
1. Create Azure Storage Account (if not exists)
2. Create Table service named "TemplateMapping"
3. Add template mappings (see schema below)

### 4. Smartsheet Setup

1. Create webhook on your "Sales Pipeline" sheet
2. Subscribe to row-updated events
3. Set callback URL to your Azure Function endpoint

## Template Mapping Schema

The Azure Table "TemplateMapping" should contain:

| PartitionKey | RowKey | templateFolderId |
|--------------|--------|------------------|
| Complex Design Build | Standard Folder Structure | {SharePoint Folder ItemId} |
| Simple Design Build | Basic Folder Structure | {SharePoint Folder ItemId} |
| ... | ... | ... |

## OneNote Integration

### Notebook Naming Convention
All OneNote notebooks are automatically named using the format: `<Customer> - Public`

### Page Content
Each OneNote page contains a structured table with the following project information:
- Project Category
- Project Name
- Description
- Company Name
- Customer Contact (with email link)
- Site Address
- Opportunity ID

### Retry Logic
The system includes automatic retry logic for OneNote section creation to handle Microsoft Graph API provisioning delays (403 errors).

## Deployment

### Azure Function Deployment

```bash
# Deploy using Azure Functions Core Tools
func azure functionapp publish <your-function-app-name>
```

### GitHub Actions

The project includes GitHub Actions workflow for:
- Code linting (flake8)
- Testing (pytest)
- Automatic deployment to Azure Functions

## Testing

```bash
# Run unit tests
pytest

# Run with coverage
pytest --cov=.

# Run linting
flake8 .
black --check .

# Test local function
func start
```

## Monitoring & Troubleshooting

### Application Insights
- All operations are logged to Application Insights
- Monitor function execution times and error rates
- Set up alerts for failed operations

### Common Issues
1. **Authentication Errors**: Verify Azure AD app permissions
2. **Template Not Found**: Check TemplateMapping table for correct category mapping
3. **Copy Operation Timeout**: Monitor Graph API rate limits
4. **403 Errors on OneNote Creation**: System automatically retries with exponential backoff

### Health Check Endpoint
```bash
curl http://localhost:7071/api/health
```

## Contributing

1. Create feature branch from `main`
2. Make changes and add tests
3. Run linting and tests
4. Create pull request with description
5. Ensure CI/CD pipeline passes

## License

[Your License Here]

## Support

For issues and questions:
- Create GitHub issue
- Contact: [Your Contact Information] 