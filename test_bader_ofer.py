"""Back-test the allocation code on the official 2022 result (must reproduce all 120 seats)."""
from pathlib import Path

import pandas as pd

from src.bader_ofer import allocate

DATA = Path(__file__).resolve().parents[1] / "data"

AGREEMENTS_2022 = [
    ("Labor", "Meretz"),
    ("Likud", "Religious Zionism"),
    ("National Unity", "Yesh Atid"),
    ("Shas", "United Torah Judaism"),
]


def test_2022_official_result():
    df = pd.read_csv(DATA / "results_2022.csv")
    got = allocate(df["votes"].to_numpy(), df["list"].tolist(), AGREEMENTS_2022)
    expected = dict(zip(df["list"], df["seats"]))
    assert got == expected, {k: (got[k], expected[k]) for k in expected if got[k] != expected[k]}


def test_threshold_and_total():
    got = allocate([50, 30, 17, 3], list("abcd"), seats=120)
    assert got["d"] == 0 and sum(got.values()) == 120


if __name__ == "__main__":
    test_2022_official_result()
    test_threshold_and_total()
    print("all tests passed")
