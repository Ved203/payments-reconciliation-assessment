from reconciliation import generate_test_data, reconcile

def run_tests():
    platform, bank = generate_test_data()
    report, merged, exceptions_df = reconcile(platform, bank, target_month="2025-01")

    issue_types = set(exceptions_df["issue_type"].dropna().tolist())

    assert "settled_next_month" in issue_types, "Failed: next month settlement not detected"
    assert "duplicate_in_platform" in issue_types, "Failed: platform duplicate not detected"
    assert "duplicate_in_bank" in issue_types, "Failed: bank duplicate not detected"
    assert "orphan_refund" in issue_types, "Failed: orphan refund not detected"
    assert "aggregate_rounding_difference" in issue_types, "Failed: aggregate rounding difference not detected"
    assert report["total_exceptions"] > 0, "Failed: no exceptions found"

    print("All tests passed!")

if __name__ == "__main__":
    run_tests()
