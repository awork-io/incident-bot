from incidentbot.configuration.settings import settings
from incidentbot.exceptions import IndexNotFoundError
from incidentbot.logging import logger
from incidentbot.models.incident import IncidentDatabaseInterface

from incidentbot.slack.messages import (
    BlockBuilder,
)
from incidentbot.util import gen
from slack_sdk.errors import SlackApiError
from typing import Any

if not settings.IS_TEST_ENVIRONMENT:
    from incidentbot.slack.client import (
        slack_web_client,
    )


def _disable_failed_incident_job(channel_id: str, job_suffix: str) -> None:
    """
    Disable a per-incident scheduler job to prevent repeated Slack errors.
    """

    try:
        from incidentbot.scheduler.core import process as TaskScheduler

        incident = IncidentDatabaseInterface.get_one(channel_id=channel_id)
        job = TaskScheduler.get_job(job_id=f"{incident.slug}_{job_suffix}")
        if job:
            TaskScheduler.delete_job(job_to_delete=job.id)
            logger.warning(
                f"disabled job {incident.slug}_{job_suffix} after repeated Slack post failures"
            )
    except Exception as error:
        logger.warning(
            f"could not disable failed job for incident channel {channel_id}: {error}"
        )


def _post_incident_message_with_join_retry(
    channel_id: str,
    blocks: list[dict[str, Any]],
    text: str,
    job_suffix: str,
    error_prefix: str,
) -> None:
    """
    Post a Slack message and recover from "not_in_channel" by attempting a join
    and one retry. If that still fails, disable the scheduled job to avoid
    repeated noisy failures.
    """

    try:
        slack_web_client.chat_postMessage(
            channel=channel_id,
            blocks=blocks,
            text=text,
        )
        return
    except SlackApiError as error:
        if error.response.get("error") != "not_in_channel":
            logger.error(f"{error_prefix}: {error}")
            return

    try:
        slack_web_client.conversations_join(channel=channel_id)
        slack_web_client.chat_postMessage(
            channel=channel_id,
            blocks=blocks,
            text=text,
        )
    except SlackApiError as retry_error:
        logger.warning(
            f"{error_prefix}: {retry_error} (attempted auto-join once before giving up)"
        )
        _disable_failed_incident_job(channel_id, job_suffix)


def comms_reminder(channel_id: str):
    """
    Sends a message to a channel to initiate communications updates

    Parameters:
        channel_id (str): The incident channel id
    """

    _post_incident_message_with_join_retry(
        channel_id=channel_id,
        blocks=BlockBuilder.comms_reminder_message(),
        text="Some time has passed since this incident was declared. How about updating others on its status?",
        job_suffix="comms_reminder",
        error_prefix="error sending comms reminder message to incident channel",
    )


def extract_role_owner(message_blocks: dict[Any, Any], block_id: str) -> str:
    """
    Takes message blocks and a block_id and returns information specific
    to one of the role blocks

    Parameters:
        message_block (dict[Any, Any]): Message blocks to search
        block_id (str): Block id to match
    """

    index = gen.find_index_in_list(message_blocks, "block_id", block_id)
    if index == -1:
        raise IndexNotFoundError(
            f"Could not find index for block_id {block_id}"
        )

    return (
        message_blocks[index]["text"]["text"].split("\n")[1].replace(" ", "")
    )


def role_watcher(channel_id: str):
    """
    Sends a message to a channel if roles remain unassigned

    Parameters:
        channel_id (str): The incident channel id
    """

    record = IncidentDatabaseInterface.get_one(channel_id=channel_id)
    participants = IncidentDatabaseInterface.list_participants(record)

    if not participants:
        _post_incident_message_with_join_retry(
            channel_id=channel_id,
            blocks=BlockBuilder.role_assignment_message(),
            text="No roles have been assigned for this incident yet. Please review, assess, and claim as-needed.",
            job_suffix="role_watcher",
            error_prefix="error sending role watcher message to incident channel",
        )
