#!/usr/bin/env python
# coding: utf-8

import argparse
import datetime
import json
import logging
import os
import re
import shutil
import sys
from typing import Dict, List

import slack_sdk
from appdirs import user_cache_dir
from rich.logging import RichHandler

APP_NAME = "slack-react"
LOGGER = logging.getLogger(__name__)

# mapping of alphabets to their corresponding emoji names
EMOJI_MAPPING = {
    "a": ["a", "alphabet-white-a", "alphabet-yellow-a"],
    "b": ["b", "alphabet-white-b", "alphabet-yellow-b"],
    "c": ["alphabet-white-c", "alphabet-yellow-c"],
    "d": ["alphabet-white-d", "alphabet-yellow-d"],
    "e": ["alphabet-white-e", "alphabet-yellow-e", "e-mail"],
    "f": ["alphabet-white-f", "alphabet-yellow-f"],
    "g": ["alphabet-white-g", "alphabet-yellow-g"],
    "h": ["alphabet-white-h", "alphabet-yellow-h"],
    "i": ["alphabet-white-i", "alphabet-yellow-i"],
    "j": ["alphabet-white-j", "alphabet-yellow-j"],
    "k": ["alphabet-white-k", "alphabet-yellow-k"],
    "l": ["alphabet-white-l", "alphabet-yellow-l"],
    "m": ["alphabet-white-m", "alphabet-yellow-m"],
    "n": ["alphabet-white-n", "alphabet-yellow-n"],
    "o": ["alphabet-white-o", "alphabet-yellow-o", "o"],
    "p": ["alphabet-white-p", "alphabet-yellow-p"],
    "q": ["alphabet-white-q", "alphabet-yellow-q"],
    "r": ["alphabet-white-r", "alphabet-yellow-r"],
    "s": ["alphabet-white-s", "alphabet-yellow-s"],
    "t": ["alphabet-white-t", "alphabet-yellow-t"],
    "u": ["alphabet-white-u", "alphabet-yellow-u"],
    "v": ["alphabet-white-v", "alphabet-yellow-v"],
    "w": ["alphabet-white-w", "alphabet-yellow-w"],
    "x": ["alphabet-white-x", "alphabet-yellow-x"],
    "y": ["alphabet-white-y", "alphabet-yellow-y"],
    "z": ["alphabet-white-z", "alphabet-yellow-z"],
    "0": ["zero", "zero"],
    "1": ["one", "one"],
    "2": ["two", "two"],
    "3": ["three", "three"],
    "4": ["four", "four"],
    "5": ["five", "five"],
    "6": ["six", "six"],
    "7": ["seven", "seven"],
    "8": ["eight", "eight"],
    "9": ["nine", "nine"],
    "?": ["alphabet-white-question", "alphabet-yellow-question"],
    "!": [
        "exclamation",
        "bangbang",
        "gray_exclamation",
        "alphabet-white-exclamation",
        "alphabet-yellow-exclamation",
    ],
    "-": ["heavy_minus_sign", "wavy_dash"],
    " ": [
        "black_small_square",
        "white_small_square",
        "small_orange_diamond",
        "small_blue_diamond",
        "black_medium_square",
        "white_medium_square",
    ],
}


def parse_args():
    # create the top-level parser
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d", "--debug", action="store_true", default=False, help="Debug mode"
    )
    parser.add_argument("-c", "--channel", help="Channel name")
    parser.add_argument(
        "-t",
        "--token",
        default=os.environ.get("SLACK_USER_OAUTH_TOKEN"),
        help="Slack OAUTH Token",
    )
    parser.add_argument("-m", "--message", help="Slack message to react to")
    parser.add_argument(
        "-r",
        "--remove",
        action="store_true",
        help="Remove reactions from message",
    )

    # add the positional argument for the message
    parser.add_argument(
        "reaction", nargs="?", help="the message to be converted to emojis"
    )

    return parser.parse_args()


def message_to_emoji_list(message):
    # create a list to hold the emojis
    emojis = []
    # create a dictionary to hold the index of the next emoji to use for
    # each character
    next_emoji_index = {}

    # iterate over each character in the message
    for char in message:
        # convert the character to lowercase
        char = char.lower()

        # if the character is in the mapping
        if char not in EMOJI_MAPPING:
            LOGGER.debug(
                "Skipping character '%s' since there is no mapping for it",
                char,
            )
            continue

        # if the character is not in next_emoji_index, this is the first
        # time we've seen it
        if char not in next_emoji_index:
            next_emoji_index[char] = 0

        # get the next emoji for this character
        emoji = EMOJI_MAPPING[char][next_emoji_index[char]]

        LOGGER.debug("Converted '%s' to '%s'", char, emoji)

        # add the emoji to the list
        emojis.append(emoji)

        # update the index of the next emoji to use for this character
        next_emoji_index[char] = (next_emoji_index[char] + 1) % len(
            EMOJI_MAPPING[char]
        )

    return emojis


def invalidate_cache():
    cache_dir = user_cache_dir(APP_NAME)
    if os.path.exists(cache_dir) and os.path.isdir(cache_dir):
        shutil.rmtree(cache_dir)


def get_cache_age(
    filename: str = "channel_cache.json",
):
    # Determine the full path to the cache file
    cache_dir = user_cache_dir(APP_NAME)
    metadata_filepath = os.path.join(
        cache_dir, filename.replace(".json", ".metadata.json")
    )
    try:
        with open(metadata_filepath, "r") as f:
            metadata = json.load(f)
            created = metadata.get("created")
            if not created:
                return

            return datetime.datetime.now() - datetime.datetime.fromtimestamp(
                created
            )
    except (FileNotFoundError, json.JSONDecodeError):
        return


