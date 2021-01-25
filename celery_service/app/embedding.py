import torch
from transformers import AutoTokenizer, AutoModel

from celery import Celery
import pandas as pd
import numpy as np

import celery_conf
from logger import get_logger

tokenizer = AutoTokenizer.from_pretrained("allegro/herbert-base-cased")
model = AutoModel.from_pretrained("allegro/herbert-base-cased")

app = Celery()
app.config_from_object(celery_conf)

LOG = get_logger('EMBEDDING')


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i: i + n]


def embed_tweets(tweets_data: pd.DataFrame) -> np.ndarray:
    tweet_texts = tweets_data["tweet"].tolist()
    tweet_embeddings = []
    with torch.no_grad():
        for idx, batch in enumerate(chunks(tweet_texts, 150)):
            LOG.info(f'{idx + 1}, {150}')
            # LOG.info(batch[0])
            # LOG.info(len(batch))
            tokenized_text = tokenizer.batch_encode_plus(
                batch, padding="longest", add_special_tokens=True,
                return_tensors="pt"
            )
            # LOG.info(idx)
            # LOG.info(tokenized_text)
            outputs = model(**tokenized_text)
            # LOG.info(idx)
            batch_embeddings = outputs[1].cpu().numpy()
            tweet_embeddings.extend(batch_embeddings)

    all_embeddings = np.vstack(tweet_embeddings)
    account_embedding = np.mean(all_embeddings, axis=0).astype(np.float)

    return account_embedding


@app.task(bind=True, name='embedding')
def calc_embedding(self, tweets: pd.DataFrame) -> np.ndarray:
    LOG.info('Embedding calculation - started')
    res = embed_tweets(tweets)
    # res = np.random.random(768)
    LOG.info('Embedding calculation - done')

    return res


