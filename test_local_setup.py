#!/usr/bin/env python3
"""
Local testing script for BVC Smartsheet-SharePoint Automation.
This script tests the Azure Table setup and allows you to test with real project data.
"""

import os
import sys
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

# Change to src directory for imports
os.chdir(src_path)

from config import config
from storage import storage_client
from graph_client import graph_client
from folder_manager import folder_manager
from onenote_manager import onenote_manager

# Change back to original directory
os.chdir(os.path.dirname(__file__))

def test_configuration():
    """Test that all configuration is properly loaded."""
    print("🔧 Testing Configuration...")
    print("-" * 40)
    
    # Test required environment variables
    required_vars = [
        'CLIENT_ID', 'CLIENT_SECRET', 'TENANT_ID', 'SMTSHEET_TOKEN',
        'STORAGE_CONNECTION_STRING', 'SHAREPOINT_SITE_ID'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = getattr(config, var, None)
        if not value:
            missing_vars.append(var)
        else:
            print(f"✅ {var}: {'*' * len(value)} (length: {len(value)})")
    
    if missing_vars:
        print(f"❌ Missing required variables: {missing_vars}")
        return False
    
    print("✅ All required configuration variables are set")
    return True

def test_storage_connection():
    """Test Azure Storage connection and table operations."""
    print("\n📦 Testing Azure Storage Connection...")
    print("-" * 40)
    
    try:
        # Test table creation
        if storage_client.create_table_if_not_exists():
            print("✅ Table created/verified successfully")
        else:
            print("❌ Failed to create table")
            return False
        
        # Test listing categories
        categories = storage_client.list_categories()
        print(f"✅ Found {len(categories)} categories: {categories}")
        
        return True
        
    except Exception as e:
        print(f"❌ Storage connection failed: {e}")
        return False

def test_graph_api_connection():
    """Test Microsoft Graph API connection."""
    print("\n🌐 Testing Microsoft Graph API Connection...")
    print("-" * 40)
    
    try:
        # Test token acquisition
        token = graph_client.get_access_token()
        print(f"✅ Graph API token acquired successfully (length: {len(token)})")
        
        # Test basic Graph API call
        site_info = graph_client.graph_request("GET", f"/sites/{config.SHAREPOINT_SITE_ID}")
        print(f"✅ SharePoint site info retrieved: {site_info.get('displayName', 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Graph API connection failed: {e}")
        return False

def test_folder_parsing():
    """Test SharePoint folder link parsing."""
    print("\n📁 Testing Folder Link Parsing...")
    print("-" * 40)
    
    # Use a real-world SharePoint URL provided by the user
    test_url = "https://bvcollective.sharepoint.com/sites/Opportunities/Shared%20Documents/General/LED%20Studio/Convention%20Center%20-%20Tree"
    try:
        drive_id, folder_id = folder_manager.parse_folder_link(test_url)
        print(f"✅ Parsed URL successfully")
        print(f"   Drive ID: {drive_id}")
        print(f"   Folder ID: {folder_id}")
        return True
    except Exception as e:
        print(f"❌ Folder parsing failed: {e}")
        print(f"   Note: This test requires a valid SharePoint folder URL")
        print(f"   You can test with a real URL in interactive mode")
        return False

def test_onenote_connection():
    """Test OneNote connection."""
    print("\n📓 Testing OneNote Connection...")
    print("-" * 40)
    
    try:
        # Test getting notebooks using delegated auth
        notebooks_response = graph_client.get_user_notebooks_delegated()
        notebooks = notebooks_response.get('value', [])
        print(f"✅ Found {len(notebooks)} OneNote notebooks")
        
        if notebooks:
            print("   Notebooks found:")
            for notebook in notebooks[:5]:  # Show first 5
                print(f"   - {notebook.get('displayName', 'Unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ OneNote connection failed: {e}")
        return False

def add_test_template(category: str, template_name: str, folder_id: str):
    """Add a test template to the Azure table."""
    print(f"\n➕ Adding Test Template...")
    print("-" * 40)
    
    try:
        success = storage_client.add_template(category, template_name, folder_id)
        if success:
            print(f"✅ Added template: {category} - {template_name}")
            return True
        else:
            print(f"❌ Failed to add template: {category} - {template_name}")
            return False
            
    except Exception as e:
        print(f"❌ Error adding template: {e}")
        return False

def test_project_workflow(company_name: str, project_name: str, project_category: str, folder_url: str):
    """Test the complete project workflow."""
    print(f"\n🚀 Testing Project Workflow...")
    print("-" * 40)
    print(f"Company: {company_name}")
    print(f"Project: {project_name}")
    print(f"Category: {project_category}")
    print(f"Folder URL: {folder_url}")
    
    try:
        # Step 1: Parse folder link
        print("\n1. Parsing folder link...")
        drive_id, parent_folder_id = folder_manager.parse_folder_link(folder_url)
        print(f"   ✅ Drive ID: {drive_id}")
        print(f"   ✅ Parent Folder ID: {parent_folder_id}")
        
        # Step 2: Get templates for category
        print("\n2. Getting templates for category...")
        templates = storage_client.get_templates(project_category)
        print(f"   ✅ Found {len(templates)} templates")
        
        for template in templates:
            print(f"   - {template.row_key}: {template.template_folder_id}")
        
        # Step 3: Test OneNote notebook and section creation
        print("\n3. Testing OneNote notebook and section creation...")
        section_result = onenote_manager.ensure_project_section(company_name, project_name)
        print(f"   ✅ Section: {section_result.get('displayName', 'Unknown')}")
        print(f"   ✅ Section ID: {section_result.get('id', 'Unknown')}")
        
        # Step 4: Test folder copying (simulation)
        print("\n4. Testing folder copying (simulation)...")
        if templates:
            print(f"   Would copy {len(templates)} templates:")
            for template in templates:
                folder_name = f"{template.row_key} - {project_name}"
                print(f"   - {folder_name}")
        else:
            print("   ⚠️  No templates found for this category")
        
        print("\n✅ Project workflow test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Project workflow test failed: {e}")
        return False

def interactive_test():
    """Interactive test mode."""
    print("\n🎯 Interactive Test Mode")
    print("=" * 50)
    
    while True:
        print("\nChoose an option:")
        print("1. Test configuration")
        print("2. Test storage connection")
        print("3. Test Graph API connection")
        print("4. Test folder parsing")
        print("5. Test OneNote connection")
        print("6. Add test template")
        print("7. Test complete project workflow")
        print("8. Run all tests")
        print("9. Exit")
        
        choice = input("\nEnter your choice (1-9): ").strip()
        
        if choice == '1':
            test_configuration()
        elif choice == '2':
            test_storage_connection()
        elif choice == '3':
            test_graph_api_connection()
        elif choice == '4':
            test_folder_parsing()
        elif choice == '5':
            test_onenote_connection()
        elif choice == '6':
            category = input("Enter project category: ").strip()
            template_name = input("Enter template name: ").strip()
            folder_id = input("Enter SharePoint folder ID: ").strip()
            add_test_template(category, template_name, folder_id)
        elif choice == '7':
            company_name = input("Enter company name: ").strip()
            project_name = input("Enter project name: ").strip()
            project_category = input("Enter project category: ").strip()
            folder_url = input("Enter SharePoint folder URL: ").strip()
            test_project_workflow(company_name, project_name, project_category, folder_url)
        elif choice == '8':
            run_all_tests()
        elif choice == '9':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

def run_all_tests():
    """Run all tests in sequence."""
    print("\n🧪 Running All Tests...")
    print("=" * 50)
    
    tests = [
        ("Configuration", test_configuration),
        ("Storage Connection", test_storage_connection),
        ("Graph API Connection", test_graph_api_connection),
        ("Folder Parsing", test_folder_parsing),
        ("OneNote Connection", test_onenote_connection)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\nRunning {test_name} test...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n📊 Test Results Summary:")
    print("-" * 30)
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Your setup is ready for Azure deployment.")
    else:
        print("⚠️  Some tests failed. Please fix the issues before deploying.")

def main():
    """Main function."""
    print("🚀 BVC Smartsheet-SharePoint Automation - Local Testing")
    print("=" * 60)
    
    # Check if running in interactive mode
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        interactive_test()
        return
    
    # Run all tests by default
    run_all_tests()
    
    # Option to run interactive mode
    print("\n" + "=" * 60)
    choice = input("Would you like to run interactive tests? (y/n): ").strip().lower()
    if choice == 'y':
        interactive_test()

if __name__ == "__main__":
    main() 
