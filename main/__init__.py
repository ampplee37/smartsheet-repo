"""
Azure Function main entry point for BVC Smartsheet-SharePoint Automation.
Handles Smartsheet webhooks and orchestrates folder/notebook creation.
"""

import logging
import json
import azure.functions as func
from typing import Dict, Any, Optional
import traceback
import sys

# Configure logging with more detailed output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import modules with better error handling
try:
    from src.config import config
    logger.info("Successfully imported config")
except Exception as e:
    logger.error(f"Failed to import config: {e}")
    logger.error(traceback.format_exc())
    raise

try:
    from src.smartsheet_listener import smartsheet_listener
    logger.info("Successfully imported smartsheet_listener")
except Exception as e:
    logger.error(f"Failed to import smartsheet_listener: {e}")
    logger.error(traceback.format_exc())
    raise

try:
    from src.folder_manager import folder_manager
    logger.info("Successfully imported folder_manager")
except Exception as e:
    logger.error(f"Failed to import folder_manager: {e}")
    logger.error(traceback.format_exc())
    raise

try:
    from src.onenote_manager import onenote_manager
    logger.info("Successfully imported onenote_manager")
except Exception as e:
    logger.error(f"Failed to import onenote_manager: {e}")
    logger.error(traceback.format_exc())
    raise

try:
    from src.storage import storage_client
    logger.info("Successfully imported storage_client")
except Exception as e:
    logger.error(f"Failed to import storage_client: {e}")
    logger.error(traceback.format_exc())
    raise

# Validate configuration at startup
logger.info("Validating configuration...")
if not config.validate():
    logger.error("Configuration validation failed. Check environment variables.")
    logger.error("Required fields: BVC_ONENOTE_INGEST_BOT_ID, "
                "BVC_ONENOTE_INGEST_BOT_KEY, BVC_BOT_REFRESH_TOKEN, "
                "BVC_BOT_CLIENT_SECRET, SMTSHEET_TOKEN")
    raise RuntimeError("Missing required configuration. Check environment variables.")
