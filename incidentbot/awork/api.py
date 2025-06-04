import json
import requests

from typing import Any, Dict, Optional
from incidentbot.configuration.settings import settings
from incidentbot.logging import logger


class AworkApi:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {settings.AWORK_API_TOKEN}",
            "Content-Type": "application/json"
        }
        self.base_url = "https://api.awork.com/api/v1"

    def document_exists(self, doc_id: str) -> bool:
        """
        Check if a document with the given ID exists
        """
        try:
            url = f"{self.base_url}/documents/{doc_id}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.status_code == 200
        except requests.exceptions.HTTPError as error:
            if error.response.status_code == 404:
                logger.info(f"Document with ID {doc_id} does not exist.")
                return False
            logger.error(f"Error checking document existence: {error}")
            return False
        except Exception as error:
            logger.error(f"Unexpected error: {error}")
            return False

    def get_document_content(self, doc_id: str) -> Optional[str]:
        """
        Fetch the content of a document by its ID
        """
        try:
            url = f"{self.base_url}/documents/{doc_id}/content?streamAsFile=true"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            # Ensure proper character decoding
            response.encoding = 'utf-8'
            return response.text
        except requests.exceptions.HTTPError as error:
            logger.error(f"Error fetching document content: {error}")
            return None
        except Exception as error:
            logger.error(f"Unexpected error: {error}")
            return None
            
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a document by its ID
        """
        try:
            url = f"{self.base_url}/documents/{doc_id}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as error:
            logger.error(f"Error fetching document: {error}")
            return None
        except Exception as error:
            logger.error(f"Unexpected error: {error}")
            return None

    def create_document(self, name: str, parent_id: str, content: str) -> Optional[str]:
        """
        Creates a new document with the given name, parent ID, and content.
        Fetches the parent document first to extract the documentSpaceId.
        Returns the URL of the created document or None if creation failed.
        """
        try:
            # First, get the parent document to extract documentSpaceId
            parent_doc = self.get_document(parent_id)
            if not parent_doc:
                logger.error(f"Could not fetch parent document with ID: {parent_id}")
                return None
                
            document_space_id = parent_doc.get('documentSpaceId')
            if not document_space_id:
                logger.error(f"Parent document does not have a documentSpaceId")
                return None
                
            logger.info(f"Using documentSpaceId: {document_space_id} from parent document")
                
            url = f"{self.base_url}/documents"
            
            # Use in-memory file instead of temporary file on disk
            import io
            
            # Ensure proper encoding to handle special characters
            # Using utf-8 encoding with BOM marker to ensure proper encoding detection
            content_bytes = content.encode('utf-8-sig')
            content_file = io.BytesIO(content_bytes)
            
            # Create multipart form data with in-memory file
            files = {
                'name': (None, name),
                'emoji': (None, '🔥'),
                'parentId': (None, parent_id),
                'documentSpaceId': (None, document_space_id),
                'content': ('document.html', content_file, 'text/html; charset=utf-8')
            }
            
            headers = {
                "Authorization": f"Bearer {settings.AWORK_API_TOKEN}"
                # Let requests set the correct Content-Type for multipart/form-data
            }
            
            response = requests.post(url, headers=headers, files=files)
            response.raise_for_status()
            
            # Return the URL to the created document
            doc_id = response.json().get("id")
            return f"https://app.awork.com/docs/{doc_id}"
        except requests.exceptions.HTTPError as error:
            logger.error(f"Error creating document: {error}")
            return None
        except Exception as error:
            logger.error(f"Unexpected error: {error}")
            return None

    def test(self) -> bool:
        """
        Test the awork API connection
        """
        try:
            return self.document_exists(
                settings.integrations.awork.template_id
            )
        except Exception as error:
            logger.error(f"Error checking awork document: {error}")
            logger.error("Please check awork configuration and try again.")
            return False
