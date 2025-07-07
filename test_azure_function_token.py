import os
import logging
from dotenv import load_dotenv
import smartsheet

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_azure_function_environment():
    """Test how the Azure Function would load and use the Smartsheet token."""
    
    # Simulate Azure Function environment loading
    # Azure Functions load environment variables differently than dotenv
    
    # Method 1: Direct environment variable (like Azure Functions)
    direct_token = os.getenv('SMTSHEET_TOKEN')
    direct_sheet_id = os.getenv('SMTSHEET_ID')
    
    logger.info("=== Testing Direct Environment Variables (Azure Function Style) ===")
    logger.info(f"Direct token length: {len(direct_token) if direct_token else 0}")
    logger.info(f"Direct token starts with: {direct_token[:10] if direct_token else 'None'}...")
    logger.info(f"Direct sheet ID: {direct_sheet_id}")
    
    # Method 2: With dotenv loading (like local development)
    load_dotenv()
    dotenv_token = os.getenv('SMTSHEET_TOKEN')
    dotenv_sheet_id = os.getenv('SMTSHEET_ID')
    
    logger.info("\n=== Testing with dotenv Loading (Local Development Style) ===")
    logger.info(f"dotenv token length: {len(dotenv_token) if dotenv_token else 0}")
    logger.info(f"dotenv token starts with: {dotenv_token[:10] if dotenv_token else 'None'}...")
    logger.info(f"dotenv sheet ID: {dotenv_sheet_id}")
    
    # Compare tokens
    if direct_token == dotenv_token:
        logger.info("\n✅ Tokens are identical")
        test_token = direct_token
    else:
        logger.warning("\n❌ Tokens are different!")
        logger.info(f"Direct token: {direct_token}")
        logger.info(f"dotenv token: {dotenv_token}")
        # Use the dotenv token for testing since that's what works locally
        test_token = dotenv_token
    
    if not test_token:
        logger.error("No valid token found")
        return False
    
    # Test the token
    try:
        client = smartsheet.Smartsheet(test_token)
        client.errors_as_exceptions(True)
        
        # Test read operation
        logger.info("\n=== Testing READ Operation ===")
        sheet = client.Sheets.get_sheet(int(dotenv_sheet_id))
        logger.info(f"✅ READ successful - Sheet name: {sheet.name}")
        
        # Test write operation
        logger.info("\n=== Testing WRITE Operation ===")
        if not sheet.rows:
            logger.error("No rows found for testing")
            return False
        
        test_row = sheet.rows[0]
        test_cell = test_row.cells[0]
        
        cell_update = smartsheet.models.Cell({
            'column_id': test_cell.column_id,
            'value': test_cell.value
        })
        
        row_update = smartsheet.models.Row({
            'id': test_row.id,
            'cells': [cell_update]
        })
        
        response = client.Sheets.update_rows(int(dotenv_sheet_id), [row_update])
        
        if response.message == 'SUCCESS':
            logger.info("✅ WRITE successful")
            return True
        else:
            logger.error(f"❌ WRITE failed: {response.message}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_azure_function_environment()
    if success:
        print("\n🎉 Environment test PASSED")
    else:
        print("\n❌ Environment test FAILED") 