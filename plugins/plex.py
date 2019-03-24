import os
import json
import logging
from functools import lru_cache
from typing import Optional, Any
from urllib.parse import urlparse

from pychromecast import Chromecast
from pychromecast.controllers.media import MediaController
from plexapi.server import PlexServer
from plexapi.myplex import MyPlexAccount
from plexapi.exceptions import NotFound
from plexapi.video import Movie

USERNAME = os.environ['PLEX_USERNAME']
PASSWORD = os.environ['PLEX_PASSWORD']
APP_ID = "9AC194DC"


@lru_cache()
def get_plex():
    logging.info("connecting to plex")
    plex = MyPlexAccount(USERNAME, PASSWORD).resource("Novell").connect()
    logging.info("connected to plex")

    return plex


class PlexMediaController(MediaController):
    def __init__(self, plex):
        super().__init__()
        self.plex = plex
        self.supporting_app_id = APP_ID

    def build_server(self):
        url = urlparse(self.plex.url(""))

        return {
            "machineIdentifier": self.plex.machineIdentifier,
            "protocol": url.scheme,
            "address": url.hostname,
            "port": url.port,
            "transcoderVideo": self.plex.transcoderVideo,
            "transcoderVideoRemuxOnly": False,
            "transcoderAudio": self.plex.transcoderAudio,
            "version": self.plex.version,
            "myPlexSubscription": self.plex.myPlexSubscription,
            "isVerifiedHostname": True,
            "accessToken": self.plex._token,
        }

    def play_media(self, video: Movie) -> None:
        self.launch(lambda: self._play_media(video))

    def _play_media(self, video: Movie) -> None:
        server = self.build_server()

        play_queue = self.plex.createPlayQueue(video)

        customData = {
            "playQueueType": "video",
            "providerIdentifier": "com.plexapp.plugins.library",
            "containerKey": f"/playQueues/{play_queue.playQueueID}?own=1",
            "offset": 0,
            "directPlay": True,
            "directStream": True,
            "mediaIndex": None,
            "audioBoost": 100,
            "subtitleSize": 100,
            "autoPlay": True,
            "repeat": 0,
            "audioForceMultiChannel": False,
            "server": server,
            "primaryServer": server,
            "user": {"username": self.plex.account().username},
        }

        body = {
            "contentId": video.key,
            "streamType": "BUFFERED",
            "metadata": None,
            "duration": None,
            "tracks": None,
            "textTrackStyle": None,
            "customData": customData,
        }

        self.send_message(
            {
                "media": body,
                "type": "LOAD",
                "autoplay": True,
                "current_time": None,
            },
            inc_session_id=True,
        )


def autocomplete(text: str) -> Optional[Movie]:
    results = get_plex().search(text)
    return results[0] if results else None


@lru_cache()
def get_controller(tv: Chromecast) -> PlexMediaController:
    mc = PlexMediaController(get_plex())

    tv.register_handler(mc)

    return mc


def play_show(tv: Chromecast, show: str) -> None:
    controller = get_controller(tv)

    video = autocomplete(show)
    if not video:
        logging.info(f'could not find matching "{show}" on Plex')
        return
    else:
        logging.info(f'playing {video.title}')

    controller.play_media(video)


if __name__ == "__main__":
    from main import get_tv

    get_plex()
    play_show(get_tv(), input('query> '))

