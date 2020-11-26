import pandas as pd
from settings import DATA_DIRECTORY
from os.path import join
from typing import List
from models import TwitterUser, TwitterPoint3d
from random import random


def load_users() -> List[TwitterUser]:
    df = pd.read_csv(join(DATA_DIRECTORY, "accounts_processed.csv"), index_col=0)

    def user_from_row(row: pd.Series) -> TwitterUser:
        return TwitterUser(row["username"], row["party"], row["coalition"])

    users = df.apply(user_from_row, axis=1).tolist()
    return users


def get_points(users: List[TwitterUser]) -> List[TwitterPoint3d]:
    def rand():
        return random() * 100

    def point_from_row(user: TwitterUser) -> TwitterPoint3d:
        return TwitterPoint3d(user.twitter_name, rand(), rand(), rand())

    points = list(map(point_from_row, users))
    return points