def is_cache_valid(filename: str = "channel_cache.json", max_age: int = 12):
    age = get_cache_age(filename)
    if not age:
        return False
    return age < datetime.timedelta(hours=max_age)


def update_channel_cache(
    content: List[Dict],
    filename: str = "channel_cache.json",
):
    # Determine the full path to the cache file
    cache_dir = user_cache_dir(APP_NAME)
    os.makedirs(cache_dir, exist_ok=True)
    filepath = os.path.join(cache_dir, filename)

    with open(filepath, "w") as f:
        json.dump(content, f)

    ts = int(datetime.datetime.now().timestamp())
    metadata = {"created": ts}
    metadata_filepath = os.path.join(
        cache_dir, filename.replace(".json", ".metadata.json")
    )
    with open(metadata_filepath, "w") as f:
        json.dump(metadata, f)


def load_channel_cache(filename: str = "channel_cache.json") -> List[Dict]:
    # Determine the full path to the cache file
    cache_dir = user_cache_dir(APP_NAME)
    filepath = os.path.join(cache_dir, filename)

    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def smart_cache(
    client: slack_sdk.WebClient,
    filename: str = "channel_cache.json",
):
    if is_cache_valid(filename):
        LOGGER.info("Using cached channel list")
        return load_channel_cache(filename)
    else:
        LOGGER.info("Cache invalid, fetching channel list")
        invalidate_cache()
        content = get_all_channels(client)
        update_channel_cache(content, filename)
        return content


def get_user_id(client):
    response = client.auth_test()

    # the user ID is in the 'user_id' field of the response
    return response["user_id"]


def get_all_channels(
    client: slack_sdk.WebClient, page_size: int = 500
) -> List[Dict]:
    channels = []
    types = ["private_channel", "public_channel", "mpim", "im"]
    result = client.conversations_list(
        types=types,
        limit=page_size,
    )

    if not isinstance(result.get("channels"), list):
        raise ValueError("Invalid response from Slack API")

    channels.extend(result.get("channels", []))
    next_cursor = result.get("response_metadata", {}).get("next_cursor")

    while next_cursor:
        result = client.conversations_list(
            limit=page_size, types=types, cursor=next_cursor
        )
        next_cursor = result.get("response_metadata", {}).get("next_cursor")
        channels.extend(result.get("channels", []))

    return channels


def get_channel_id(client, channel_name):
    # the channels are in the 'channels' field of the response
    channels = smart_cache(client)

    # iterate over the channels to find the one with the given name
    for channel in channels:
        if channel["name"] == channel_name:
            return channel["id"]


def find_matching_message(client, channel_id, regex):
    # get the history of the channel
    response = client.conversations_history(channel=channel_id)

    # TODO Get messages from threads

    # the messages are in the 'messages' field of the response
    messages = response["messages"]

    # create a regex object
    pattern = re.compile(regex)

    # iterate over the messages in reverse order
    for message in reversed(messages):
        # check if the message matches the regex
        if pattern.search(message["text"]):
            # return the matching message
            return message

    # if no matching message was found, return None
    return None


def remove_reactions(client, channel_id, timestamp):
    LOGGER.info("Removing all reactions from message")
    response = client.reactions_get(channel=channel_id, timestamp=timestamp)

    # the reactions are in the 'message'->'reactions' field of the response
    reactions = response["message"].get("reactions", [])

    # iterate over the reactions and remove each one
    for reaction in [
        x.get("name")
        for x in reactions
        if get_user_id(client) in x.get("users", [])
    ]:
        LOGGER.info("Removing reaction: '%s'", reaction)
        client.reactions_remove(
            channel=channel_id, timestamp=timestamp, name=reaction
        )


def add_reactions(client, channel_id, timestamp, message):
    LOGGER.info("Adding reactions to message so that is spells '%s'", message)
    for reaction in message_to_emoji_list(message):
        # react to a message
        LOGGER.info("Adding reaction to message: '%s'", reaction)
        client.reactions_add(
            channel=channel_id, timestamp=timestamp, name=reaction
        )


def main():
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(message)s",
        datefmt="[%H:%M:%S]",
        handlers=[RichHandler(rich_tracebacks=True)],
    )

    # create a client instance
    client = slack_sdk.WebClient(token=args.token)

    channel_id = get_channel_id(client, args.channel)

    if not channel_id:
        LOGGER.error(f"Channel '{args.channel}' not found")
        return 1

    response = client.conversations_history(channel=channel_id)

    target_message = None
    if args.message:
        message = find_matching_message(client, channel_id, args.message)
        if not message:
            LOGGER.error("Message not found")
            return 1
        ts = message["ts"]
        target_message = message["text"]
    else:
        # Default to last message
        message = response.get("messages", [{"ts": None}])[0]
        target_message = message["text"]
        ts = message["ts"]

    if not ts:
        LOGGER.error("No messages found")
        return 1

    LOGGER.debug("Target message: %s", message)
    LOGGER.info("Target message: %s", target_message)
    remove_reactions(client, channel_id, ts)

    if args.reaction and not args.remove:
        add_reactions(client, channel_id, ts, args.reaction)

    return 0


if __name__ == "__main__":
    sys.exit(main())