else:
    logger.info("Configuration validation successful")


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Main Azure Function handler for Smartsheet webhooks.
    
    Args:
        req: HTTP request from Smartsheet webhook
        
    Returns:
        func.HttpResponse: Response to Smartsheet
    """
    try:
        logger.info("Function execution started")
        
        # Validate configuration
        if not config.validate():
            logger.error("Configuration validation failed")
            return func.HttpResponse(
                "Configuration error",
                status_code=500
            )
        
        # Get request body
        try:
            body = req.get_body().decode('utf-8')
            logger.info(f"Received request body length: {len(body)}")
            logger.info(f"Request body content: {body[:500]}...")  # Log first 500 chars
        except Exception as e:
            logger.error(f"Failed to read request body: {e}")
            return func.HttpResponse(
                "Invalid request body",
                status_code=400
            )
        
        # Get webhook signature if available
        signature = req.headers.get('Smartsheet-Hook-Signature')
        webhook_secret = config.FUNCTION_KEY or ""  # Use function key as webhook secret
        
        logger.info(f"Processing webhook with signature: {signature is not None}")
        logger.info(f"Webhook secret available: {bool(webhook_secret)}")
        
        # Process webhook event
        try:
            event_data = smartsheet_listener.process_webhook_event(
                payload=body,
                signature=signature,
                webhook_secret=webhook_secret
            )
            logger.info(f"Webhook event processed, result: {event_data is not None}")
            if event_data:
                logger.info(f"Event type: {event_data.get('type')}")
                logger.info(f"Project info: {event_data.get('project_info', {}).get('project_id', 'N/A')}")
            else:
                logger.warning("Webhook processing returned None - no relevant event data")
        except Exception as e:
            logger.error(f"Failed to process webhook event: {e}")
            logger.error(traceback.format_exc())
            return func.HttpResponse(
                f"Webhook processing error: {str(e)}",
                status_code=500
            )
        
        if not event_data:
            logger.info("No relevant event data found, returning 200")
            return func.HttpResponse(
                "OK",
                status_code=200
            )
        
        # Handle webhook challenge
        if event_data.get('type') == 'challenge':
            logger.info("Responding to webhook challenge")
            return func.HttpResponse(
                event_data['response'],
                status_code=200,
                mimetype='text/plain'
            )
        
        # Handle project type change event
        if event_data.get('type') == 'project_type_change':
            logger.info("Handling project type change event")
            return handle_project_type_change(event_data)
        
        # Handle closed won deal event
        if event_data.get('type') == 'closed_won_deal':
            logger.info("Handling closed won deal event")
            return handle_closed_won_deal(event_data)
        
        # Unknown event type
        logger.warning(f"Unknown event type: {event_data.get('type')}")
        return func.HttpResponse(
            "OK",
            status_code=200
        )
        
    except Exception as e:
        logger.error(f"Function execution failed: {e}")
        logger.error(traceback.format_exc())
        return func.HttpResponse(
            f"Internal server error: {str(e)}",
            status_code=500
        )


def handle_project_type_change(event_data: Dict[str, Any]) -> func.HttpResponse:
    """
    Handle a project type change event.
    Args:
        event_data: Processed webhook event data
    Returns:
        func.HttpResponse: Response to Smartsheet
    """
    try:
        project_info = event_data.get('project_info', {})
        project_type = project_info.get('project_type')
        # project_name = project_info.get('project_name')  # Unused variable
        if not project_type:
            logger.error("Missing ProjectType in event data")
            return func.HttpResponse(
                "Missing ProjectType",
                status_code=400
            )
        # Look up project metadata from BVCSSProjects
        project = storage_client.get_project_by_type(project_type)
        if not project:
            logger.error(f"No project metadata found for ProjectType: {project_type}")
            return func.HttpResponse(
                f"No project metadata found for ProjectType: {project_type}",
                status_code=400
            )
        logger.info(f"Processing project type change for: {project.project_name} ({project_type})")
        # Copy template folders using metadata
        folder_results = copy_template_folders(
            parent_drive_id=project.drive_id,  # Destination drive (project)
            parent_folder_id=project.job_folder_id,  # Destination parent folder
            project_category=project.project_type,  # Or whatever field is used
            project_name=project.project_name
        )
        # Create OneNote notebook, section, and page using metadata
        # Construct section name as "ProjectName - Opp ID"
        opp_id = project_info.get('3408182019051396', 'Unknown')  # SMT_PROJECT_ID from .env
        section_name = f"{project.project_name} - {opp_id}"
        
        notebook_result = create_project_notebook_and_section_with_metadata(
            site_id=project.site_id,
            parent_folder_id=project.parent_folder_id,
            notebook_name=project.company_name,  # Use CompanyName for notebook name
            section_name=section_name,           # Use "ProjectName - Opp ID" for section name
            smartsheet_data=project_info         # Pass all available Smartsheet/project data
        )
        # Prepare response
        response_data = {
            'project_name': project.project_name,
            'project_type': project_type,
            'folder_results': folder_results,
            'notebook_result': notebook_result,
            'row_id': project_info.get('row_id'),
            'status': 'success'
        }
        logger.info(f"Successfully processed project '{project.project_name}' of type '{project_type}'")
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=200,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Failed to handle project type change: {e}")
        return func.HttpResponse(
            f"Failed to process project type change: {str(e)}",
            status_code=500
        )


def handle_closed_won_deal(event_data: Dict[str, Any]) -> func.HttpResponse:
    try:
        project_info = event_data.get('project_info', {})
        project_id = project_info.get('project_id')
        project_type = project_info.get('project_type')
        if not project_id or not project_type:
            logger.error("Missing project_id or project_type in event data")
            return func.HttpResponse(
                "Missing project_id or project_type",
                status_code=400
            )
        # Look up project metadata from BVCSSProjects using project_id as RowKey
        project = storage_client.get_project_by_type(project_id)
        if not project:
            logger.error(f"No project metadata found for project_id: {project_id}")
            return func.HttpResponse(
                f"No project metadata found for project_id: {project_id}",
                status_code=400
            )
        logger.info(f"Processing Closed Won deal for project_id: {project_id}, project_type: {project_type}")
        # Copy template folders using metadata, but skip if folder already exists
        folder_results = copy_template_folders_skip_existing(
            parent_drive_id=project.drive_id,  # Destination drive (project)
            parent_folder_id=project.job_folder_id,  # Destination parent folder
            project_category=project.project_type,  # Or whatever field is used
            project_name=project.project_name
        )
        # Create OneNote notebook, section, and page using metadata
        # Construct section name as "ProjectName - Opp ID"
        opp_id = project_info.get('3408182019051396', 'Unknown')  # SMT_PROJECT_ID from .env
        section_name = f"{project.project_name} - {opp_id}"
        
        notebook_result = create_project_notebook_and_section_with_metadata(
            site_id=project.site_id,
            parent_folder_id=project.parent_folder_id,
            notebook_name=project.company_name,  # Use CompanyName for notebook name
            section_name=section_name,           # Use "ProjectName - Opp ID" for section name
            smartsheet_data=project_info         # Pass all available Smartsheet/project data
        )
        response_data = {
            'project_id': project_id,
            'project_type': project_type,
            'folder_results': folder_results,
            'notebook_result': notebook_result,
            'row_id': project_info.get('row_id'),
            'status': 'success'
        }
        logger.info(f"Successfully processed Closed Won deal for project_id: {project_id}")
        return func.HttpResponse(
            json.dumps(response_data),
            status_code=200,
            mimetype='application/json'
        )
    except Exception as e:
        logger.error(f"Failed to handle Closed Won deal: {e}")
        return func.HttpResponse(
            f"Failed to process Closed Won deal: {str(e)}",
            status_code=500
        )


def template_to_dict(template):
    return {
        "partition_key": getattr(template, "partition_key", None),
        "row_key": getattr(template, "row_key", None),
        "template_folder_id": getattr(template, "template_folder_id", None),
        "site_id": getattr(template, "site_id", None)
    }


def copy_template_folders(
    parent_drive_id: str,
    parent_folder_id: str,
    project_category: str,
    project_name: str
) -> Dict[str, Any]:
    """
    Copy template folders for a project category.
    
    Args:
        parent_drive_id: SharePoint drive ID
        parent_folder_id: Parent folder ID
        project_category: Project category
        project_name: Project name
        
    Returns:
        Dict[str, Any]: Copy operation results
    """
    try:
        logger.info(f"Copying templates for category '{project_category}'")
        
        # Copy templates using folder manager
        results = folder_manager.copy_templates_for_category(
            parent_drive_id=parent_drive_id,
            parent_folder_id=parent_folder_id,
            project_category=project_category,
            project_name=project_name
        )
        
        # Convert Template objects to dicts for JSON serialization
        for r in results:
            if 'template' in r and r['template'] is not None:
                r['template'] = template_to_dict(r['template'])
        
        # Count successes and failures
        successful_copies = [r for r in results if r.get('success')]
        failed_copies = [r for r in results if not r.get('success')]
        
        result_summary = {
            'total_templates': len(results),
            'successful_copies': len(successful_copies),
            'failed_copies': len(failed_copies),
            'details': results
        }
        
        if failed_copies:
            logger.warning(f"Some template copies failed: {len(failed_copies)} failures")
            for failure in failed_copies:
                logger.error(f"Failed to copy template '{failure.get('template', {}).get('row_key')}': {failure.get('error')}")
        else:
            logger.info(f"All {len(successful_copies)} templates copied successfully")
        
        return result_summary
        
    except Exception as e:
        logger.error(f"Failed to copy template folders: {e}")
        return {
            'total_templates': 0,
            'successful_copies': 0,
            'failed_copies': 0,
            'error': str(e),
            'details': []
        }


def copy_template_folders_skip_existing(
    parent_drive_id: str,
    parent_folder_id: str,
    project_category: str,
    project_name: str
) -> Dict[str, Any]:
    try:
        logger.info(f"Copying templates for category '{project_category}' (skip existing folders)")
        # Get existing folder names in the parent folder
        existing_folders = folder_manager.list_folder_contents(parent_drive_id, parent_folder_id)
        existing_names = set()
        for item in existing_folders.get('value', []):
            if item.get('folder') is not None:
                existing_names.add(item.get('name'))
        # Copy templates using folder manager, but skip if folder exists
        templates = storage_client.get_templates(project_category)
        results = []
        for template in templates:
            folder_name = f"{template.row_key} - {project_name}"
            if folder_name in existing_names:
                logger.info(f"Folder '{folder_name}' already exists, skipping copy.")
                results.append({
                    'template': template_to_dict(template),
                    'folder_name': folder_name,
                    'skipped': True,
                    'success': True
                })
                continue
            try:
                # Use correct source and destination drive IDs
                result = folder_manager.copy_template(
                    drive_id=template.drive_id or parent_drive_id,  # source drive
                    template_id=template.template_folder_id,
                    parent_id=parent_folder_id,  # destination folder
                    name=folder_name,
                    dest_drive_id=parent_drive_id  # destination drive
                )
                results.append({
                    'template': template_to_dict(template),
                    'folder_name': folder_name,
                    'result': result,
                    'success': True
                })
                logger.info(f"Successfully copied template '{template.row_key}' to '{folder_name}'")
            except Exception as e:
                logger.error(f"Failed to copy template '{template.row_key}': {e}")
                results.append({
                    'template': template_to_dict(template),
                    'folder_name': folder_name,
                    'error': str(e),
                    'success': False
                })
        successful_copies = [r for r in results if r.get('success') and not r.get('skipped')]
        skipped_copies = [r for r in results if r.get('skipped')]
        failed_copies = [r for r in results if not r.get('success')]
        return {
            'total_templates': len(results),
            'successful_copies': len(successful_copies),
            'skipped_copies': len(skipped_copies),
            'failed_copies': len(failed_copies),
            'details': results
        }
    except Exception as e:
        logger.error(f"Failed to copy template folders: {e}")
        return {
            'total_templates': 0,
            'successful_copies': 0,
            'skipped_copies': 0,
            'failed_copies': 0,
            'error': str(e),
            'details': []
        }


def resolve_full_graph_site_id(site_id: str, hostname: str = None) -> str:
    """
    Given a site_id (which may be just a GUID), resolve the full Graph site ID using the Graph API.
    If already in full format, return as is.
    """
    if not site_id:
        raise ValueError("site_id is required")
    if ',' in site_id:
        return site_id  # Already full format
    if not hostname:
        # Try to get from config
        from src import config
        hostname = getattr(config, 'SHAREPOINT_HOSTNAME', None) or 'bvcollective.sharepoint.com'
    # Use Graph API to resolve
    from src.graph_client import graph_client
    logger.info(f"Resolving full Graph site ID for GUID: {site_id} and hostname: {hostname}")
    site_response = graph_client.graph_request("GET", f"/sites/{hostname},{site_id}")
    full_id = site_response.get('id')
    if not full_id:
        raise ValueError(f"Could not resolve full Graph site ID for {site_id}")
    logger.info(f"Resolved full Graph site ID: {full_id}")
    return full_id


def create_project_notebook_and_section_with_metadata(site_id: str, parent_folder_id: str, notebook_name: str, section_name: str, smartsheet_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a OneNote notebook in the specified parent folder if it doesn't exist, or add a section if it does.
    Args:
        site_id: SharePoint Site ID (may be GUID or full Graph site ID)
        parent_folder_id: Parent folder ID for the notebook
        notebook_name: Project name (for notebook)
        section_name: Project name (for section)
        smartsheet_data: All available Smartsheet/project data
    Returns:
        Dict[str, Any]: Notebook and section creation result
    """
    try:
        logger.info(f"Creating OneNote notebook/section for project: {notebook_name} in parent folder: {parent_folder_id}")
        # Ensure site_id is the full Graph site ID (resolve if needed)
        full_site_id = resolve_full_graph_site_id(site_id)
        section = onenote_manager.ensure_project_section_with_metadata(full_site_id, parent_folder_id, notebook_name, section_name, smartsheet_data)
        
        # Extract URLs and notebook name from the response
        notebook_url = section.get('notebook_url')
        section_url = section.get('section_url')
        notebook_name = section.get('notebook_name', notebook_name)
        
        # Update Smartsheet with the OneNote URL
        try:
            from src.smartsheet_updater import smartsheet_updater
            row_id = smartsheet_data.get('row_id')
            sheet_id = int(config.SMTSHEET_ID)
            
            if row_id and (notebook_url or section_url):
                success = smartsheet_updater.update_row_with_onenote_url(
                    sheet_id=sheet_id,
                    row_id=row_id,
                    notebook_name=notebook_name,
                    notebook_url=notebook_url,
                    section_url=section_url
                )
                if success:
                    logger.info(f"Successfully updated Smartsheet row {row_id} with OneNote URL")
                else:
                    logger.warning(f"Failed to update Smartsheet row {row_id} with OneNote URL")
            else:
                logger.warning(f"Cannot update Smartsheet: missing row_id ({row_id}) or URLs (notebook: {notebook_url}, section: {section_url})")
        except Exception as e:
            logger.error(f"Error updating Smartsheet with OneNote URL: {e}")
        
        result = {
            'notebook_name': notebook_name,
            'section_id': section.get('id'),
            'notebook_url': notebook_url,
            'section_url': section_url,
            'status': 'success'
        }
        logger.info(f"Successfully created/verified notebook/section for project '{notebook_name}'")
        return result
    except Exception as e:
        logger.error(f"Failed to create project notebook and section: {e}")
        return {
            'status': 'error',
            'error': str(e)
        }


