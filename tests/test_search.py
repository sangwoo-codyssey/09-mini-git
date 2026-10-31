"""검색 회귀 테스트.

여기 적힌 것이 곧 검색의 스펙이다. 나중에 역색인으로 갈아끼울 때
**이 테스트가 그대로 통과해야 한다** — 그것이 교체가 동작을 바꾸지 않았다는 증거다.
"""

import unittest

from mini_git.cli import run_line
from mini_git.repository import Commit, Repository
from mini_git.search import (
    InvertedIndex,
    scan_by_author,
    scan_by_keyword,
    tokenize_message,
)


def build(*specs: tuple[str, str, str]) -> dict[str, Commit]:
    """(해시, 메시지, 작성자) 쌍으로 커밋 목록을 만든다."""
    return {
        commit_hash: Commit(
            hash=commit_hash, message=message, author=author,
            timestamp=float(i), parents=(),
        )
        for i, (commit_hash, message, author) in enumerate(specs)
    }


SAMPLE = build(
    ("aa", "Add login feature", "Alice"),
    ("bb", "Fix login bug", "Bob"),
    ("cc", "Add payment feature", "Alice"),
    ("dd", "Refactor", "Carol"),
)


class TokenizeTest(unittest.TestCase):
    """메시지 → 키워드. 규칙은 split + lower 뿐이다 (과제 §4 최소 기준)."""

    def test_공백으로_쪼갠다(self):
        self.assertEqual(
            tokenize_message("Add login feature"), {"add", "login", "feature"}
        )

    def test_소문자로_정규화한다(self):
        self.assertEqual(tokenize_message("FIX Bug"), {"fix", "bug"})

    def test_같은_단어는_하나로_모인다(self):
        self.assertEqual(tokenize_message("fix fix Fix"), {"fix"})

    def test_빈_메시지는_빈_집합(self):
        self.assertEqual(tokenize_message(""), set())
        self.assertEqual(tokenize_message("   "), set())

    def test_연속_공백은_빈_토큰을_만들지_않는다(self):
        self.assertEqual(tokenize_message("a    b"), {"a", "b"})

    def test_구두점은_떼지_않는다(self):
        # 최소 기준만 따르므로 "fix:" 와 "fix" 는 다른 키워드다.
        self.assertEqual(
            tokenize_message("Fix: login bug,"), {"fix:", "login", "bug,"}
        )


class ScanByKeywordTest(unittest.TestCase):
    def found(self, keyword: str) -> set[str]:
        return set(scan_by_keyword(SAMPLE, keyword))

    def test_키워드를_가진_커밋을_찾는다(self):
        self.assertEqual(self.found("login"), {"aa", "bb"})

    def test_대소문자를_가리지_않는다(self):
        self.assertEqual(self.found("LOGIN"), {"aa", "bb"})
        self.assertEqual(self.found("Login"), {"aa", "bb"})

    def test_없는_키워드는_빈_결과(self):
        self.assertEqual(self.found("deploy"), set())

    def test_부분_문자열은_걸리지_않는다(self):
        # 토큰 단위 일치다. "log" 는 "login" 의 일부지만 별개의 단어다.
        self.assertEqual(self.found("log"), set())

    def test_여러_커밋이_같은_키워드를_공유한다(self):
        self.assertEqual(self.found("feature"), {"aa", "cc"})

    def test_빈_저장소(self):
        self.assertEqual(scan_by_keyword({}, "login"), [])


class ScanByAuthorTest(unittest.TestCase):
    def found(self, author: str) -> set[str]:
        return set(scan_by_author(SAMPLE, author))

    def test_작성자로_찾는다(self):
        self.assertEqual(self.found("Alice"), {"aa", "cc"})

    def test_대소문자를_가리지_않는다(self):
        self.assertEqual(self.found("alice"), {"aa", "cc"})

    def test_없는_작성자는_빈_결과(self):
        self.assertEqual(self.found("Dave"), set())

    def test_이름_전체가_맞아야_한다(self):
        # 작성자는 쪼개지 않는다. "Ali" 로는 "Alice" 를 못 찾는다.
        self.assertEqual(self.found("Ali"), set())


def indexed(commits: dict[str, Commit]) -> InvertedIndex:
    """커밋들을 전부 색인에 넣어 돌려준다."""
    index = InvertedIndex()
    for commit in commits.values():
        index.add(commit)
    return index


