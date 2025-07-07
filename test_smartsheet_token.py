import os
import logging
from dotenv import load_dotenv
import smartsheet

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_smartsheet_token():
    """Test Smartsheet token for both read and write operations."""
    
    # Get token from environment
    token = os.getenv('SMTSHEET_TOKEN')
    sheet_id = os.getenv('SMTSHEET_ID')
    
    if not token:
        logger.error("SMTSHEET_TOKEN not found in environment")
        return False
    
    if not sheet_id:
        logger.error("SMTSHEET_ID not found in environment")
        return False
    
    logger.info(f"Token length: {len(token)}")
    logger.info(f"Token starts with: {token[:10]}...")
    logger.info(f"Sheet ID: {sheet_id}")
    
    try:
        # Initialize client
        client = smartsheet.Smartsheet(token)
        client.errors_as_exceptions(True)
        
        # Test 1: Read operation (get sheet info)
        logger.info("Testing READ operation...")
        sheet = client.Sheets.get_sheet(int(sheet_id))
        logger.info(f"✅ READ successful - Sheet name: {sheet.name}")
        
        # Test 2: Write operation (try to update a cell)
        logger.info("Testing WRITE operation...")
        
        # Get the first row to test with
        if not sheet.rows:
            logger.error("No rows found in sheet for testing")
            return False
        
        test_row = sheet.rows[0]
        logger.info(f"Testing with row ID: {test_row.id}")
        
        # Try to update a cell (we'll use a column that exists)
        if not test_row.cells:
            logger.error("No cells found in test row")
            return False
        
        test_cell = test_row.cells[0]
        column_id = test_cell.column_id
        
        # Create a test update (we'll just set the same value to avoid changing data)
        cell_update = smartsheet.models.Cell({
            'column_id': column_id,
            'value': test_cell.value  # Keep the same value
        })
        
        row_update = smartsheet.models.Row({
            'id': test_row.id,
            'cells': [cell_update]
        })
        
        # Attempt the update
        response = client.Sheets.update_rows(int(sheet_id), [row_update])
        
        if response.message == 'SUCCESS':
            logger.info("✅ WRITE successful - Row updated successfully")
            return True
        else:
            logger.error(f"❌ WRITE failed - Response: {response.message}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed with exception: {e}")
        return False

if __name__ == "__main__":
    success = test_smartsheet_token()
    if success:
        print("\n🎉 Smartsheet token test PASSED - both read and write operations work!")
    else:
        print("\n❌ Smartsheet token test FAILED - check the logs above") 