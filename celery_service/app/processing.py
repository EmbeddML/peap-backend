from random import random, randint
from typing import Dict
import pickle as pkl

from celery import Celery
import numpy as np

import celery_conf
from logger import get_logger

app = Celery()
app.config_from_object(celery_conf)

LOG = get_logger('PROCESSING')


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
