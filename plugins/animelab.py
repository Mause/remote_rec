import logging
import os
from datetime import datetime
from functools import lru_cache
from pprint import pprint
from typing import Dict, Optional
from urllib.parse import parse_qsl

import requests
from pychromecast import Chromecast
from pychromecast.controllers.media import MediaController
from requests_toolbelt.sessions import BaseUrlSession

USERNAME = os.environ['ANIMELAB_USERNAME']
PASSWORD = os.environ['ANIMELAB_PASSWORD']
ANIMELAB_APP_ID = "53C25447"

session = BaseUrlSession("https://api.animelab.com/api/")


@lru_cache()
def get_controller(tv):
    mc = AnimelabController()

    tv.register_handler(mc)

    return mc


class AnimelabController(MediaController):
    def __init__(self):
        super().__init__()
        self.app_id = ANIMELAB_APP_ID


def autocomplete(text: str) -> Optional[Dict]:
    result = session.get("shows/search", params={"searchTerms": text}).json()["list"]

    return result[0] if result else None


def play_show(tv: Chromecast, text: str):
    show = autocomplete(text)
    if not show:
        logging.info(f'could not find a show that matched "{text}" for animelab')
        return

    logging.info(f"playing from {show['name']}")

    video = get_video_for_show(show["id"])

    mc = get_controller(tv)

    mc.play_media(video, "video/mp4")
    mc.block_until_active()

    mc.play()


def get_expiry(play_session: str) -> datetime:
    _, data_bit = play_session.split("-", 1)
    data = dict(parse_qsl(data_bit))

    exp = datetime.fromtimestamp(int(data["pa.u.exp"]) / 1000)

    logging.info(exp)

    return exp


def get_session():
    play_session = session.cookies.get("PLAY_SESSION")
    if not play_session:  # or datetime.now() > get_expiry(play_session):
        logging.info("obtaining new token")

        session.post(
            "login",
            data={
                "email": USERNAME,
                "password": PASSWORD,
                "rememberMe": "true",
            },
        )

    return session


def get_video_for_show(show_id: str) -> str:
    first_unwatched = (
        get_session().get(f"shows/firstunwatched/{show_id}").json()["videoList"]
    )

    logging.info(
        {
            fw["videoQuality"]["videoFormat"]["name"]
            for video in first_unwatched
            for fw in video["videoInstances"]
        }
    )

    first_unwatched = list(
        fw
        for video in first_unwatched
        for fw in video["videoInstances"]
        if fw["videoQuality"]["videoFormat"]["name"] in {"MP4", "MPEG-DASH"}
    )

    first_unwatched = max(first_unwatched, key=lambda show: show["bitrate"])

    return (
        get_session()
        .get(
            f"videoinstances/sign/{first_unwatched['id']}/{first_unwatched['filename']}"
        )
        .json()["httpUrl"]
    )


if __name__ == "__main__":
    pprint(get_video_for_show('479'))
