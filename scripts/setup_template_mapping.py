#!/usr/bin/env python3
"""
Utility script to set up Azure Table with template mappings.
This script helps populate the TemplateMapping table with initial data.
"""

import os
import sys
from typing import List, Dict, Any
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from storage import storage_client

# Load environment variables
load_dotenv()


def get_sample_template_data() -> List[Dict[str, str]]:
    """
    Get sample template data for seeding the table.
    
    Returns:
        List[Dict[str, str]]: Sample template data
    """
    return [
        {
            'category': 'Complex Design Build',
            'template_name': 'Standard Folder Structure',
            'template_folder_id': 'your_sharepoint_folder_item_id_1',
            'site_id': 'your_site_id_1',
            'drive_id': 'your_drive_id_1'
        },
        {
            'category': 'Complex Design Build',
            'template_name': 'Documentation Templates',
            'template_folder_id': 'your_sharepoint_folder_item_id_2',
            'site_id': 'your_site_id_2',
            'drive_id': 'your_drive_id_2'
        },
        {
            'category': 'Simple Design Build',
            'template_name': 'Basic Folder Structure',
            'template_folder_id': 'your_sharepoint_folder_item_id_3',
            'site_id': 'your_site_id_3',
            'drive_id': 'your_drive_id_3'
        },
        {
            'category': 'Simple Design Build',
            'template_name': 'Essential Documents',
            'template_folder_id': 'your_sharepoint_folder_item_id_4',
            'site_id': 'your_site_id_4',
            'drive_id': 'your_drive_id_4'
        },
        {
            'category': 'Consulting',
            'template_name': 'Consulting Project Structure',
            'template_folder_id': 'your_sharepoint_folder_item_id_5',
            'site_id': 'your_site_id_5',
            'drive_id': 'your_drive_id_5'
        },
        {
            'category': 'Maintenance',
            'template_name': 'Maintenance Project Structure',
            'template_folder_id': 'your_sharepoint_folder_item_id_6',
            'site_id': 'your_site_id_6',
            'drive_id': 'your_drive_id_6'
        }
    ]


def setup_template_mapping():
    """Set up the template mapping table with sample data."""
    try:
        print("Setting up Azure Table for template mappings...")
        
        # Create table if it doesn't exist
        if storage_client.create_table_if_not_exists():
            print("✅ Table created successfully or already exists")
        else:
            print("❌ Failed to create table")
            return False
        
        # Get sample data
        template_data = get_sample_template_data()
        
        print(f"Seeding table with {len(template_data)} template mappings...")
        
        # Seed the table
        if storage_client.seed_template_data(template_data):
            print("✅ Template data seeded successfully")
        else:
            print("❌ Failed to seed template data")
            return False
        
        # Verify the data
        print("\nVerifying template data...")
        categories = storage_client.list_categories()
        print(f"Found categories: {categories}")
        
        for category in categories:
            templates = storage_client.get_templates(category)
            print(f"  {category}: {len(templates)} templates")
            for template in templates:
                print(f"    - {template.row_key}: {template.template_folder_id}")
        
        print("\n✅ Template mapping setup completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error setting up template mapping: {e}")
        return False


def interactive_setup():
    """Interactive setup for template mappings."""
    print("Interactive Template Mapping Setup")
    print("=" * 40)
    
    templates = []
    
    while True:
        print("\nEnter template information (or 'done' to finish):")
        
        category = input("Project Category (e.g., 'Complex Design Build'): ").strip()
        if category.lower() == 'done':
            break
        
        template_name = input("Template Name (e.g., 'Standard Folder Structure'): ").strip()
        if template_name.lower() == 'done':
            break
        
        folder_id = input("SharePoint Folder ItemId: ").strip()
        if folder_id.lower() == 'done':
            break
        
        site_id = input("Site ID: ").strip()
        if site_id.lower() == 'done':
            break
        
        drive_id = input("Drive ID: ").strip()
        if drive_id.lower() == 'done':
            break
        
        templates.append({
            'category': category,
            'template_name': template_name,
            'template_folder_id': folder_id,
            'site_id': site_id,
            'drive_id': drive_id
        })
        
        print(f"✅ Added template: {category} - {template_name}")
    
    if templates:
        print(f"\nSeeding {len(templates)} templates...")
        if storage_client.seed_template_data(templates):
            print("✅ Templates added successfully!")
        else:
            print("❌ Failed to add templates")
    else:
        print("No templates to add.")


def main():
    """Main function."""
    print("BVC Smartsheet-SharePoint Automation - Template Mapping Setup")
    print("=" * 60)
    
    # Check if configuration is valid
    from config import config
    if not config.validate():
        print("❌ Configuration validation failed. Please check your .env file.")
        print("Required environment variables:")
        print("  - STORAGE_CONNECTION_STRING")
        return 1
    
    print("Configuration validated successfully!")
    
    # Ask user for setup type
    print("\nChoose setup type:")
    print("1. Sample data setup (recommended for testing)")
    print("2. Interactive setup (for production)")
    print("3. Exit")
    
    choice = input("\nEnter your choice (1-3): ").strip()
    
    if choice == '1':
        success = setup_template_mapping()
    elif choice == '2':
        interactive_setup()
        success = True
    elif choice == '3':
        print("Setup cancelled.")
        return 0
    else:
        print("Invalid choice.")
        return 1
    
    if success:
        print("\n🎉 Setup completed successfully!")
        print("\nNext steps:")
        print("1. Update the template_folder_id values with actual SharePoint folder IDs")
        print("2. Test the webhook with a sample 'Closed Won' deal")
        print("3. Monitor the Azure Function logs for any issues")
        return 0
    else:
        print("\n❌ Setup failed. Please check the error messages above.")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 