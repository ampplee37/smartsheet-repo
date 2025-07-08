"""
OneNote management operations.
Handles creating and managing OneNote notebooks and sections.
"""

import logging
import re
from typing import Dict, Any, Optional, List
import json
try:
    from .graph_client import graph_client
    from .config import config
except ImportError:
    from graph_client import graph_client
    from config import config

logger = logging.getLogger(__name__)


def get_cell_str(cell) -> str:
    """
    Extract string value from a Smartsheet cell.
    
    Args:
        cell: Cell value from Smartsheet (can be dict, string, or other types)
        
    Returns:
        str: String value from the cell
    """
    if isinstance(cell, dict):
        return cell.get('displayValue') or cell.get('value') or ''
    return str(cell) if cell is not None else ''


def sanitize_onenote_name(name: str) -> str:
    """
    Sanitize a name for use in OneNote notebooks and sections.
    Removes forbidden characters: ? * \ / : < > | '
    
    Args:
        name: Original name
        
    Returns:
        str: Sanitized name
    """
    if not name:
        return 'Untitled'
    
    # Remove forbidden characters: ? * \ / : < > | '
    sanitized = re.sub(r"[?*\\\\/:<>|']", "", name)
    
    # Remove leading/trailing whitespace
    sanitized = sanitized.strip()
    
    # If empty after sanitization, use default
    if not sanitized:
        return 'Untitled'
    
    return sanitized


def get_display_text(cell):
    """
    Extract the display value for a cell, or value, or empty string.
    If the cell has a hyperlink, return an HTML link.
    If the value looks like an email, return a mailto link.
    """
    if isinstance(cell, dict):
        display = cell.get('displayValue') or cell.get('value') or ''
        hyperlink = cell.get('hyperlink')
        # If hyperlink is a dict with a url, render as a link
        if hyperlink and isinstance(hyperlink, dict) and hyperlink.get('url'):
            url = hyperlink['url']
            label = display or hyperlink.get('label') or url
            return f'<a href="{url}">{label}</a>'
        # If value looks like an email, render as mailto
        value = cell.get('value')
        if value and isinstance(value, str) and '@' in value and not display:
            return f'<a href="mailto:{value}">{value}</a>'
        return display
    elif isinstance(cell, str) and '@' in cell:
        return f'<a href="mailto:{cell}">{cell}</a>'
    return str(cell) if cell is not None else ''


