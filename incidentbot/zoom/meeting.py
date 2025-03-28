import json
import requests

from incidentbot.configuration.settings import settings
from incidentbot.logging import logger


class ZoomMeeting:
    """Creates a Zoom meeting"""

    def __init__(self, incident: str):
        self.incident = incident
        self.endpoint = "https://api.zoom.us/v2"
        self.token = self.__generate_token()
        self.headers = {
            "authorization": "Bearer " + self.token,
            "content-type": "application/json",
        }

    @property
    def url(self) -> str:
        url = self.__create()

        return url

    def __create(self) -> str:
        meeting_details = {
            "agenda": self.incident,
            "default_password": True,
            "settings": {
                "audio": "voip",
                "host_video": False,
                "jbh_time": 0,
                "join_before_host": True,
                "meeting_authentication": True,
                "mute_upon_entry": True,
                "participant_video": True,
                "use_pmi": False,
                "waiting_room": False,
                "auto_recording": "cloud",
            },
            "topic": self.incident,
            "type": 2,
        }
        try:
            res = requests.post(
                f"{self.endpoint}/users/me/meetings",
                headers=self.headers,
                data=json.dumps(meeting_details),
            )
            res_json = json.loads(res.text)
            if res.status_code != 201:
                logger.error(f"Error creating Zoom meeting: {res.status_code}")
                return None

            return res_json["join_url"]
        except Exception as error:
            logger.error(f"Error creating Zoom meeting: {error}")

    def __generate_token(self) -> str:
        try:
            endpoint = "https://zoom.us/oauth/token"
            payload = {
                "grant_type": "account_credentials",
                "account_id": settings.ZOOM_ACCOUNT_ID,
            }
            res = requests.post(
                endpoint,
                auth=requests.auth.HTTPBasicAuth(
                    settings.ZOOM_CLIENT_ID, settings.ZOOM_CLIENT_SECRET
                ),
                params=payload,
            )
            if "access_token" in json.loads(res.text):
                return json.loads(res.text)["access_token"]
            else:
                return None
        except Exception as error:
            logger.error(f"Error creating token for Zoom API: {error}")

    def test_auth(self) -> bool:
        token = self.__generate_token()
        if not token:
            return False

        return True
