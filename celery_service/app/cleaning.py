import json

from celery import Celery
import pandas as pd
import numpy as np

from utils import process_text, emoji2text_tweet, lemmatize, \
    remove_stop_words_from_text, jsonc_load

import celery_conf
from logger import get_logger

app = Celery()
app.config_from_object(celery_conf)

logger = get_logger('xxx')


@app.task(bind=True, name='clean')
def clean_tweets(self, df: pd.DataFrame) -> pd.DataFrame:
    logger.info('Cleaning - started')
    df = df[df["language"] == "pl"]

    df.loc[:, "tweet"] = df["tweet"].apply(process_text)

    df.loc[:, "tweet_length"] = df["tweet"].apply(len)
    df = df[df["tweet_length"] >= 20]
    df.drop(columns="tweet_length")

    logger.info('Cleaning - done')
    return df


@app.task(bind=True, name='emoji')
def emoji2text(self, df: pd.DataFrame) -> pd.DataFrame:
    logger.info('Emoji2text - started')
    with open('data/emojis.json') as f:
        emoji_mapping = json.load(f)
    emoji_mapping_items = emoji_mapping.items()
    df.loc[:, "tweet"] = df["tweet"].apply(
        lambda x: emoji2text_tweet(x, emoji_mapping_items))
    logger.info('Emoji2text - done')
    return df


@app.task(bind=True, name='lemmatize')
def lemmatization(self, df: pd.DataFrame) -> pd.DataFrame:
    logger.info('Lemma - started')
    pos_to_keep = {"subst", "depr", "ger"}
    df.loc[:, "tweet"] = df["tweet"].apply(
        lambda x: lemmatize(x, pos_to_keep, True).lower()
    )
    logger.info('Lemma - done')
    return df


@app.task(bind=True, name='stopwords')
def remove_stop_words(self, df: pd.DataFrame) -> pd.DataFrame:
    logger.info('Stop words - started')
    stop_words = set(jsonc_load('data/stopwords.jsonc'))

    df.loc[:, "tweet"] = df["tweet"].apply(
        lambda text: remove_stop_words_from_text(text, stop_words)
    )
    logger.info('Stop words - done')
    return df
