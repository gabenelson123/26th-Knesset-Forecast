# Method (for the submission form, under 500 words)

**Model:** house-effect-adjusted poll aggregation, Monte Carlo simulation of election-day vote shares, exact Bader-Ofer seat allocation with the 2026 surplus-vote agreements, and an L1-optimal point forecast.

**1. Data.** All seat-projection polls published since the candidate lists were finalised (8 Sep 2026) up to the publication ban (23 Oct), 70 polls from 8 polling houses, taken from the Wikipedia opinion-polling page and the outlets' own reports. Each poll's parties sum to 120.

**2. Seats to vote shares.** Seats are a non-linear function of votes because of the 3.25% threshold. For each poll, a list below the threshold keeps its published percentage. A list with seats gets share = seats/120 × (100 − W), where W is the share wasted on sub-threshold lists in that poll plus 1% for the tail of tiny lists.

**3. Aggregation.** For each party I fit weighted least squares, share = μ + h(house) + ε. The weights are √(n/500) × 0.5^(age/10 days). House effects are constrained to average zero across houses, with each house counting once. This stops a prolific house, such as Channel 14 (Likud +6.4 points relative to the field), from dragging the anchor. μ is the election-day estimate.

**4. Uncertainty.** I draw 20,000 election-day share vectors from three error sources:
- a party error with SD 0.25·√share (about 1.4 seats for an 18% party);
- a correlated bloc swing between the right-wing and Jewish-opposition parties (SD 1 point);
- a common Arab-turnout shock to the Joint List and Ra'am (log-SD 0.12).

**5. Allocation.** Each simulated result is turned into seats as the law does it:
- the 3.25% threshold;
- an initial quota;
- the remaining seats by Bader-Ofer (D'Hondt) for the five surplus-agreement pairs (Likud–RZP-Zehut, Shas–UTJ, Yashar–Democrats, Together–Yisrael Beiteinu, Joint List–Ra'am);
- each pair's seats split between its two lists by D'Hondt.

The allocation code reproduces the official 2022 result seat for seat.

**6. Point forecast.** The score is the sum of absolute seat errors. For each party, the value that minimises expected absolute error is the median of its simulated seat distribution. This handles threshold parties correctly: a list with a 22% chance of passing is forecast at 0, not at its mean of 0.9. If the medians don't sum to 120, I apply the ±1 adjustments that increase expected error least.

**7. Turnout.** Turnout is regressed on whether the Arab parties ran as a single Joint List, using the 2015–2022 elections (united: 71.2% on average; split: 68.8%). The Joint List is united in 2026, giving 71.2%.

**Robustness.** I re-ran the forecast without Channel 14, without Channel 14 and i24, with a 5- or 20-day half-life, and with 1.5× errors. Only Likud (20–23), the Joint List/Ra'am rounding, and the Reservists list's threshold call change.

**Main assumptions and risks:**
- On average, the polling houses are unbiased.
- There is no systematic Haredi or right-wing under-polling correction.
- Blue and White withdrew on 19 Oct and its ballot slips were removed from polling stations, so it is set to 0%.
