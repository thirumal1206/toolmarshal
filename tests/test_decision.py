from toolmarshal.decision import Decision, Request, check


def test_allows_tool_on_allowlist() -> None:
    assert check(Request("read_file"), {"read_file"}) == Decision(
        allow=True, reason="tool 'read_file' is allowlisted"
    )


def test_denies_tool_not_on_allowlist() -> None:
    decision = check(Request("refund", {"amount": 500}), {"read_file"})
    assert decision == Decision(allow=False, reason="tool 'refund' is not allowlisted")


def test_denies_everything_when_allowlist_is_empty() -> None:
    assert not check(Request("read_file"), set()).allow


def test_tool_name_match_is_exact() -> None:
    assert not check(Request("read_file_all"), {"read_file"}).allow
    assert not check(Request("Read_File"), {"read_file"}).allow
