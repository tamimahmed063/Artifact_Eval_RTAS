import pandas as pd
import math
from functools import reduce


def load_flow_data(file_path):
    return pd.read_csv(file_path)


def compute_hyperperiod(df):
    periods = df['Period'].tolist()
    w = df['w'].tolist()
    h = df['h'].tolist()

    k = [w[i] + h[i] for i in range(len(w))]
    products = [k[i] * periods[i] for i in range(len(k))]

    def lcm(a, b):
        return abs(a * b) // math.gcd(a, b)

    return reduce(lcm, products)