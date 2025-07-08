# Submittals Folder Integration

This document describes the implementation of the Submittals folder integration feature that automatically updates Smartsheet with SharePoint folder URLs when a deal is marked as "Closed Won".

## Overview

When a user changes the Sales Stage (ColumnID: `593432251944836`) to "Closed Won", the system:

1. Creates a public OneNote notebook and copies template folders
2. Finds the "Submittals" folder among the copied templates
3. Sets up "anyone with the link" permissions for the Submittals folder
4. Updates Smartsheet column `6100803036860292` with a hyperlink to the Submittals folder

## Implementation Details

### 1. Graph API Sharing Methods (`src/graph_client.py`)

Added two new methods to handle SharePoint folder sharing:

- `share_folder_with_anyone_link(drive_id, item_id)`: Creates an anonymous sharing link for a folder
- `get_folder_web_url(drive_id, item_id)`: Gets or creates a web URL for a folder

### 2. Folder Manager Methods (`src/folder_manager.py`)

Added methods to find and manage Submittals folders:

- `find_submittals_folder(drive_id, parent_folder_id)`: Searches for folders containing "Submittals" in the name
- `get_submittals_folder_url(drive_id, parent_folder_id)`: Finds the Submittals folder and gets its web URL

### 3. Smartsheet Updater Methods (`src/smartsheet_updater.py`)

Added method to update Smartsheet with folder URLs:

- `update_submittals_folder_link(sheet_id, row_id, project_name, folder_url)`: Updates column `6100803036860292` with a hyperlink

### 4. Main Workflow Integration (`main/__init__.py`)

Modified `handle_closed_won_deal()` function to:

1. Copy template folders as before
2. Find the Submittals folder among copied templates
3. Get the web URL with "anyone with the link" permissions
4. Update Smartsheet with the hyperlink
5. Continue with OneNote notebook creation

## Column Mappings

- **Sales Stage Column**: `593432251944836` - Triggers the workflow when set to "Closed Won"
- **Project Name Column**: `3534360453271428` - Used as display text for the hyperlink
- **Submittals Folder Column**: `6100803036860292` - Where the hyperlink is inserted

## Error Handling

- If the Submittals folder is not found, an error is logged but the workflow continues
- If Smartsheet update fails, an error is logged but the workflow continues
- If sharing permissions fail, an error is logged but the workflow continues

## Testing

Use the `test_submittals_integration.py` script to test individual components:

```bash
python test_submittals_integration.py
```

The test script will prompt for required parameters and test:
1. Graph API sharing functionality
2. Submittals folder finding
3. URL generation
4. Smartsheet updates

## Configuration Requirements

Ensure the following permissions are configured in Azure AD:

- **Files.ReadWrite.All**: For folder operations and sharing
- **Sites.ReadWrite.All**: For SharePoint site access
- **Smartsheet API Token**: For updating Smartsheet cells

## Workflow Summary

1. **Trigger**: Sales Stage changes to "Closed Won"
2. **Folder Copying**: Template folders are copied to the project directory
3. **Submittals Detection**: System searches for folder containing "Submittals" in name
4. **Sharing Setup**: Creates "anyone with the link" permissions for the Submittals folder
5. **Smartsheet Update**: Inserts hyperlink in column `6100803036860292`
6. **OneNote Creation**: Continues with existing OneNote notebook creation

## Response Data

The API response now includes the Submittals folder URL:

```json
{
  "project_id": "...",
  "project_type": "...",
  "folder_results": {...},
  "notebook_result": {...},
  "submittals_folder_url": "https://sharepoint.com/...",
  "row_id": "...",
  "status": "success"
}
```

## Troubleshooting

### Common Issues

1. **Submittals folder not found**: Check that template folders contain a folder with "Submittals" in the name
2. **Sharing permissions fail**: Verify Azure AD app has Files.ReadWrite.All permission
3. **Smartsheet update fails**: Check Smartsheet API token and column ID
4. **URL generation fails**: Verify SharePoint site permissions

### Log Messages

Look for these log messages to diagnose issues:

- `"Found Submittals folder: ..."`
- `"Successfully got web URL for Submittals folder: ..."`
- `"Successfully updated Smartsheet row ... with Submittals folder URL"`
- `"Could not find or get URL for Submittals folder"`
- `"Failed to update Smartsheet with Submittals folder URL"` 