class InvertedIndexTest(unittest.TestCase):
    """색인이 두 종류를 모두 갖추고, 조회가 맞는 해시를 돌려준다."""

    def setUp(self):
        self.index = indexed(SAMPLE)

    def test_두_색인이_모두_채워진다(self):
        self.assertTrue(self.index.by_keyword)
        self.assertTrue(self.index.by_author)

    def test_키워드로_찾는다(self):
        self.assertEqual(set(self.index.find_by_keyword("login")), {"aa", "bb"})

    def test_작성자로_찾는다(self):
        self.assertEqual(set(self.index.find_by_author("Alice")), {"aa", "cc"})

    def test_대소문자를_가리지_않는다(self):
        self.assertEqual(set(self.index.find_by_keyword("LOGIN")), {"aa", "bb"})
        self.assertEqual(set(self.index.find_by_author("ALICE")), {"aa", "cc"})

    def test_없는_키는_빈_목록(self):
        self.assertEqual(self.index.find_by_keyword("deploy"), [])
        self.assertEqual(self.index.find_by_author("Dave"), [])

    def test_clear_로_비운다(self):
        self.index.clear()
        self.assertEqual(self.index.find_by_keyword("login"), [])
        self.assertEqual(self.index.find_by_author("Alice"), [])

    def test_조회_결과를_고쳐도_색인이_안_망가진다(self):
        found = self.index.find_by_keyword("login")
        found.clear()
        self.assertEqual(set(self.index.find_by_keyword("login")), {"aa", "bb"})

    def test_같은_단어가_여러_번_나와도_한_번만_등록된다(self):
        index = indexed(build(("aa", "fix fix Fix", "Alice")))
        self.assertEqual(index.find_by_keyword("fix"), ["aa"])


class EquivalenceTest(unittest.TestCase):
    """순회와 역색인이 **같은 결과**를 낸다.

    이 Phase 에서 가장 값진 테스트다. 순회는 커밋을 직접 보므로 항상 진실을
    말한다. 색인이 어긋나면 검색 결과가 틀려도 에러가 안 나는데, 이 비교가
    그 침묵을 깬다. 순회 버전을 지우지 않고 남겨 둔 진짜 이유가 이것이다.
    """

    def setUp(self):
        self.commits = build(
            ("aa", "Add login feature", "Alice"),
            ("bb", "Fix login bug", "Bob"),
            ("cc", "Add payment feature", "Alice"),
            ("dd", "Refactor", "Carol"),
            ("ee", "fix FIX fix", "bob"),
            ("ff", "", "Alice"),
        )
        self.index = indexed(self.commits)

    def assert_same(self, scanned, indexed_result, label):
        self.assertEqual(
            set(scanned), set(indexed_result),
            f"{label}: 순회={sorted(scanned)} 색인={sorted(indexed_result)}",
        )

    def test_모든_키워드에서_일치한다(self):
        keywords = set()
        for commit in self.commits.values():
            keywords |= tokenize_message(commit.message)
        keywords |= {"deploy", "LOGIN", "Fix"}   # 없는 것과 대소문자 변형도 섞는다

        for keyword in keywords:
            self.assert_same(
                scan_by_keyword(self.commits, keyword),
                self.index.find_by_keyword(keyword),
                f"keyword={keyword!r}",
            )

    def test_모든_작성자에서_일치한다(self):
        authors = {c.author for c in self.commits.values()} | {"Dave", "ALICE"}
        for author in authors:
            self.assert_same(
                scan_by_author(self.commits, author),
                self.index.find_by_author(author),
                f"author={author!r}",
            )


class RepositoryIndexTest(unittest.TestCase):
    """저장소가 색인을 제때 갱신하는가."""

    def test_COMMIT_이_색인을_갱신한다(self):
        repo = Repository()
        run_line(repo, 'init "Alice"')
        run_line(repo, 'commit "Add login feature"')
        commit_hash = repo.branches["main"]
        self.assertEqual(repo.index.find_by_keyword("login"), [commit_hash])
        self.assertEqual(repo.index.find_by_author("Alice"), [commit_hash])

    def test_INIT_이_색인을_비운다(self):
        # 안 비우면 사라진 커밋이 검색 결과에 유령으로 남는다.
        repo = Repository()
        run_line(repo, 'init "Alice"')
        run_line(repo, 'commit "Add login feature"')
        run_line(repo, 'init "Bob"')
        self.assertEqual(repo.index.find_by_keyword("login"), [])
        self.assertEqual(repo.index.find_by_author("Alice"), [])

    def test_저장소_전체가_순회와_일치한다(self):
        repo = Repository()
        run_line(repo, 'init "Alice"')
        for message in ["Initial commit", "Add login feature", "Fix login bug"]:
            run_line(repo, f'commit "{message}"')
        repo.author = "Bob"
        run_line(repo, 'commit "Add payment feature"')

        for keyword in ["login", "add", "feature", "deploy"]:
            self.assertEqual(
                set(scan_by_keyword(repo.commits, keyword)),
                set(repo.index.find_by_keyword(keyword)),
                f"keyword={keyword!r}",
            )
        for author in ["Alice", "Bob", "Carol"]:
            self.assertEqual(
                set(scan_by_author(repo.commits, author)),
                set(repo.index.find_by_author(author)),
                f"author={author!r}",
            )


if __name__ == "__main__":
    unittest.main()
