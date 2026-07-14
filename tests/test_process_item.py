import importlib.util
import sys
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


SCRIPT_PATH = Path(__file__).parents[1] / ".github" / "scripts" / "process_item.py"


def load_script():
    github_module = types.ModuleType("github")
    github_module.Github = object
    openai_module = types.ModuleType("openai")
    openai_module.OpenAI = object
    spec = importlib.util.spec_from_file_location("process_item", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)

    with patch.dict(sys.modules, {"github": github_module, "openai": openai_module}):
        spec.loader.exec_module(module)

    return module


class User:
    def __init__(self, login):
        self.login = login


class Reaction:
    def __init__(self, content, login):
        self.content = content
        self.user = User(login)


class Item:
    def __init__(self, reactions=(), comments=(), pull_request=None, number=1):
        self._reactions = reactions
        self._comments = comments
        self.pull_request = pull_request
        self.number = number

    def get_reactions(self):
        return self._reactions

    def get_comments(self, since):
        return self._comments


class PullRequestItem(Item):
    def get_reactions(self):
        raise AssertionError("pull requests must not be scanned as issues")

    def get_comments(self, since):
        raise AssertionError("pull request comments must not be scanned as issues")


class Repository:
    def __init__(self, issue160, issues):
        self.issue160 = issue160
        self.issues = issues

    def get_issue(self, number):
        return self.issue160

    def get_issues(self, state):
        return self.issues


class ProcessItemTests(unittest.TestCase):
    def setUp(self):
        self.script = load_script()

    def test_contributor_success_reaction_does_not_suppress_submission(self):
        item = Item((
            Reaction("rocket", "1c7"),
            Reaction("hooray", "contributor"),
        ))

        self.assertEqual(self.script.check_reactions(item), (True, False))

    def test_admin_success_reaction_marks_submission_complete(self):
        item = Item((
            Reaction("rocket", "1c7"),
            Reaction("hooray", "1c7"),
        ))

        self.assertEqual(self.script.check_reactions(item), (True, True))

    def test_scanner_skips_pull_requests(self):
        issue160 = Item(number=160)
        pull_request = PullRequestItem(
            pull_request={"url": "https://api.github.com/repos/1c7/chinese-independent-developer/pulls/1"},
            number=1,
        )
        repository = Repository(issue160, (pull_request,))

        pending_items = self.script.collect_pending_items(
            repository, datetime(2026, 7, 14, tzinfo=timezone.utc)
        )

        self.assertEqual(pending_items, [])

    def test_scanner_keeps_admin_marked_issues(self):
        issue160 = Item(number=160)
        issue = Item(reactions=(Reaction("rocket", "1c7"),), number=2)
        repository = Repository(issue160, (issue,))

        pending_items = self.script.collect_pending_items(
            repository, datetime(2026, 7, 14, tzinfo=timezone.utc)
        )

        self.assertEqual(pending_items, [(issue, issue)])


if __name__ == "__main__":
    unittest.main()