class OneNoteManager:
    """Manages OneNote notebook and section operations."""
    
    def __init__(self):
        """Initialize the OneNote manager."""
        self.site_id = config.SHAREPOINT_SITE_ID
    
    def ensure_notebook(self, company_name: str) -> Dict[str, Any]:
        """
        Ensure a OneNote notebook exists for the company, create if it doesn't.
        
        Args:
            company_name: Company name for the notebook
            
        Returns:
            Dict[str, Any]: Notebook information
            
        Raises:
            Exception: If notebook creation fails
        """
        try:
            # First, check if notebook already exists
            existing_notebook = self.get_notebook_by_name(company_name)
            
            if existing_notebook:
                logger.info(f"OneNote notebook '{company_name}' already exists")
                return existing_notebook
            
            # Create new notebook using delegated authentication
            logger.info(f"Creating OneNote notebook for company: {company_name}")
            notebook = graph_client.create_notebook_delegated(
                display_name=company_name
            )
            
            logger.info(f"Successfully created OneNote notebook: {notebook.get('id')}")
            return notebook
            
        except Exception as e:
            logger.error(f"Failed to ensure notebook for company '{company_name}': {e}")
            raise
    
    def get_notebook_by_name(self, display_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a OneNote notebook by display name using delegated authentication.
        
        Args:
            display_name: Notebook display name
            
        Returns:
            Optional[Dict[str, Any]]: Notebook information if found, None otherwise
        """
        try:
            notebooks_response = graph_client.get_user_notebooks_delegated(
                display_name=display_name
            )
            
            notebooks = notebooks_response.get('value', [])
            
            if notebooks:
                logger.info(f"Found existing notebook '{display_name}' with ID: {notebooks[0].get('id')}")
                return notebooks[0]
            else:
                logger.info(f"No existing notebook found with name '{display_name}'")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get notebook by name '{display_name}': {e}")
            return None
    
    def create_section(
        self, 
        notebook_id: str, 
        section_name: str
    ) -> Dict[str, Any]:
        """
        Create a new section in a OneNote notebook using delegated authentication.
        
        Args:
            notebook_id: OneNote notebook ID
            section_name: Section name
            
        Returns:
            Dict[str, Any]: Created section information
            
        Raises:
            Exception: If section creation fails
        """
        try:
            logger.info(f"Creating OneNote section '{section_name}' in notebook {notebook_id}")
            
            section = graph_client.create_notebook_section_delegated(
                notebook_id=notebook_id,
                section_name=section_name
            )
            
            logger.info(f"Successfully created OneNote section: {section.get('id')}")
            return section
            
        except Exception as e:
            logger.error(f"Failed to create section '{section_name}' in notebook {notebook_id}: {e}")
            raise
    
    def ensure_project_section(self, company_name: str, project_name: str) -> Dict[str, Any]:
        """
        Ensure a project section exists in the company's OneNote notebook.
        
        Args:
            company_name: Company name (for notebook)
            project_name: Project name (for section)
            
        Returns:
            Dict[str, Any]: Section information
            
        Raises:
            Exception: If section creation fails
        """
        try:
            # First ensure the notebook exists
            notebook = self.ensure_notebook(company_name)
            notebook_id = notebook.get('id')
            
            if not notebook_id:
                raise Exception("Failed to get notebook ID")
            
            # Check if section already exists
            existing_section = self.get_section_by_name(notebook_id, project_name)
            if existing_section:
                logger.info(f"Section '{project_name}' already exists in notebook '{company_name}'")
                return existing_section
            
            # Create a section with the project name
            section = self.create_section(
                notebook_id=notebook_id,
                section_name=project_name
            )
            
            logger.info(f"Successfully ensured project section '{project_name}' in notebook '{company_name}'")
            return section
            
        except Exception as e:
            logger.error(f"Failed to ensure project section '{project_name}' in notebook '{company_name}': {e}")
            raise
    
    def get_notebook_sections(self, notebook_id: str) -> List[Dict[str, Any]]:
        """
        Get all sections in a OneNote notebook using delegated authentication.
        
        Args:
            notebook_id: OneNote notebook ID
            
        Returns:
            List[Dict[str, Any]]: List of sections
            
        Raises:
            Exception: If retrieval fails
        """
        try:
            response = graph_client.get_notebook_sections_delegated(notebook_id)
            
            sections = response.get('value', [])
            logger.info(f"Retrieved {len(sections)} sections from notebook {notebook_id}")
            return sections
            
        except Exception as e:
            logger.error(f"Failed to get sections for notebook {notebook_id}: {e}")
            raise
    
    def get_section_by_name(self, notebook_id: str, section_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific section by name in a notebook.
        
        Args:
            notebook_id: OneNote notebook ID
            section_name: Section name
            
        Returns:
            Optional[Dict[str, Any]]: Section information if found, None otherwise
        """
        try:
            sections = self.get_notebook_sections(notebook_id)
            
            for section in sections:
                if section.get('displayName') == section_name:
                    logger.info(f"Found section '{section_name}' with ID: {section.get('id')}")
                    return section
            
            logger.info(f"No section found with name '{section_name}' in notebook {notebook_id}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get section by name '{section_name}': {e}")
            return None
    
    def create_project_notebook_with_sections(
        self, 
        project_name: str, 
        section_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a complete OneNote notebook for a project with multiple sections.
        
        Args:
            project_name: Project name
            section_names: List of section names to create (defaults to project name)
            
        Returns:
            Dict[str, Any]: Created notebook information with sections
        """
        try:
            if section_names is None:
                section_names = [project_name]
            
            # Create the notebook
            notebook = self.ensure_notebook(project_name)
            notebook_id = notebook.get('id')
            
            if not notebook_id:
                raise Exception("Failed to get notebook ID")
            
            # Create sections
            sections = []
            for section_name in section_names:
                try:
                    section = self.create_section(notebook_id, section_name)
                    sections.append(section)
                except Exception as e:
                    logger.error(f"Failed to create section '{section_name}': {e}")
                    # Continue with other sections
            
            result = {
                'notebook': notebook,
                'sections': sections,
                'project_name': project_name
            }
            
            logger.info(f"Successfully created notebook with {len(sections)} sections for project '{project_name}'")
            return result
            
        except Exception as e:
            logger.error(f"Failed to create project notebook for '{project_name}': {e}")
            raise
    
    def list_all_notebooks(self) -> List[Dict[str, Any]]:
        """
        List all OneNote notebooks in the SharePoint site.
        
        Returns:
            List[Dict[str, Any]]: List of all notebooks
            
        Raises:
            Exception: If retrieval fails
        """
        try:
            response = graph_client.get_site_notebooks(site_id=self.site_id)
            notebooks = response.get('value', [])
            
            logger.info(f"Retrieved {len(notebooks)} notebooks from site {self.site_id}")
            return notebooks
            
        except Exception as e:
            logger.error(f"Failed to list notebooks: {e}")
            raise
    
    def delete_notebook(self, notebook_id: str) -> bool:
        """
        Delete a OneNote notebook using delegated authentication.
        
        Args:
            notebook_id: OneNote notebook ID
            
        Returns:
            bool: True if successful, False otherwise
            
        Raises:
            Exception: If deletion fails
        """
        try:
            endpoint = f"/sites/{self.site_id}/onenote/notebooks/{notebook_id}"
            graph_client.graph_request_delegated("DELETE", endpoint)
            
            logger.info(f"Successfully deleted notebook {notebook_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete notebook {notebook_id}: {e}")
            raise
    
    def create_standard_project_notebook(self, project_name: str) -> Dict[str, Any]:
        """
        Create a standard OneNote notebook structure for a project.
        
        Args:
            project_name: Project name
            
        Returns:
            Dict[str, Any]: Created notebook information
        """
        # Define standard sections for BVC projects
        standard_sections = [
            "Project Overview",
            "Requirements",
            "Design",
            "Development",
            "Testing",
            "Deployment",
            "Documentation",
            "Meeting Notes"
        ]
        
        return self.create_project_notebook_with_sections(project_name, standard_sections)

    def _format_notebook_name(self, customer_name) -> str:
        """
        Format the OneNote notebook name as '<Customer> - Public'.
        
        Args:
            customer_name: Customer name (can be string, dict, or other types)
            
        Returns:
            str: Formatted and sanitized notebook name
        """
        # Extract string value from cell if it's a dict
        customer_str = get_cell_str(customer_name)
        
        # Sanitize the name
        sanitized_customer = sanitize_onenote_name(customer_str)
        
        # Format as "Customer - Public"
        notebook_name = f"{sanitized_customer} - Public"
        
        logger.info(f"Formatted notebook name: '{customer_str}' -> '{notebook_name}'")
        return notebook_name

    def ensure_project_section_with_metadata(self, site_id: str, parent_folder_id: str, notebook_name: str, section_name: str, smartsheet_data: dict) -> Dict[str, Any]:
        """
        Ensure a OneNote notebook exists at the site level (not in a subfolder), create if it doesn't, or add a section if it does. Then create a page in the section with Smartsheet data.
        Args:
            site_id: SharePoint Site ID
            parent_folder_id: (ignored for notebook creation, kept for compatibility)
            notebook_name: Name for the notebook
            section_name: Name for the section
            smartsheet_data: Dict of key-value pairs to add to the page
        Returns:
            Dict[str, Any]: Notebook, section, and page information
        Raises:
            Exception: If section or page creation fails
        """
        logger.info(f"Raw Smartsheet data for page: {json.dumps(smartsheet_data, indent=2)}")
        try:
            # Always use customer name + ' - Public' for the notebook name
            customer_name = smartsheet_data.get('1475623376867204', notebook_name)
            notebook_name = self._format_notebook_name(customer_name)
            
            # Format and sanitize the section name
            project_name = smartsheet_data.get('3534360453271428', section_name)  # Project Name
            opp_id = smartsheet_data.get('3408182019051396', '')  # Opportunity ID
            
            # Extract string values and sanitize
            project_str = get_cell_str(project_name)
            opp_str = get_cell_str(opp_id)
            
            # Build section name as "Opp ID - ProjectName" (reversed format)
            if opp_str:
                section_name = f"{opp_str} - {project_str}"
            else:
                section_name = project_str
            
            # Sanitize the section name
            section_name = sanitize_onenote_name(section_name)
            
            logger.info(f"Formatted section name: '{section_name}'")
            
            # The notebook will be created at the site level, named after the folder/project
            # Check if notebook exists at the site level
            notebooks_response = graph_client.get_site_notebooks(site_id=site_id)
            notebooks = notebooks_response.get('value', [])
            notebook = next((nb for nb in notebooks if nb.get('displayName') == notebook_name), None)
            if not notebook:
                logger.info(f"Creating OneNote notebook at site level: /sites/{site_id}/onenote/notebooks with displayName: {notebook_name}")
                try:
                    notebook = graph_client.create_notebook(site_id, notebook_name)
                except Exception as e:
                    # If 409, try to find the notebook again (it may have just been created or already existed)
                    response = getattr(e, 'response', None)
                    status_code = getattr(response, 'status_code', None) if response is not None else None
                    if status_code == 409:
                        logger.warning(f"409 Conflict: Notebook already exists at site level, searching for existing notebook '{notebook_name}'")
                        notebooks_response = graph_client.get_site_notebooks(site_id=site_id)
                        notebooks = notebooks_response.get('value', [])
                        notebook = next((nb for nb in notebooks if nb.get('displayName') == notebook_name), None)
                        if not notebook:
                            logger.error(f"Notebook exists but could not be found after 409: {notebook_name}")
                            raise Exception(f"Notebook exists but could not be found: {notebook_name}")
                    else:
                        logger.error(f"Failed to create notebook at site level: {e}")
                        raise
            notebook_id = notebook.get('id')
            if not notebook_id:
                raise Exception("Failed to get notebook ID")
            # Check if section already exists using site-based endpoint
            existing_section = self.get_section_by_name_site(site_id, notebook_id, section_name)
            if existing_section:
                logger.info(f"Section '{section_name}' already exists in notebook '{notebook_name}'")
                section = existing_section
            else:
                # Create a section with the section name using site-based endpoint
                logger.info(f"Calling Graph API: /sites/{site_id}/onenote/notebooks/{notebook_id}/sections with displayName: {section_name}")
                section = graph_client.create_site_notebook_section(
                    site_id=site_id,
                    notebook_id=notebook_id,
                    section_name=section_name
                )
                logger.info(f"Successfully created project section '{section_name}' in notebook '{notebook_name}'")
            section_id = section.get('id')
            if not section_id:
                raise Exception("Failed to get section ID")
            # Build the page title as '{OpportunityID} - {ProjectName}' (reversed format)
            # Use the already extracted and sanitized values
            page_title = f"{opp_str} - {project_str}" if opp_str else project_str
            
            # Check if a page with this title already exists in the section
            existing_page = self.get_page_by_title_site(site_id, section_id, page_title)
            if existing_page:
                logger.info(f"Page with title '{page_title}' already exists in section '{section_name}', skipping page creation")
                page = existing_page
            else:
                # Create a page in the section with a two-column table of smartsheet_data
                page_html = self._build_two_column_table_html(page_title, smartsheet_data)
                logger.info(f"Creating page in section '{section_name}' with Smartsheet data table")
                page = graph_client.create_page_in_section(site_id, section_id, page_html)
                logger.info(f"Successfully created page in section '{section_name}'")
            
            # Extract URLs from the responses
            notebook_url = None
            section_url = None
            
            # Get notebook URL from links
            if notebook.get('links') and notebook['links'].get('oneNoteWebUrl'):
                notebook_url = notebook['links']['oneNoteWebUrl']['href']
                logger.info(f"Notebook URL: {notebook_url}")
            
            # Get section URL from links
            if section.get('links') and section['links'].get('oneNoteWebUrl'):
                section_url = section['links']['oneNoteWebUrl']['href']
                logger.info(f"Section URL: {section_url}")
            
            return {
                'notebook': notebook,
                'section': section,
                'page': page,
                'notebook_url': notebook_url,
                'section_url': section_url,
                'notebook_name': notebook_name
            }
        except Exception as e:
            logger.error(f"Failed to ensure project section '{section_name}' in notebook '{notebook_name}': {e}")
            raise

    def _clean_text_for_onenote(self, text, page_title=None):
        if not isinstance(text, str):
            return text
        # Remove all actual newlines, carriage returns, and literal \n (single and double-escaped)
        text = text.replace('\r\n', ' ').replace('\n', ' ').replace('\n', ' ').replace('\r', ' ').replace('\n', ' ')
        # Remove any repeated whitespace
        text = re.sub(r'\\n+', ' ', text)
        text = re.sub(r'\\+', '', text)
        # Split into lines, filter out lines that are empty, just quotes, or match the page title
        lines = [line.strip() for line in text.split(' ') if line.strip() and line.strip() not in ['"', "'"]]
        if page_title:
            lines = [line for line in lines if line != page_title]
        # Remove lines that are just a sequence of n's (e.g., nnnnn)
        lines = [line for line in lines if not re.fullmatch(r'n+', line)]
        return ' '.join(lines)

    def _build_two_column_table_html(self, title, data):
        logger = logging.getLogger(__name__)
        # Mapping of Smartsheet column IDs to friendly names (now includes RFP Scope and DE Consulting Scope)
        COLUMNS = [
            ("5878702367002500", "Project Category"),
            ("3534360453271428", "Project Name"),
            ("1375102739632004", "Description"),
            ("1475623376867204", "Company Name"),
            ("7911781646421892", "Customer Contact"),
            ("1611314616291204", "Site Address"),
            ("3408182019051396", "Opportunity ID"),
            ("677356797906820", "RFP Scope"),
            ("1639045752639364", "DE Consulting Scope"),
        ]
        # Clean the title and values as before
        title = self._clean_text_for_onenote(title)
        rows = ""
        for col_id, friendly_name in COLUMNS:
            raw_value = data.get(col_id, "")
            logger.debug(f"Raw value for {friendly_name} ({col_id}): {repr(raw_value)}")
            # Special handling for DE Consulting Scope (multi-select)
            if col_id == "1639045752639364":
                value = raw_value
                # If value is a dict with a list, join the list
                if isinstance(value, dict):
                    v = value.get('displayValue') or value.get('value')
                    if isinstance(v, list):
                        value = ', '.join(str(item) for item in v)
                    else:
                        value = v or ''
                elif isinstance(value, list):
                    value = ', '.join(str(item) for item in value)
                else:
                    value = get_display_text(value)
            else:
                value = get_display_text(raw_value)
            logger.debug(f"Display value for {friendly_name}: {repr(value)}")
            rows += f"<tr><td>{friendly_name}</td><td>{value}</td></tr>"
        html = f"""
<!DOCTYPE html>
<html>
<head>
  <title>{title}</title>
  <meta charset='utf-8' />
</head>
<body>
  <table border='1' cellpadding='5' style='border-collapse:collapse;'>
    <thead>
      <tr><th>Field</th><th>Value</th></tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>
</body>
</html>
"""
        import re
        # Minify HTML: remove all newlines, carriage returns, and whitespace between tags
        html = re.sub(r"[\r\n]+", "", html)
        html = re.sub(r">\s+<", "><", html)
        html = html.strip()
        # Remove only leading/trailing quotes
        if html.startswith('"'):
            html = html[1:]
        if html.endswith('"'):
            html = html[:-1]
        logger.info(f"Final HTML for OneNote page:\n{html}")
        return html

    def get_section_by_name_site(self, site_id: str, notebook_id: str, section_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific section by name in a site notebook.
        
        Args:
            site_id: SharePoint site ID
            notebook_id: OneNote notebook ID
            section_name: Section name
            
        Returns:
            Optional[Dict[str, Any]]: Section information if found, None otherwise
        """
        try:
            response = graph_client.get_site_notebook_sections(site_id, notebook_id)
            sections = response.get('value', [])
            
            for section in sections:
                if section.get('displayName') == section_name:
                    logger.info(f"Found section '{section_name}' with ID: {section.get('id')}")
                    return section
            
            logger.info(f"No section found with name '{section_name}' in notebook {notebook_id}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get section by name '{section_name}' in site notebook: {e}")
            return None

    def get_page_by_title_site(self, site_id: str, section_id: str, page_title: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific page by title in a site notebook section.
        
        Args:
            site_id: SharePoint site ID
            section_id: OneNote section ID
            page_title: Page title
            
        Returns:
            Optional[Dict[str, Any]]: Page information if found, None otherwise
        """
        try:
            response = graph_client.get_site_notebook_section_pages(site_id, section_id)
            pages = response.get('value', [])
            
            for page in pages:
                if page.get('title') == page_title:
                    logger.info(f"Found page '{page_title}' with ID: {page.get('id')}")
                    return page
            
            logger.info(f"No page found with title '{page_title}' in section {section_id}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get page by title '{page_title}' in site notebook: {e}")
            return None

    def add_opportunity_page_for_row(self, site_id: str, notebook_id: str, customer_name: str, opp_id: str, project_name: str, row_data: dict, column_id_to_name: dict = None) -> dict:
        """
        Add a page to the Opportunity Notebook for a new Smartsheet row.
        - Finds or creates a section named after the customer.
        - Finds or skips (if exists) a page titled 'Opp ID - Project Name'.
        - Builds a table with all non-empty fields/values from row_data.
        - Uses column_id_to_name mapping for friendly column names if provided.
        - Logs errors if notebook/section cannot be found/created.
        Args:
            site_id: SharePoint site ID
            notebook_id: Opportunity Notebook ID
            customer_name: Customer name (section name)
            opp_id: Opportunity ID (for page title)
            project_name: Project Name (for page title)
            row_data: Dict of all Smartsheet fields/values
            column_id_to_name: Dict mapping column IDs to names (optional)
        Returns:
            dict: Info about the created or found page, or error info
        """
        try:
            section = self.get_section_by_name_site(site_id, notebook_id, customer_name)
            if not section:
                section = graph_client.create_site_notebook_section(site_id, notebook_id, customer_name)
                if not section or not section.get('id'):
                    logger.error(f"Failed to create/find section '{customer_name}' in Opportunity Notebook {notebook_id}")
                    return {"error": f"Section creation failed: {customer_name}"}
            section_id = section.get('id')
            if not section_id:
                logger.error(f"Section ID is None for section '{customer_name}' in Opportunity Notebook {notebook_id}")
                return {"error": f"Section ID is None for section: {customer_name}"}
            page_title = f"{opp_id} - {project_name}" if opp_id else project_name
            existing_page = self.get_page_by_title_site(site_id, section_id, page_title)
            if existing_page:
                logger.info(f"Page '{page_title}' already exists in section '{customer_name}', skipping creation.")
                return {"skipped": True, "page": existing_page}
            page_html = self._build_full_table_html(page_title, row_data, column_id_to_name=column_id_to_name or {})
            page = graph_client.create_page_in_section(site_id, section_id, page_html)
            logger.info(f"Successfully created Opportunity page '{page_title}' in section '{customer_name}'")
            return {"created": True, "page": page}
        except Exception as e:
            logger.error(f"Error adding Opportunity page for row: {e}")
            return {"error": str(e)}

    def _build_full_table_html(self, title, data, column_id_to_name=None):
        """
        Build an HTML table with all non-empty fields/values from data.
        Args:
            title: Page title
            data: Dict of all fields/values (each value is a dict with value, displayValue, hyperlink)
            column_id_to_name: Dict mapping column IDs to names (optional)
        Returns:
            str: HTML content for the OneNote page
        """
        title = self._clean_text_for_onenote(title)
        if column_id_to_name is None:
            column_id_to_name = {}
        rows = ""
        for key, cell in data.items():
            if not isinstance(cell, dict):
                continue
            value = cell.get('displayValue') or cell.get('value')
            if value is None or value == "":
                continue
            friendly_name = column_id_to_name.get(key, str(key))
            # Special handling for hyperlink column
            if key == "1838548451020676" and cell.get('hyperlink'):
                url = cell['hyperlink'].get('url')
                label = cell['hyperlink'].get('label') or value
                if url:
                    value = f'<a href="{url}">{label}</a>'
            elif isinstance(value, dict):
                name = value.get("name", "")
                email = value.get("email", "")
                if name and email:
                    value = f'<a href="mailto:{email}">{name}</a>'
                elif email:
                    value = f'<a href="mailto:{email}">{email}</a>'
                else:
                    value = json.dumps(value)
            else:
                value = self._clean_text_for_onenote(str(value), page_title=title)
            rows += f"<tr><td>{friendly_name}</td><td>{value}</td></tr>"
        html = f"""
<!DOCTYPE html>
<html>
<head>
  <title>{title}</title>
  <meta charset='utf-8' />
</head>
<body>
  <table border='1' cellpadding='5' style='border-collapse:collapse;'>
    <thead>
      <tr><th>Field</th><th>Value</th></tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>
</body>
</html>
"""
        import re
        html = re.sub(r"[\r\n]+", "", html)
        html = re.sub(r">\s+<", "><", html)
        html = html.strip()
        if html.startswith('"'):
            html = html[1:]
        if html.endswith('"'):
            html = html[:-1]
        logger.info(f"Final HTML for Opportunity OneNote page:\n{html}")
        return html


# Global OneNote manager instance
onenote_manager = OneNoteManager() 