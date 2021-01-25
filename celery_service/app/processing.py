from random import random, randint
from typing import Dict, List, Union, Tuple
import pickle as pkl

from celery import Celery
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation
import fasttext

import celery_conf
from logger import get_logger

app = Celery()
app.config_from_object(celery_conf)

LOG = get_logger('PROCESSING')

sentiment_model = fasttext.load_model('models/sentiment.bin')


@app.task(bind=True, name='clustering')
def calc_clustering(self, embedding: np.ndarray) -> Dict[str, int]:
    LOG.info('Clusters calculations - started')

    with open('models/kmeans.pkl.gz', 'rb') as f:
        kmeans = pkl.load(f)

    kmeans_cluster = kmeans.predict(embedding.reshape(1, -1))
    dbscan_cluster = randint(0, 6)
    pam_cluster = randint(0, 6)

    LOG.info('Clusters calculations - done')

    return {
        'kmeans_cluster': kmeans_cluster,
        'dbscan_cluster': dbscan_cluster,
        'pam_cluster': pam_cluster
    }


@app.task(bind=True, name='graph')
def calc_graph_pos(self, embedding: np.ndarray) -> Dict[str, float]:
    LOG.info('Graph calculations - started')
    #  TODO - when UMAP is ready use it here
    LOG.info('Graph calculations - done')

    return {
        '2D_x': random(),
        '2D_y': random(),
        '3D_x': random(),
        '3D_y': random(),
        '3D_z': random()
    }


@app.task(bind=True, name='topics')
def calc_topics(self, tweets: pd.DataFrame) -> Tuple[pd.DataFrame, List[Dict]]:
    LOG.info('Topics calculations - started')

    with open('models/vectorizer.pkl.gz', 'rb') as f:
        vectorizer: CountVectorizer = pkl.load(f)
    with open('models/lda.pkl.gz', 'rb') as f:
        lda: LatentDirichletAllocation = pkl.load(f)

    tweets_text = tweets['tweet'].tolist()
    counts = vectorizer.transform(tweets_text)
    probas = lda.transform(counts)

    labels = np.argmax(probas, axis=1)
    prob_values = np.max(probas, axis=1)

    tweets.loc[:, 'topic'] = labels
    tweets.loc[:, 'topic_proba'] = prob_values

    values = np.sum(probas, axis=0)
    distribution = values / np.sum(values)

    topics_distributions = [
        {
            'topic': t,
            'part': p
        }
        for t, p
        in zip(range(len(lda.components_)), distribution)
    ]

    LOG.info('Topics calculations - done')

    tweets = tweets[['id', 'topic', 'topic_proba']]
    return tweets, topics_distributions


@app.task(bind=True, name='sentiment')
def calc_sentiment(self, tweets: pd.DataFrame) -> Tuple[pd.DataFrame, List]:
    LOG.info('Sentiment calculations - started')

    tweets.loc[:, 'tweet'] = tweets['tweet'].apply(str.lower)
    tweets_text = tweets['tweet'].tolist()

    predictions = sentiment_model.predict(tweets_text)[0]
    predictions = [label for sublist in predictions for label in sublist]

    tweets['sentiment'] = predictions
    tweets.replace(to_replace={
        '__label__positive': 'positive',
        '__label__negative': 'negative',
        '__label__ambiguous': 'ambiguous',
        '__label__neutral': 'neutral'
    }, inplace=True)

    sent_values = ['negative', 'neutral', 'positive', 'ambiguous']
    sent_counts = tweets.sentiment.value_counts()
    tweets_count = sent_counts.sum()
    sentiment_dist = []
    for sent in sent_values:
        if sent in sent_counts.index:
            sentiment_dist.append((sent, sent_counts[sent] / tweets_count))
        else:
            sentiment_dist.append((sent, 0))

    LOG.info('Sentiment calculations - done')

    tweets = tweets[['id', 'sentiment']]
    return tweets, sentiment_dist


@app.task(bind=True, name='words')
def count_words(self, tweets: pd.DataFrame) -> List[Dict[str, float]]:
    LOG.info('Words count - started')

    with open('models/vectorizer.pkl.gz', 'rb') as f:
        vectorizer: CountVectorizer = pkl.load(f)

    tweets_text = tweets['tweet'].tolist()
    counts = vectorizer.transform(tweets_text)

    summed = np.sum(counts, axis=0)
    summed = np.array(summed).squeeze().tolist()

    words_counts = [
        {
            'text': name,
            'value': freq
        }
        for name, freq in zip(vectorizer.get_feature_names(), summed)
    ]

    words_counts.sort(key=lambda x: x['value'], reverse=True)

    LOG.info('Words count - done')

    return words_counts
