from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CODEQL_WORKFLOW = ROOT / ".github" / "workflows" / "codeql.yml"
DEPENDABOT = ROOT / ".github" / "dependabot.yml"
CODEQL_ACTION_SHA = "9b3254085494b55a0f7c4c2b3d2d52cc712ce370"


def test_codeql_init_and_analyze_use_the_same_immutable_revision():
    workflow = CODEQL_WORKFLOW.read_text(encoding="utf-8")
    revisions = re.findall(
        r"^\\s*uses:\\s*github/codeql-action/(?:init|analyze)@([0-9a-f]{40})\\b",
        workflow,
        re.MULTILINE,
    )

    assert revisions == [CODEQL_ACTION_SHA, CODEQL_ACTION_SHA]


def test_dependabot_groups_codeql_action_updates_together():
    config = DEPENDABOT.read_text(encoding="utf-8")
    github_actions_block = re.search(
        r"(?ms)^  - package-ecosystem: github-actions\\n(.*?)(?=^  - package-ecosystem:|\\Z)",
        config,
    )

    assert github_actions_block is not None
    assert re.search(
        r"(?ms)^    groups:\\n      codeql-action:\\n        patterns:\\n          - github/codeql-action/\\*$",
        github_actions_block.group(1),
    )
