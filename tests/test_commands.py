"""명령 라우팅 · 인자 검증 · 출력 문구 회귀 테스트.

REPL 을 거치지 않고 run_line 을 직접 부른다. 표준입력을 흉내 낼 필요 없이
"한 줄 넣으면 무엇이 나오나" 만 보면 되기 때문이다.
"""

import unittest

from mini_git.cli import run_line
from mini_git.errors import (
    InvalidArgs,
    NotInitialized,
    UnknownBranch,
    UnknownCommand,
)
from mini_git.repository import Repository


class RunLineTest(unittest.TestCase):
    def setUp(self):
        self.repo = Repository()

    def run_line(self, line: str) -> str | None:
        return run_line(self.repo, line)

    def test_빈_줄은_아무것도_출력하지_않는다(self):
        self.assertIsNone(self.run_line(""))
        self.assertIsNone(self.run_line("   "))

    def test_모르는_명령은_거절된다(self):
        with self.assertRaises(UnknownCommand):
            self.run_line("rebase main")

    def test_대소문자를_가리지_않는다(self):
        self.assertIn("Initialized", self.run_line('INIT "Alice"'))
        self.assertIn("first", self.run_line("Commit first"))


class InitCommandTest(unittest.TestCase):
    def setUp(self):
        self.repo = Repository()

    def test_출력에_브랜치와_사용자가_보인다(self):
        output = run_line(self.repo, 'init "Alice"')
        self.assertIn("Initialized repository.", output)
        self.assertIn("Current branch: main", output)
        self.assertIn("Current user: Alice", output)

    def test_따옴표로_감싼_이름의_공백이_살아남는다(self):
        run_line(self.repo, "init 'Alice Kim'")
        self.assertEqual(self.repo.author, "Alice Kim")

    def test_인자가_없으면_거절된다(self):
        with self.assertRaises(InvalidArgs):
            run_line(self.repo, "init")

    def test_따옴표를_빠뜨려_인자가_둘이_되면_거절된다(self):
        # 조용히 첫 번째만 쓰면 이름이 잘린 것을 사용자가 못 알아챈다.
        with self.assertRaises(InvalidArgs):
            run_line(self.repo, "init Alice Kim")


class CommitCommandTest(unittest.TestCase):
    def setUp(self):
        self.repo = Repository()
        run_line(self.repo, 'init "Alice"')

    def test_출력이_브랜치와_해시와_메시지를_담는다(self):
        output = run_line(self.repo, 'commit "Initial commit"')
        commit_hash = self.repo.branches["main"]
        self.assertEqual(output, f"[main {commit_hash}] Initial commit")

    def test_INIT_전에는_거절된다(self):
        with self.assertRaises(NotInitialized):
            run_line(Repository(), 'commit "nope"')

    def test_인자가_없으면_거절된다(self):
        with self.assertRaises(InvalidArgs):
            run_line(self.repo, "commit")


class BranchSwitchCommandTest(unittest.TestCase):
    def setUp(self):
        self.repo = Repository()
        run_line(self.repo, 'init "Alice"')
        run_line(self.repo, 'commit "Initial commit"')

    def test_브랜치_생성_출력(self):
        self.assertEqual(
            run_line(self.repo, "branch feature"), "Created branch: feature"
        )

    def test_전환_출력(self):
        run_line(self.repo, "branch feature")
        self.assertEqual(
            run_line(self.repo, "switch feature"), "Switched to branch: feature"
        )

    def test_없는_브랜치로는_전환할_수_없다(self):
        with self.assertRaises(UnknownBranch):
            run_line(self.repo, "switch nonexistent")


class ScenarioTest(unittest.TestCase):
    """과제 §8 결과 예시의 앞부분을 그대로 따라간다."""

    def test_갈라진_브랜치_시나리오(self):
        repo = Repository()
        for line in [
            'init "Alice"',
            'commit "Initial commit"',
            "branch feature",
            "switch feature",
            'commit "Add login feature"',
            "switch main",
            'commit "Add payment feature"',
        ]:
            run_line(repo, line)

        self.assertEqual(repo.head, "main")
        self.assertEqual(len(repo.commits), 3)

        login = repo.commits[repo.branches["feature"]]
        payment = repo.commits[repo.branches["main"]]
        self.assertEqual(login.message, "Add login feature")
        self.assertEqual(payment.message, "Add payment feature")
        self.assertEqual(login.parents, payment.parents)  # 같은 곳에서 갈라졌다


if __name__ == "__main__":
    unittest.main()
