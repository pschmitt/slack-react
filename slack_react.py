#!/usr/bin/env python
# coding: utf-8

import argparse
import logging
import os
import re
import sys
from typing import Dict, List

import slack_sdk
from rich import print
from rich.logging import RichHandler


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
    # mapping of alphabets to their corresponding emoji names
    emoji_mapping = {
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
        "o": ["alphabet-white-o", "alphabet-yellow-o"],
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
    }

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
        if char in emoji_mapping:
            # if the character is not in next_emoji_index, this is the first
            # time we've seen it
            if char not in next_emoji_index:
                next_emoji_index[char] = 0

            # get the next emoji for this character
            emoji = emoji_mapping[char][next_emoji_index[char]]

            # add the emoji to the list
            emojis.append(emoji)

            # update the index of the next emoji to use for this character
            next_emoji_index[char] = (next_emoji_index[char] + 1) % len(
                emoji_mapping[char]
            )

    return emojis


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
    channels = get_all_channels(client)

    # iterate over the channels to find the one with the given name
    for channel in channels:
        # print(channel["name"])
        if channel["name"] == channel_name:
            return channel["id"]


def find_matching_message(client, channel_id, regex):
    # get the history of the channel
    response = client.conversations_history(channel=channel_id)

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
    response = client.reactions_get(channel=channel_id, timestamp=timestamp)

    # the reactions are in the 'message'->'reactions' field of the response
    reactions = response["message"].get("reactions", [])

    # iterate over the reactions and remove each one
    for reaction in [
        x.get("name")
        for x in reactions
        if get_user_id(client) in x.get("users", [])
    ]:
        client.reactions_remove(
            channel=channel_id, timestamp=timestamp, name=reaction
        )


def add_reactions(client, channel_id, timestamp, message):
    for reaction in message_to_emoji_list(message):
        # react to a message
        LOGGER.info("Adding reaction to message: %s", reaction)
        client.reactions_add(
            channel=channel_id, timestamp=timestamp, name=reaction
        )


def main():
    args = parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        handlers=[RichHandler()],
    )

    # create a client instance
    client = slack_sdk.WebClient(token=args.token)

    channel_id = get_channel_id(client, args.channel)

    if not channel_id:
        print(f"Channel '{args.channel}' not found", file=sys.stderr)
        return 1

    response = client.conversations_history(channel=channel_id)

    if args.message:
        message = find_matching_message(client, channel_id, args.message)
        if not message:
            print("Message not found", file=sys.stderr)
            return 1
        ts = message["ts"]
    else:
        # Default to last message
        ts = response["messages"][0]["ts"]

    remove_reactions(client, channel_id, ts)

    if args.reaction and not args.remove:
        add_reactions(client, channel_id, ts, args.reaction)

    return 0


LOGGER = logging.getLogger(__name__)


if __name__ == "__main__":
    sys.exit(main())
