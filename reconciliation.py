import pandas as pd
import numpy as np

# ----------------------------
# 1. Generate synthetic data
# ----------------------------
def generate_test_data():
    np.random.seed(42)

    # Base platform transactions for Jan 2025
    platform = pd.DataFrame({
        "transaction_id": [f"TXN{i:04d}" for i in range(1, 11)],
        "customer_id": [f"CUST{i:03d}" for i in range(1, 11)],
        "transaction_date": pd.to_datetime([
            "2025-01-05", "2025-01-08", "2025-01-10", "2025-01-12", "2025-01-15",
            "2025-01-20", "2025-01-25", "2025-01-28", "2025-01-30", "2025-01-31"
        ]),
        "amount": [100.125, 250.335, 75.555, 400.000, 120.499,
                   89.999, 150.250, 60.105, 300.455, 500.555],
        "type": ["payment"] * 10
    })

    # Add duplicate in platform (duplicate TXN0004)
    duplicate_row = platform[platform["transaction_id"] == "TXN0004"].copy()
    platform = pd.concat([platform, duplicate_row], ignore_index=True)

    # Ensure original_transaction_id exists before adding refund
    platform["original_transaction_id"] = None

    # Add refund with no matching original transaction
    refund = pd.DataFrame({
        "transaction_id": ["RFND9999"],
        "customer_id": ["CUST999"],
        "transaction_date": [pd.to_datetime("2025-01-22")],
        "amount": [-45.00],
        "type": ["refund"],
        "original_transaction_id": ["TXN9999"]  # doesn't exist
    })

    platform = pd.concat([platform, refund], ignore_index=True)

    # Create bank settlements based on unique platform payments only
    payments_only = platform[platform["type"] == "payment"].drop_duplicates(subset=["transaction_id"]).copy()

    bank = payments_only.copy()
    bank["settlement_date"] = bank["transaction_date"] + pd.to_timedelta(
        np.random.choice([1, 2], size=len(bank)), unit="D"
    )

    # Bank stores 2 decimal amounts
    bank["settled_amount"] = bank["amount"].round(2)

    # Keep only relevant columns
    bank = bank[["transaction_id", "settlement_date", "settled_amount"]]

    # Plant a transaction that settles in following month
    bank.loc[bank["transaction_id"] == "TXN0010", "settlement_date"] = pd.to_datetime("2025-02-02")

    # Plant duplicate in bank dataset (duplicate TXN0007)
    bank_duplicate = bank[bank["transaction_id"] == "TXN0007"].copy()
    bank = pd.concat([bank, bank_duplicate], ignore_index=True)

    # Plant a small hidden aggregate rounding effect
    bank.loc[bank["transaction_id"] == "TXN0001", "settled_amount"] = 100.12
    bank.loc[bank["transaction_id"] == "TXN0002", "settled_amount"] = 250.34
    bank.loc[bank["transaction_id"] == "TXN0003", "settled_amount"] = 75.55

    return platform.reset_index(drop=True), bank.reset_index(drop=True)

