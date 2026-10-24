# Knesset 26 Forecast (Systematic Track)

This repository forecasts seats per list and national turnout for the 27 October 2026 Knesset election. It was built for the HUJI Department of Statistics and Data Science election-forecasting competition.

The method is summarised in [METHOD.md](METHOD.md), which is also the text submitted in the form.

## Run it

```bash
pip install -r requirements.txt
python -m tests.test_bader_ofer     # allocation code reproduces the official 2022 result
python forecast.py                  # writes output/forecast.csv and output/summary.json
python -m scripts.sensitivity       # optional: robustness table -> output/sensitivity.csv
```

`output/forecast.csv` has one row per list. Its columns are:
- the poll-average vote share;
- the simulated seat distribution (mean, 5th, 25th, 75th and 95th percentiles);
- the probability of passing the threshold;
- **`FORECAST`**, the submitted number.

## Pipeline

| Step | File | What it does |
|---|---|---|
| Polls to shares | `src/aggregate.py` | Converts published seats and sub-threshold percentages into implied vote shares |
| Aggregation | `src/aggregate.py` | Fits a weighted least-squares model per party, with house effects (zero-mean across houses) and recency weights (10-day half-life) |
| Simulation | `src/simulate.py` | Draws 20,000 election-day share vectors with party, bloc and Arab-turnout errors |
| Allocation | `src/bader_ofer.py` | Applies the 3.25% threshold, then Bader-Ofer with the five 2026 surplus-vote agreements |
| Point forecast | `src/simulate.py` | Takes each party's median seat count (which minimises expected absolute error), then adjusts so the total is 120 |
| Turnout | `src/turnout.py` | Fits OLS on 2015–2022 turnout, with whether the Joint List was united as the predictor |

All tunable assumptions are in `data/config.json`.

## Adding new polls

Append rows to `data/polls_manual.csv` and re-run `python forecast.py`. The Israeli silence law bars publishing polls after Friday 23 October, so this mostly means the final Thursday and Friday polls.

The CSV format is:
- one row per poll;
- seats as integers;
- lists below the threshold as a percentage with a `%` sign (for example `2.8%`);
- blank cells for lists the poll didn't report.

Every row must sum to 120 seats.

## Data sources

- **`data/polls_snapshot.csv`** — Seat-projection polls from 8 September to 8 October 2026. They come from the Wikipedia page [Opinion polling for the 2026 Israeli legislative election](https://en.wikipedia.org/wiki/Opinion_polling_for_the_2026_Israeli_legislative_election) (CC BY-SA 4.0), via the parsed snapshot in [razkaplan/primaries-selector](https://github.com/razkaplan/primaries-selector).
- **`data/polls_manual.csv`** — Polls from 11 to 21 October. I transcribed them from the same Wikipedia table and from the publishers' own reports (Kan 11, Channel 12/mako, Channel 13, Channel 14, i24NEWS, Walla, Maariv, Zman Yisrael, Channel 16).
- **`data/results_2022.csv`** — Official Central Elections Committee results for the 25th Knesset, used to validate the seat allocation.
- **`data/turnout_history.csv`** — Official national turnout for 2015–2022.
- **Surplus-vote agreements** — From Central Elections Committee filings, as reported on the Wikipedia page for the 2026 election.
