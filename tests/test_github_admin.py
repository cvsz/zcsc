from scripts.github_admin import REQUIRED_CHECKS, protection_payload


def test_branch_protection_requires_all_current_pull_request_checks():
    assert REQUIRED_CHECKS == (
        "repository-baseline",
        "test",
        "Analyze GitHub Actions",
        "CodeQL",
        "dependency-review",
    )
    assert protection_payload()["required_status_checks"] == {
        "strict": True,
        "contexts": list(REQUIRED_CHECKS),
    }


def test_branch_protection_fails_closed_for_admins_force_push_and_deletion():
    payload = protection_payload()

    assert payload["enforce_admins"] is True
    assert payload["allow_force_pushes"] is False
    assert payload["allow_deletions"] is False
    reviews = payload["required_pull_request_reviews"]
    assert reviews["required_approving_review_count"] == 1
    assert reviews["dismiss_stale_reviews"] is True
    assert reviews["require_code_owner_reviews"] is True
    assert reviews["require_last_push_approval"] is True
