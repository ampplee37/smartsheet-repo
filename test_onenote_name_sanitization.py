#!/usr/bin/env python3
"""
Test script to verify OneNote name sanitization functions.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from onenote_manager import get_cell_str, sanitize_onenote_name

def test_cell_str_extraction():
    """Test extracting string values from Smartsheet cells."""
    print("Testing cell string extraction...")
    
    # Test with dict cell
    cell_dict = {'value': 'Test Company', 'displayValue': 'Test Company', 'hyperlink': None}
    result = get_cell_str(cell_dict)
    print(f"Dict cell: {cell_dict} -> '{result}'")
    assert result == 'Test Company'
    
    # Test with string
    cell_str = 'Simple String'
    result = get_cell_str(cell_str)
    print(f"String cell: '{cell_str}' -> '{result}'")
    assert result == 'Simple String'
    
    # Test with None
    cell_none = None
    result = get_cell_str(cell_none)
    print(f"None cell: {cell_none} -> '{result}'")
    assert result == ''
    
    print("✓ Cell string extraction tests passed\n")

def test_name_sanitization():
    """Test sanitizing names for OneNote."""
    print("Testing name sanitization...")
    
    # Test normal name
    name = "Test Company"
    result = sanitize_onenote_name(name)
    print(f"Normal name: '{name}' -> '{result}'")
    assert result == "Test Company"
    
    # Test with forbidden characters
    name_with_chars = "Test?Company*with\\forbidden:chars<in>name|with'quotes"
    result = sanitize_onenote_name(name_with_chars)
    print(f"Name with forbidden chars: '{name_with_chars}' -> '{result}'")
    assert result == "TestCompanywithforbiddencharsinnamewithquotes"
    
    # Test empty string
    name_empty = ""
    result = sanitize_onenote_name(name_empty)
    print(f"Empty name: '{name_empty}' -> '{result}'")
    assert result == "Untitled"
    
    # Test None
    name_none = None
    result = sanitize_onenote_name(name_none)
    print(f"None name: {name_none} -> '{result}'")
    assert result == "Untitled"
    
    # Test with only whitespace
    name_whitespace = "   \t\n  "
    result = sanitize_onenote_name(name_whitespace)
    print(f"Whitespace name: '{name_whitespace}' -> '{result}'")
    assert result == "Untitled"
    
    print("✓ Name sanitization tests passed\n")

def test_integration():
    """Test the full integration of cell extraction and sanitization."""
    print("Testing integration...")
    
    # Simulate the real scenario from the logs
    smartsheet_data = {
        '1475623376867204': {'value': 'Allbridge', 'displayValue': 'Allbridge', 'hyperlink': None},  # Company
        '3534360453271428': {'value': 'LV with FLS Peer Review and Stamp', 'displayValue': 'LV with FLS Peer Review and Stamp', 'hyperlink': None},  # Project
        '3408182019051396': {'value': '000115', 'displayValue': '000115', 'hyperlink': None}  # Opportunity ID
    }
    
    # Extract company name
    company_cell = smartsheet_data.get('1475623376867204')
    company_str = get_cell_str(company_cell)
    notebook_name = f"{sanitize_onenote_name(company_str)} - Public"
    print(f"Company: {company_cell} -> '{company_str}' -> '{notebook_name}'")
    
    # Extract project and opportunity info
    project_cell = smartsheet_data.get('3534360453271428')
    opp_cell = smartsheet_data.get('3408182019051396')
    
    project_str = get_cell_str(project_cell)
    opp_str = get_cell_str(opp_cell)
    
    if opp_str:
        section_name = f"{opp_str} - {project_str}"
    else:
        section_name = project_str
    
    section_name = sanitize_onenote_name(section_name)
    print(f"Section: opp='{opp_str}', project='{project_str}' -> '{section_name}'")
    
    # Verify the results
    expected_notebook = "Allbridge - Public"
    expected_section = "000115 - LV with FLS Peer Review and Stamp"
    
    assert notebook_name == expected_notebook, f"Expected '{expected_notebook}', got '{notebook_name}'"
    assert section_name == expected_section, f"Expected '{expected_section}', got '{section_name}'"
    
    print("✓ Integration tests passed\n")

if __name__ == "__main__":
    print("Running OneNote name sanitization tests...\n")
    
    try:
        test_cell_str_extraction()
        test_name_sanitization()
        test_integration()
        
        print("🎉 All tests passed! The OneNote name sanitization is working correctly.")
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 