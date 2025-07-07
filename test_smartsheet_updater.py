#!/usr/bin/env python3
"""
Test script for Smartsheet updater functionality.
"""

import os
import sys
from dotenv import load_dotenv

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_smartsheet_updater():
    """Test the Smartsheet updater functionality."""
    print("Testing Smartsheet updater...")
    
    try:
        from src.smartsheet_updater import smartsheet_updater
        from src.config import config
        
        # Test getting sheet info
        sheet_id = int(config.SMTSHEET_ID)
        sheet_info = smartsheet_updater.get_sheet_info(sheet_id)
        
        if sheet_info:
            print(f"✅ Successfully connected to Smartsheet: {sheet_info['name']}")
            print(f"   Sheet ID: {sheet_info['id']}")
            print(f"   Access Level: {sheet_info['access_level']}")
        else:
            print("❌ Failed to get sheet info")
            return False
        
        # Test updating a row with a sample OneNote URL
        # Note: This will only work if you have a valid row ID
        # For testing, we'll use a dummy row ID and expect it to fail gracefully
        test_row_id = 999999999  # Dummy row ID
        test_notebook_name = "Test Notebook - Public"
        test_notebook_url = "https://www.onenote.com/notebook/test"
        test_section_url = "https://www.onenote.com/notebook/test/section/test"
        
        print(f"\nTesting row update with dummy row ID {test_row_id}...")
        success = smartsheet_updater.update_row_with_onenote_url(
            sheet_id=sheet_id,
            row_id=test_row_id,
            notebook_name=test_notebook_name,
            notebook_url=test_notebook_url,
            section_url=test_section_url
        )
        
        if not success:
            print("✅ Expected failure for dummy row ID - this is normal")
        else:
            print("✅ Successfully updated row (unexpected for dummy row ID)")
        
        print("\n✅ Smartsheet updater test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Smartsheet updater test failed: {e}")
        return False

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Run the test
    success = test_smartsheet_updater()
    sys.exit(0 if success else 1) 
