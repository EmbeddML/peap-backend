import pandas as pd
import pickle as pkl
from settings import DATA_DIRECTORY
from os.path import join
from typing import List, Dict
from models import Coalition, Party, User
from random import randint


def load_coalitions() -> List[Coalition]:
    df = pd.read_csv(join(DATA_DIRECTORY, "coalitions.csv"))

    coalitions = []

    for idx, coalition in enumerate(df.columns):
        coalitions.append(Coalition(coalition_id=idx, name=coalition))

    return coalitions


def load_parties() -> List[Party]:
    df = pd.read_csv(
        join(DATA_DIRECTORY, 'parties.csv'),
        names=['id', 'party', 'coalition'], header=0)

    def party_from_row(row: pd.Series) -> Party:
        return Party(
            party_id=row['id'],
            name=row['party'],
            coalition=row['coalition'])

    parties = df.apply(party_from_row, axis=1).tolist()

    return parties


def load_users() -> List[User]:
    users = pd.read_csv(join(DATA_DIRECTORY, "users.csv"))
    graph = pd.read_csv(join(DATA_DIRECTORY, "graph_tsne.csv"))
    clusters = pd.read_csv(join(DATA_DIRECTORY, "clusters.csv"))

    users['username'] = users['username'].str.lower()

    df = users.merge(graph, on='username', how='right')
    df = df.merge(clusters, on='username')

    def user_from_row(row: pd.Series) -> User:
        return User(
            username=row['username'],
            party=row['party'],
            coalition=row['coalition'],
            role=row['pozycja'],
            name=row['name'],
            tweets_count=row['tweets_count'],
            x_graph2d=row['2D_x'],
            y_graph2d=row['2D_y'],
            x_graph3d=row['3D_x'],
            y_graph3d=row['3D_y'],
            z_graph3d=row['3D_z'],
            cluster_dbscan_id=randint(0, 6),
            cluster_kmeans_id=row['kmeans_cluster'],
            cluster_pam_id=randint(0, 6)
        )

    users = df.apply(user_from_row, axis=1).tolist()

    return users


def load_topics_distributions() -> Dict[str, Dict[str, List]]:
    with open(join(DATA_DIRECTORY, 'topics_distributions.pkl.gz'), 'rb') as f:
        topics_dist = pkl.load(f)

    return topics_dist