def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """
    Health check endpoint for debugging.
    
    Args:
        req: HTTP request
        
    Returns:
        func.HttpResponse: Health status
    """
    try:
        logger.info("Health check requested")
        
        # Check configuration
        config_status = "OK" if config.validate() else "FAILED"
        
        # Check storage client
        storage_status = "OK"
        if storage_client.table_service is None:
            storage_status = "NOT_INITIALIZED"
        
        # Check Smartsheet client
        smartsheet_status = "OK"
        if smartsheet_listener.client is None:
            smartsheet_status = "NOT_INITIALIZED"
        
        health_data = {
            "status": "healthy",
            "timestamp": "2025-01-06T23:43:14Z",
            "components": {
                "configuration": config_status,
                "storage_client": storage_status,
                "smartsheet_client": smartsheet_status
            },
            "environment": {
                "python_version": sys.version,
                "azure_functions_version": "1.17.0"
            }
        }
        
        logger.info(f"Health check completed: {health_data}")
        
        return func.HttpResponse(
            json.dumps(health_data, indent=2),
            status_code=200,
            mimetype='application/json'
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        logger.error(traceback.format_exc())
        
        error_data = {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "2025-01-06T23:43:14Z"
        }
        
        return func.HttpResponse(
            json.dumps(error_data, indent=2),
            status_code=500,
            mimetype='application/json'
        )


# Export functions for Azure Functions
__all__ = ['main', 'health_check'] 