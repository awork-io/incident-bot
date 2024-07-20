import config

from bot.notion.api import NotionApi, logger
from bot.models.pg import IncidentLogging
from typing import Dict, List


class IncidentPostmortem:
    def __init__(
        self,
        incident_id: str,
        postmortem_title: str,
        incident_commander: str,
        severity: str,
        severity_definition: str,
        pinned_items: List[IncidentLogging],
        timeline: List[Dict],
    ):
        self.incident_id = incident_id
        self.title = postmortem_title
        self.incident_commander = incident_commander
        self.severity = severity
        self.severity_definition = severity_definition
        self.pinned_items = pinned_items
        self.timeline = timeline

        self.postmortem_template_id = config.active.integrations.get("notion").get("postmortem_template_id")
        self.parent = config.active.integrations.get("notion").get("parent")

        self.notion = NotionApi()

    def create(self) -> str:
        """
        Creates a starting postmortem page and returns the created page's URL
        """
        logger.info(f"Creating postmortem {self.title} in Notion under parent page ID {self.parent}...")

        # Check if the parent page exists
        if self.notion.page_exists(self.parent):
            try:
                # Get blocks from the template page
                template_blocks = self.notion.retrieve_page_blocks(self.postmortem_template_id)

                # Create a new postmortem page with the retrieved blocks
                new_page_url = self.notion.create_new_page(self.title, self.parent, template_blocks)

                logger.info(f"Postmortem page created successfully: {new_page_url}")
                return new_page_url
            except Exception as error:
                logger.error(f"Error creating postmortem page: {error}")
                raise
        else:
            logger.error("Couldn't create postmortem page, does the parent page exist?")
            raise ValueError("Parent page does not exist.")
