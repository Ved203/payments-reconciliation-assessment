import streamlit as st
import pandas as pd
from reconciliation import generate_test_data, reconcile

st.set_page_config(page_title="Payments Reconciliation Assessment", layout="wide")

st.title("Payments Platform vs Bank Settlement Reconciliation")
st.caption("Synthetic month-end reconciliation for a fintech/payments company (January 2025)")

# Generate data and reconcile
platform, bank = generate_test_data()
report, merged, exceptions_df = reconcile(platform, bank, target_month="2025-01")

# KPI cards
st.subheader("Reconciliation Summary")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Platform Payments", report["platform_payment_count"])
with col2:
    st.metric("Bank Settlements (Jan)", report["bank_settlement_count_in_month"])
with col3:
    st.metric("Aggregate Difference", f"{report['aggregate_difference']:.2f}")
with col4:
    st.metric("Total Exceptions", report["total_exceptions"])

# Detailed summary
with st.expander("View Detailed Summary", expanded=True):
    st.json(report)

# Exception counts by type
st.subheader("Exception Breakdown")
if not exceptions_df.empty:
    issue_counts = exceptions_df["issue_type"].value_counts().reset_index()
    issue_counts.columns = ["issue_type", "count"]
    st.dataframe(issue_counts, use_container_width=True)
else:
    st.success("No exceptions found.")

# Data tabs
tab1, tab2, tab3, tab4 = st.tabs(["Platform Transactions", "Bank Settlements", "Reconciliation Report", "Exceptions"])

with tab1:
    st.dataframe(platform, use_container_width=True)

with tab2:
    st.dataframe(bank, use_container_width=True)

with tab3:
    st.dataframe(merged, use_container_width=True)

with tab4:
    st.dataframe(exceptions_df, use_container_width=True)

# Download section
st.subheader("Download Outputs")

platform_csv = platform.to_csv(index=False).encode("utf-8")
bank_csv = bank.to_csv(index=False).encode("utf-8")
merged_csv = merged.to_csv(index=False).encode("utf-8")
exceptions_csv = exceptions_df.to_csv(index=False).encode("utf-8")

d1, d2, d3, d4 = st.columns(4)

with d1:
    st.download_button("Download Platform CSV", platform_csv, "platform_transactions.csv", "text/csv")
with d2:
    st.download_button("Download Bank CSV", bank_csv, "bank_settlements.csv", "text/csv")
with d3:
    st.download_button("Download Reconciliation CSV", merged_csv, "reconciliation_report.csv", "text/csv")
with d4:
    st.download_button("Download Exceptions CSV", exceptions_csv, "exception_report.csv", "text/csv")

st.markdown("---")
st.markdown("### Assumptions")
st.markdown(
    """
- Platform records transactions immediately when a customer pays.
- Bank settles funds 1–2 days later.
- January 2025 is the target reconciliation month.
- Matching is primarily by transaction_id.
- Bank stores settlement amounts at 2 decimal precision.
- Refunds without a valid original transaction are flagged as data integrity exceptions.
- Duplicate transaction IDs are treated as operational/data quality exceptions.
"""
)
