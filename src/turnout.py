"""National turnout: OLS of turnout on whether the Arab parties ran as one Joint List.

Rationale: in Israel's last six elections, turnout swings track Arab-sector turnout, which
has been markedly higher when Hadash, Ta'al and Balad ran together (2015, Sep 2019, 2020)
than when they split (Apr 2019, 2021, 2022). In 2026 the Joint List is reunited.
With n = 6 this is deliberately a tiny model; turnout only breaks ties in the competition.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def predict_turnout(path: str, joint_list_united: int = 1):
    df = pd.read_csv(path)
    X = np.column_stack([np.ones(len(df)), df["joint_list_united"].to_numpy()])
    y = df["turnout_pct"].to_numpy()
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    sigma = np.sqrt(resid @ resid / (len(y) - 2))
    pred = beta[0] + beta[1] * joint_list_united
    return float(pred), float(sigma), beta
