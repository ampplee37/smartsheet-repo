import os
import logging
import smartsheet
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_hyperlink_formats():
    """Test different formats for creating hyperlinks in Smartsheet."""
    
    token = os.getenv('SMTSHEET_TOKEN')
    sheet_id = os.getenv('SMTSHEET_ID')
    column_id = 3086497829048196  # Public Notebook column
    
    if not token or not sheet_id:
        logger.error("Missing SMTSHEET_TOKEN or SMTSHEET_ID")
        return False
    
    # Get a test row
    client = smartsheet.Smartsheet(token)
    client.errors_as_exceptions(True)
    
    try:
        sheet = client.Sheets.get_sheet(int(sheet_id))
        if not sheet.rows:
            logger.error("No rows found for testing")
            return False
        
        test_row = sheet.rows[0]
        logger.info(f"Testing with row ID: {test_row.id}")
        
        # Test 1: Using SDK models (current approach)
        logger.info("\n=== Test 1: SDK Models Approach ===")
        try:
            cell_update = smartsheet.models.Cell({
                'column_id': column_id,
                'value': 'Test Notebook Name',
                'hyperlink': {
                    'url': 'https://example.com/test'
                }
            })
            
            row_update = smartsheet.models.Row({
                'id': test_row.id,
                'cells': [cell_update]
            })
            
            response = client.Sheets.update_rows(int(sheet_id), [row_update])
            logger.info(f"SDK Models result: {response.message}")
            
        except Exception as e:
            logger.error(f"SDK Models failed: {e}")
        
        # Test 2: Using raw API format (like your working example)
        logger.info("\n=== Test 2: Raw API Format ===")
        try:
            raw_payload = {
                "id": test_row.id,
                "cells": [
                    {
                        "columnId": column_id,
                        "value": "Test Notebook Name",
                        "hyperlink": {
                            "url": "https://example.com/test"
                        }
                    }
                ]
            }
            
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            url = f"https://api.smartsheet.com/2.0/sheets/{sheet_id}/rows"
            response = requests.put(url, headers=headers, json=raw_payload)
            
            logger.info(f"Raw API status: {response.status_code}")
            logger.info(f"Raw API response: {response.text}")
            
        except Exception as e:
            logger.error(f"Raw API failed: {e}")
        
        # Test 3: Check current cell value
        logger.info("\n=== Test 3: Check Current Cell Value ===")
        for cell in test_row.cells:
            if cell.column_id == column_id:
                logger.info(f"Current value: {cell.value}")
                if hasattr(cell, 'hyperlink'):
                    logger.info(f"Current hyperlink: {cell.hyperlink}")
                break
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_hyperlink_formats()
    if success:
        print("\n🎉 Hyperlink format test completed")
    else:
        print("\n❌ Hyperlink format test failed") 