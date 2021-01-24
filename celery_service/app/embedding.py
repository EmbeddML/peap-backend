from celery import Celery
import pandas as pd
import numpy as np

import celery_conf

app = Celery()
app.config_from_object(celery_conf)


def clean_tweets(tweets: pd.DataFrame) -> np.ndarray:
    pass
