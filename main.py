import json
import logging
import os
from functools import lru_cache
from uuid import UUID

import pychromecast
import requests
from dotenv import load_dotenv
from pluginbase import PluginBase
from pychromecast import Chromecast
from redis import StrictRedis

logging.basicConfig(level=logging.INFO)

load_dotenv()

plugin_source = PluginBase('plugins').make_plugin_source(searchpath=['plugins'])


@lru_cache()
def get_tv(*, uuid: str = None, name: str = None) -> Chromecast:
    assert uuid or name, "Must specify either name or uuid"
    logging.info("finding tv")

    chromecasts = pychromecast.get_chromecasts()

    logging.info("found chromecasts: %s", chromecasts)

    _uuid = UUID(uuid) if uuid else None
    tv = next(
        (
            ch
            for ch in chromecasts
            if (ch.device.friendly_name == name or ch.device.uuid == _uuid)
        ),
        None,
    )
    if not tv:
        message = f'did not find tv with criteria: name="{name}" or uuid="{uuid}"'
        logging.error(message)
        raise Exception(message)

    logging.info("tv found: %s", tv)

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
        tv = get_tv(name="Ellie's TV")

        message = json.loads(message["data"])
        logging.info(message)

        try:
            play_show = plugin_source.load_plugin(message['service']).play_show
        except ImportError as e:
            raise Exception(message) from e
        else:
            play_show(tv, message['show'])


if __name__ == "__main__":
    try:
        with open(".git/ref") as fh:
            print(f"version: {fh.read().strip()}")
    except FileNotFoundError:
        pass
    main()
