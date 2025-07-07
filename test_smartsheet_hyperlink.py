"""
Test script for Smartsheet hyperlink functionality with project description.
"""

import os
import json
from dotenv import load_dotenv
from src.smartsheet_updater import SmartsheetUpdater

def test_smartsheet_hyperlink():
    """Test the Smartsheet hyperlink update functionality."""
    load_dotenv()
    
    # Initialize the updater
    updater = SmartsheetUpdater()
    
    # Test data
    sheet_id = int(os.getenv("SMTSHEET_ID", "0"))
    row_id = 6122993425813380  # Replace with actual row ID for testing
    notebook_name = "Test Company - Public"
    notebook_url = "https://bvcollective.sharepoint.com/sites/test/_layouts/15/OneNote.aspx?id=/sites/test/Shared%20Documents/Test%20Company%20-%20Public"
    section_url = "https://bvcollective.sharepoint.com/sites/test/_layouts/15/OneNote.aspx?id=/sites/test/Shared%20Documents/Test%20Company%20-%20Public/Test%20Project%20-%20OPP123"
    project_description = "This is a test project description that should appear as the hyperlink text"
    
    print("Testing Smartsheet hyperlink update...")
    print(f"Sheet ID: {sheet_id}")
    print(f"Row ID: {row_id}")
    print(f"Notebook Name: {notebook_name}")
    print(f"Notebook URL: {notebook_url}")
    print(f"Section URL: {section_url}")
    print(f"Project Description: {project_description}")
    
    # Test with project description (preferred)
    print("\n--- Test 1: With Project Description ---")
    success = updater.update_row_with_onenote_url(
        sheet_id=sheet_id,
        row_id=row_id,
        notebook_name=notebook_name,
        notebook_url=notebook_url,
        section_url=section_url,
        project_description=project_description
    )
    print(f"Result: {'Success' if success else 'Failed'}")
    
    # Test with notebook name only (fallback)
    print("\n--- Test 2: With Notebook Name Only ---")
    success = updater.update_row_with_onenote_url(
        sheet_id=sheet_id,
        row_id=row_id,
        notebook_name=notebook_name,
        notebook_url=notebook_url,
        section_url=section_url,
        project_description=None
    )
    print(f"Result: {'Success' if success else 'Failed'}")
    
    # Test with section URL only
    print("\n--- Test 3: With Section URL Only ---")
    success = updater.update_row_with_onenote_url(
        sheet_id=sheet_id,
        row_id=row_id,
        notebook_name=notebook_name,
        notebook_url=None,
        section_url=section_url,
        project_description=project_description
    )
    print(f"Result: {'Success' if success else 'Failed'}")

if __name__ == "__main__":
    test_smartsheet_hyperlink() 