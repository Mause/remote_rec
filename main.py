import os
import json
from functools import lru_cache
from typing import Optional
import logging

import requests
from dotenv import load_dotenv
from redis import StrictRedis
import pychromecast

import animelab
import plex

logging.basicConfig(level=logging.INFO)

load_dotenv()


@lru_cache()
def get_tv():
    logging.info("finding tv")
    chromecasts = pychromecast.get_chromecasts()

    logging.info('found chromecasts: %s', chromecasts)

    tv = next(ch for ch in chromecasts if ch.device.friendly_name == "Bedroom TV")

    logging.info("tv found")

    return tv


def main():
    url = requests.get(
        "https://remote-hook.herokuapp.com/redis",
        auth=(os.environ["CONFIG_USERNAME"], os.environ["CONFIG_PASSWORD"]),
    ).json()["redis_endpoint"]

    redis = StrictRedis.from_url(url)
    redis.execute_command('client setname remoterec')

    ps = redis.pubsub()
    ps.subscribe("watch")
    sub = ps.listen()
    logging.info(next(sub))  # skip connection

    for message in ps.listen():
        tv = get_tv()

        message = json.loads(message["data"])
        logging.info(message)

        if message["service"] == "animelab":
            animelab.play_show(tv, message["show"])
        elif message["service"] == "plex":
            plex.play_show(tv, message["show"])
        else:
            raise Exception(message)


if __name__ == "__main__":
    main()