# ----------------------------
# 2. Reconciliation logic
# ----------------------------
def reconcile(platform, bank, target_month="2025-01"):
    exceptions = []

    platform = platform.copy()
    bank = bank.copy()

    # Add month fields
    platform["transaction_month"] = platform["transaction_date"].dt.to_period("M").astype(str)
    bank["settlement_month"] = bank["settlement_date"].dt.to_period("M").astype(str)

    platform_month = platform[platform["transaction_month"] == target_month].copy()
    bank_month = bank[bank["settlement_month"] == target_month].copy()

    # ---- Detect duplicates
    platform_dupes = platform_month[platform_month.duplicated(subset=["transaction_id"], keep=False)]
    bank_dupes = bank_month[bank_month.duplicated(subset=["transaction_id"], keep=False)]

    for _, row in platform_dupes.iterrows():
        exceptions.append({
            "issue_type": "duplicate_in_platform",
            "severity": "MEDIUM",
            "transaction_id": row["transaction_id"],
            "details": "Duplicate transaction found in platform dataset"
        })

    for _, row in bank_dupes.iterrows():
        exceptions.append({
            "issue_type": "duplicate_in_bank",
            "severity": "MEDIUM",
            "transaction_id": row["transaction_id"],
            "details": "Duplicate transaction found in bank settlement dataset"
        })

    # ---- Detect orphan refunds
    refunds = platform_month[platform_month["type"] == "refund"].copy()
    valid_transaction_ids = set(platform["transaction_id"].tolist())

    for _, row in refunds.iterrows():
        if row["original_transaction_id"] not in valid_transaction_ids:
            exceptions.append({
                "issue_type": "orphan_refund",
                "severity": "HIGH",
                "transaction_id": row["transaction_id"],
                "details": f"Refund references missing original transaction {row['original_transaction_id']}"
            })

    # ---- Reconcile unique platform payments to unique bank settlements
    platform_payments = (
        platform_month[platform_month["type"] == "payment"]
        .drop_duplicates(subset=["transaction_id"])
        .copy()
    )

    bank_unique = bank.drop_duplicates(subset=["transaction_id"]).copy()

    merged = platform_payments.merge(
        bank_unique,
        on="transaction_id",
        how="left"
    )

    # Settlement status classification
    merged["recon_status"] = "MATCHED"

    # ---- Identify next-month settlements
    merged["is_settled_next_month"] = (
        merged["settlement_date"].notna() &
        (merged["settlement_month"] > target_month)
    )

    for idx, row in merged[merged["is_settled_next_month"]].iterrows():
        merged.at[idx, "recon_status"] = "SETTLED_NEXT_MONTH"
        exceptions.append({
            "issue_type": "settled_next_month",
            "severity": "LOW",
            "transaction_id": row["transaction_id"],
            "details": f"Transaction dated {row['transaction_date'].date()} settled on {row['settlement_date'].date()}"
        })

    # ---- Identify missing settlements (not found at all)
    missing = merged[merged["settlement_date"].isna()]
    for idx, row in missing.iterrows():
        merged.at[idx, "recon_status"] = "MISSING_SETTLEMENT"
        exceptions.append({
            "issue_type": "missing_settlement",
            "severity": "HIGH",
            "transaction_id": row["transaction_id"],
            "details": "No matching bank settlement found"
        })

    # ---- Amount comparison at 2dp
    merged["platform_amount_2dp"] = merged["amount"].round(2)
    merged["amount_diff"] = merged["platform_amount_2dp"] - merged["settled_amount"]

    amount_mismatches = merged[
        merged["settled_amount"].notna() &
        (merged["amount_diff"].abs() > 0.009)
    ]

    for idx, row in amount_mismatches.iterrows():
        if merged.at[idx, "recon_status"] == "MATCHED":
            merged.at[idx, "recon_status"] = "AMOUNT_MISMATCH"
        exceptions.append({
            "issue_type": "amount_mismatch",
            "severity": "MEDIUM",
            "transaction_id": row["transaction_id"],
            "details": f"Platform={row['platform_amount_2dp']}, Bank={row['settled_amount']}, Diff={row['amount_diff']:.2f}"
        })

    # ---- Monthly totals
    platform_month_total_raw = round(platform_payments["amount"].sum(), 3)
    platform_month_total_2dp = round(platform_payments["amount"].round(2).sum(), 2)
    bank_month_total = round(bank_month["settled_amount"].sum(), 2)

    # Matched settled total in the target month (exclude next-month settlements)
    settled_in_month = merged[merged["settlement_month"] == target_month]
    matched_settled_total_in_month = round(settled_in_month["settled_amount"].sum(), 2)

    # Hidden aggregate difference after 2dp rounding
    aggregate_diff = round(platform_month_total_2dp - matched_settled_total_in_month, 2)

    if abs(aggregate_diff) > 0:
        exceptions.append({
            "issue_type": "aggregate_rounding_difference",
            "severity": "LOW",
            "transaction_id": None,
            "details": f"Aggregate difference after 2dp rounding = {aggregate_diff:.2f}"
        })

    # Summary report
    report = {
        "target_month": target_month,
        "platform_payment_count": len(platform_payments),
        "bank_settlement_count_in_month": len(bank_month),
        "platform_total_raw": platform_month_total_raw,
        "platform_total_2dp": platform_month_total_2dp,
        "bank_month_total": bank_month_total,
        "matched_settled_total_in_month": matched_settled_total_in_month,
        "aggregate_difference": aggregate_diff,
        "platform_duplicates": len(platform_dupes),
        "bank_duplicates": len(bank_dupes),
        "orphan_refunds": len([e for e in exceptions if e["issue_type"] == "orphan_refund"]),
        "next_month_settlements": len([e for e in exceptions if e["issue_type"] == "settled_next_month"]),
        "missing_settlements": len([e for e in exceptions if e["issue_type"] == "missing_settlement"]),
        "amount_mismatches": len([e for e in exceptions if e["issue_type"] == "amount_mismatch"]),
        "total_exceptions": len(exceptions)
    }

    exceptions_df = pd.DataFrame(exceptions)

    return report, merged, exceptions_df
