import datetime
import uuid

from incidentbot.configuration.settings import settings
from incidentbot.awork.api import AworkApi
from incidentbot.exceptions import PostmortemException
from incidentbot.models.database import (
    IncidentEvent,
    IncidentParticipant,
    IncidentRecord,
)
from incidentbot.slack.client import slack_workspace_id
from incidentbot.logging import logger
from requests.exceptions import HTTPError
from typing import Dict, List, Optional


class IncidentPostmortem:
    def __init__(
        self,
        incident: IncidentRecord,
        participants: list[IncidentParticipant],
        timeline: list[IncidentEvent],
        title: str,
    ):
        self.parent = settings.integrations.awork.parent
        self.template_id = settings.integrations.awork.template_id
        self.incident = incident
        self.participants = participants
        self.timeline = timeline
        self.title = title

        self.awork = AworkApi()

    def create(self) -> str | None:
        """
        Creates a starting postmortem document and returns the created document's URL
        """
        logger.info(f"Creating postmortem {self.title} in awork with parent doc ID {self.parent}...")

        # Check if the template document exists
        if self.awork.document_exists(self.template_id):
            try:
                logger.info(f"Fetching template document content from ID: {self.template_id}")
                # Get content from the template document
                template_content = self.awork.get_document_content(self.template_id)
                
                if template_content:
                    # Modify the template content with incident details
                    logger.info("Modifying template content with incident details")
                    modified_content = self._modify_template_content(template_content)
                    
                    # Create a new postmortem document with the modified content
                    logger.info(f"Creating new document with parent ID: {self.parent}")
                    logger.info(modified_content)
                    new_doc_url = self.awork.create_document(
                        name=self.title,
                        parent_id=self.parent,
                        content=modified_content
                    )

                    logger.info(f"Postmortem document created successfully: {new_doc_url}")
                    return new_doc_url
                else:
                    logger.error("Failed to retrieve template content")
                    raise PostmortemException("Failed to retrieve template content")
            except Exception as error:
                logger.error(f"Error creating postmortem document: {error}")
                raise
        else:
            logger.error("Couldn't create postmortem document, does the template document exist?")
            raise ValueError("Template document does not exist.")

    def _modify_template_content(self, template_content: str) -> str:
        """
        Modify the template content with incident details
        """
        content = template_content
        
        # Replace placeholders with actual values
        replacements = {
            "!ib-inject-description": self.incident.description,
            "!ib-inject-duration": self._get_duration(),
            "!ib-inject-impact": self.incident.impact,
            "!ib-inject-components": self.incident.components,
            "!ib-inject-channel": f"https://{slack_workspace_id}.slack.com/archives/{self.incident.channel_id}",
            "!ib-inject-severity": self.incident.severity,
            "!ib-inject-created-at": self._format_datetime(self.incident.created_at),
            "!ib-inject-updated-at": self._format_datetime(self.incident.updated_at),
            "!ib-inject-participants": self._generate_participants_html(),
            "!ib-inject-timeline": self._generate_timeline_html()
        }
        
        for placeholder, value in replacements.items():
            content = content.replace(placeholder, value or "")
            
        return content

    def _get_duration(self) -> str:
        """
        Calculate the incident duration in a human-readable format
        """
        if not self.incident.created_at or not self.incident.updated_at:
            return "Unknown"
            
        delta = self.incident.updated_at - self.incident.created_at
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if delta.days > 0:
            return f"{delta.days} days, {hours} hours, {minutes} minutes"
        elif hours > 0:
            return f"{hours} hours, {minutes} minutes"
        else:
            return f"{minutes} minutes, {seconds} seconds"

    def _generate_participants_html(self) -> str:
        """
        Generate HTML table for participants
        """
        html = "<table><thead><tr><th>Role</th><th>User</th></tr></thead><tbody>"
        
        for participant in self.participants:
            html += f"<tr><td>{participant.role.replace('_', ' ').title()}</td><td>{participant.user_name}</td></tr>"
            
        html += "</tbody></table>"
        return html

    def _generate_timeline_html(self) -> str:
        """
        Generate HTML table for timeline events
        """
        html = "<table><thead><tr><th>Timestamp</th><th>Event</th></tr></thead><tbody>"
        
        for event in self.timeline:
            html += f"<tr><td>{self._format_datetime(event.created_at)}</td><td>{event.text}</td></tr>"
            
        html += "</tbody></table>"
        return html
        
    def _format_datetime(self, dt: datetime.datetime) -> str:
        """
        Format datetime to YYYY-MM-DD HH:MM:SS
        """
        if not dt:
            return ""
        return dt.strftime("%Y-%m-%d %H:%M:%S")
