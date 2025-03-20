import datetime
import uuid

from incidentbot.configuration.settings import settings
from incidentbot.notion.api import NotionApi
from incidentbot.exceptions import PostmortemException
from incidentbot.models.database import (
    IncidentEvent,
    IncidentParticipant,
    IncidentRecord,
)
from incidentbot.logging import logger
from requests.exceptions import HTTPError
from typing import Dict, List


class IncidentPostmortem:
    def __init__(
        self,
        incident: IncidentRecord,
        participants: list[IncidentParticipant],
        timeline: list[IncidentEvent],
        title: str,
    ):
        self.parent = settings.integrations.atlassian.notion.parent
        self.template_id = settings.integrations.atlassian.notion.template_id
        self.incident = incident
        self.participants = participants
        self.timeline = timeline
        self.title = title

        self.notion = NotionApi()

    def create(self) -> str | None:
        """
        Creates a starting postmortem page and returns the created page's URL
        """
        logger.info(f"Creating postmortem {self.title} in Notion under parent page ID {self.parent}...")

        # Check if the parent page exists
        if self.notion.page_exists(self.parent):
            try:
                # Get blocks from the template page
                template_blocks = self.notion.retrieve_page_blocks(self.template_id)

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
