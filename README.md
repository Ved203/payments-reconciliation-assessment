# Payments Reconciliation Assessment

## Project Overview
This project solves a month-end reconciliation problem between a payments platform ledger and bank settlement records.

- The platform records transactions immediately when customers pay.
- The bank settles funds in batches 1–2 days later.
- The goal is to identify why month-end totals do not match and classify the reconciliation gaps.

## Problem Scenarios Intentionally Injected
This synthetic dataset includes the following four required gap types:

1. A transaction that settles in the following month
2. A rounding difference that only shows when summed
3. A duplicate entry in one dataset
4. A refund with no matching original transaction

## Technologies Used
- Python
- Pandas
- NumPy
- Streamlit
- GitHub
- Streamlit Cloud

## Assumptions
- Platform records transactions at payment time.
- Bank settles 1–2 days later.
- January 2025 is the reconciliation month.
- Matching is primarily by `transaction_id`.
- Bank stores settlement amounts at 2 decimal precision.
- Refunds are negative platform entries.
- A refund without a valid original transaction is an exception.
- Duplicate transaction IDs are treated as data quality exceptions.

## Files
- `reconciliation.py` → synthetic data generation + reconciliation logic
- `app.py` → Streamlit dashboard
- `tests.py` → validation tests
- `requirements.txt` → required dependencies

## How to Run
```bash
pip install -r requirements.txt
python reconciliation.py
python tests.py
streamlit run app.py
