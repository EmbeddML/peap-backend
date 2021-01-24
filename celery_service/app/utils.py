import json
import os
from typing import Dict, Set

import regex as re
import requests

KRNNT_URL = os.getenv('KRNNT_URL', 'http://krnnt:9003')


def process_text(text: str) -> str:
    text = re.sub(r"http\S+", "", text)  # removes http links
    text = re.sub(r"\S+\.com\S+", "", text)  # removes links that have no http but end with com
    text = re.sub(r"\S+\.pl\S+", "", text)  # removes links that have no http but end with pl
    text = re.sub(r"\@\w+", "", text)  # removes whole mentions
    text = re.sub(r"\#", "", text)  # removes hashes (content of hashtag remains)
    text = re.sub(r"\s+", " ", text)  # convert multiple spaces into one
    return text


def emoji2text_tweet(tweet: str, emoji_mapping_items: Dict[str, str]) -> str:
    text = tweet
    for emoji, emoji_text in emoji_mapping_items:
        text = text.replace(emoji, f"<{emoji_text}>")
    return text


def krnnt_tag(text: str) -> str:
    response = requests.post(KRNNT_URL, data=text.encode("utf-8"))
    response_text = response.text.encode("utf-8")
    return response_text.decode("utf-8")


def lemmatize(text: str, pos_to_keep: set, keep_interp: bool) -> str:
    krnnt_text = krnnt_tag(text)

    sentences = krnnt_text.split("\n\n")
    tweet_lemmatized = ""
    for s_idx, sentence in enumerate(sentences):
        if sentence == "":
            continue
        sentence_lines = sentence.split("\n")
        words_data = list(zip(sentence_lines, sentence_lines[1:]))[::2]

        for orth, lex in words_data:
            orth_word, orth_preceding = orth.split("\t")
            lex_lem, lex_tag, _ = lex.split("\t")[1:]

            if lex_tag == "interp":
                pos = None
            else:
                pos = lex_tag.split(":")[0]

            if (pos is None and keep_interp) or (
                pos is not None and (len(pos_to_keep) == 0 or pos in pos_to_keep)
            ):
                if orth_preceding == "space":
                    tweet_lemmatized += " "
                elif orth_preceding == "newline":
                    if s_idx != 0:
                        tweet_lemmatized += "\n"
                elif orth_preceding == "none":
                    pass  # do nothing on purpose
                else:
                    raise Exception(f"Orth preceding not known {orth_preceding}")

                tweet_lemmatized += lex_lem

    return tweet_lemmatized


def remove_stop_words_from_text(text: str, stop_words: Set[str]) -> str:
    return " ".join(
        list(filter(lambda token: token not in stop_words, text.split(" ")))
    )


def jsonc_load(path: str):
    text = open(path, "r", encoding="utf-8").read()
    return json.loads(re.sub("//.*", "", text, flags=re.MULTILINE))
