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
    UnknownCommit,
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


class LogCommandTest(unittest.TestCase):
    """LOG 는 부모가 자식보다 먼저 오게 출력한다."""

    def setUp(self):
        self.repo = Repository()
        run_line(self.repo, 'init "Alice"')

    def test_커밋이_없으면_알려준다(self):
        self.assertEqual(run_line(self.repo, "log"), "No commits yet.")

    def test_INIT_전에는_거절된다(self):
        with self.assertRaises(NotInitialized):
            run_line(Repository(), "log")

    def test_한_커밋이_두_줄로_나온다(self):
        run_line(self.repo, 'commit "Initial commit"')
        commit = self.repo.commits[self.repo.branches["main"]]

        first, second = run_line(self.repo, "log").split("\n")
        self.assertEqual(
            first,
            f"commit {commit.hash} (Alice, {commit.formatted_time}) [main]",
        )
        self.assertEqual(second, "Initial commit")

    def test_부모가_자식보다_먼저_나온다(self):
        run_line(self.repo, 'commit "first"')
        run_line(self.repo, 'commit "second"')
        output = run_line(self.repo, "log")
        self.assertLess(output.index("first"), output.index("second"))

    def test_갈라진_브랜치의_커밋이_전부_나온다(self):
        run_line(self.repo, 'commit "Initial commit"')
        run_line(self.repo, "branch feature")
        run_line(self.repo, "switch feature")
        run_line(self.repo, 'commit "Add login feature"')
        run_line(self.repo, "switch main")
        run_line(self.repo, 'commit "Add payment feature"')

        output = run_line(self.repo, "log")
        # 갈라졌어도 뿌리는 둘 다보다 앞이다.
        self.assertLess(output.index("Initial commit"), output.index("Add login"))
        self.assertLess(output.index("Initial commit"), output.index("Add payment"))
        self.assertIn("[feature]", output)
        self.assertIn("[main]", output)

    def test_브랜치_라벨은_끝에_있는_커밋에만_붙는다(self):
        run_line(self.repo, 'commit "first"')
        run_line(self.repo, 'commit "second"')
        first_line, _, second_line, _ = run_line(self.repo, "log").split("\n")
        self.assertNotIn("[main]", first_line)
        self.assertIn("[main]", second_line)

    def test_한_커밋을_여러_브랜치가_가리키면_모두_붙는다(self):
        run_line(self.repo, 'commit "first"')
        run_line(self.repo, "branch feature")
        header = run_line(self.repo, "log").split("\n")[0]
        self.assertIn("main", header)
        self.assertIn("feature", header)

    def test_아직_옵션은_받지_않는다(self):
        with self.assertRaises(InvalidArgs):
            run_line(self.repo, "log --sort-by=date")


class DivergedRepo(unittest.TestCase):
    """과제 §8 예시와 같은 갈라진 저장소를 세우는 공통 setUp."""

    def setUp(self):
        self.repo = Repository()
        run_line(self.repo, 'init "Alice"')
        run_line(self.repo, 'commit "Initial commit"')
        self.base = self.repo.branches["main"]

        run_line(self.repo, "branch feature")
        run_line(self.repo, "switch feature")
        run_line(self.repo, 'commit "Add login feature"')
        self.login = self.repo.branches["feature"]

        run_line(self.repo, "switch main")
        run_line(self.repo, 'commit "Add payment feature"')
        self.payment = self.repo.branches["main"]


class AncestorsCommandTest(DivergedRepo):
    def test_뿌리는_조상이_없다(self):
        self.assertEqual(
            run_line(self.repo, f"ancestors {self.base}"), "No ancestors."
        )

    def test_조상이_출력된다(self):
        output = run_line(self.repo, f"ancestors {self.login}")
        self.assertIn(self.base, output)
        self.assertIn("Initial commit", output)

    def test_형제는_조상이_아니다(self):
        output = run_line(self.repo, f"ancestors {self.login}")
        self.assertNotIn(self.payment, output)

    def test_없는_커밋은_거절된다(self):
        with self.assertRaises(UnknownCommit):
            run_line(self.repo, "ancestors deadbe")

    def test_INIT_전에는_거절된다(self):
        with self.assertRaises(NotInitialized):
            run_line(Repository(), "ancestors deadbe")


class PathCommandTest(DivergedRepo):
    def test_부모_자식_경로(self):
        self.assertEqual(
            run_line(self.repo, f"path {self.base} {self.payment}"),
            f"Path: {self.base} -> {self.payment}",
        )

    def test_형제끼리는_공통_부모를_거친다(self):
        self.assertEqual(
            run_line(self.repo, f"path {self.login} {self.payment}"),
            f"Path: {self.login} -> {self.base} -> {self.payment}",
        )

    def test_자기_자신까지의_경로(self):
        self.assertEqual(
            run_line(self.repo, f"path {self.base} {self.base}"),
            f"Path: {self.base}",
        )

    def test_인자가_둘이_아니면_거절된다(self):
        with self.assertRaises(InvalidArgs):
            run_line(self.repo, f"path {self.base}")

    def test_없는_커밋은_거절된다(self):
        with self.assertRaises(UnknownCommit):
            run_line(self.repo, f"path {self.base} deadbe")


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

        log = run_line(repo, "log")
        self.assertEqual(log.count("commit "), 3)

        base = login.parents[0]
        self.assertEqual(
            run_line(repo, f"path {base} {payment.hash}"),
            f"Path: {base} -> {payment.hash}",
        )
        self.assertIn(base, run_line(repo, f"ancestors {login.hash}"))


if __name__ == "__main__":
    unittest.main()
