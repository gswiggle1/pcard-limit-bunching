# Text for the application box

**Project:** Do card limits change behavior? Evidence from 1.4M Oklahoma purchase-card transactions
**Link:** https://github.com/<your-username>/pcard-limit-bunching

**What I was trying to learn.** Whether corporate-card spending limits shape behavior: how much spend piles up just under a limit, whether that reflects split purchases, and whether the pile-up moves when the limit moves. Oklahoma publishes every government P-card transaction and raised its limit from $5,000 to $25,000 in January 2025, which makes a natural experiment.

**Why this approach.** No charge is labeled as a split purchase, so a supervised model had nothing to learn from. I used a bunching estimator from public finance: fit the smooth counterfactual distribution of transaction amounts and measure the excess just under the limit. Then I used the limit change and universities, which run their own programs, as a comparison group.

**How I validated it.** Placebo thresholds ($3k to $7k) show no bunching; the $5,000 excess is 11 standard errors from zero. After the change a new spike formed at $25,000 for agencies but not universities (z = 2.6). I audited the raw files (mislabeled months, duplicates, a look-alike report that created a false result in an early draft) and report a cardholder-level test that came back null. The main finding: one department (Transportation) ignored the higher limit entirely, so the limit set on each card matters more than the policy.
