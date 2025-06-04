import json
import requests

from typing import Any, Dict, List
from incidentbot.configuration.settings import settings
from incidentbot.logging import logger


class NotionApi:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {settings.NOTION_API_KEY}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }

    def page_exists(self, page_id: str) -> bool:
        try:
            url = f"https://api.notion.com/v1/pages/{page_id}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.status_code == 200
        except requests.exceptions.HTTPError as error:
            if error.response.status_code == 404:
                logger.info(f"Page with ID {page_id} does not exist.")
                return False
            logger.error(f"Error checking page existence: {error}")
            return False
        except Exception as error:
            logger.error(f"Unexpected error: {error}")
            return False

    def retrieve_page_blocks(self, page_id: str) -> List[Dict[str, Any]]:
        url = f"https://api.notion.com/v1/blocks/{page_id}/children"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        
        blocks = response.json().get("results", [])
        filtered_blocks = [block for block in blocks if not block.get("has_children", False)]
        
        return filtered_blocks

    def create_new_page(self, title: str, parent_page_id: str, blocks: List[Dict[str, Any]]) -> str:
        url = "https://api.notion.com/v1/pages"
        new_page_data = {
            "parent": {"page_id": parent_page_id},
            "properties": {
                "title": {
                    "title": [
                        {
                            "text": {
                                "content": title
                            }
                        }
                    ]
                }
            },
            "children": blocks
        }
        response = requests.post(url, headers=self.headers, data=json.dumps(new_page_data))
        response.raise_for_status()
        return response.json()["url"]

    def test(self) -> bool:
        try:
            return self.page_exists(
                settings.integrations.notion.parent
            )
        except Exception as error:
            logger.error(f"Error checking Notion page: {error}")
            logger.error("Please check Notion configuration and try again.")
            return False