from celery import Celery
import pandas as pd
import twint

import celery_conf
from logger import get_logger

app = Celery()
app.config_from_object(celery_conf)

LOG = get_logger('TWINT')


@app.task(bind=True, name='get_tweets')
def download_tweets(self, username: str) -> pd.DataFrame:
    LOG.info(f'Gathering tweets for account: {username}')
    c = twint.Config()
    c.Username = username
    c.Pandas = True
    c.Hide_output = True
    c.Count = True
    c.Limit = None

    twint.run.Search(c)

    df = twint.storage.panda.Tweets_df

    df = df[['id', 'tweet', 'link', 'language', 'username']]

    return df
