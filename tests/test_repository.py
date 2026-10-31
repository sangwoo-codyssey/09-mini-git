"""저장소 회귀 테스트.

여기 적힌 것이 곧 Repository 의 스펙이다.
"""

import unittest

from mini_git.errors import (
    BranchExists,
    NotInitialized,
    UnknownBranch,
)
from mini_git.repository import Commit, Repository


def fresh(author: str = "Alice") -> Repository:
    """INIT 까지 끝낸 저장소."""
    repo = Repository()
    repo.init(author)
    return repo


class InitTest(unittest.TestCase):
    """INIT 은 네 칸을 모두 세운다."""

    def test_main_브랜치가_생기고_HEAD_가_거기를_가리킨다(self):
        repo = fresh()
        self.assertEqual(repo.head, "main")
        self.assertIn("main", repo.branches)

    def test_커밋이_없으므로_main_은_아무것도_안_가리킨다(self):
        repo = fresh()
        self.assertIsNone(repo.branches["main"])
        self.assertEqual(repo.commits, {})

    def test_사용자가_설정된다(self):
        self.assertEqual(fresh("Bob").author, "Bob")

    def test_다시_부르면_기존_상태를_버린다(self):
        repo = fresh()
        repo.commit("first")
        repo.init("Bob")
        self.assertEqual(repo.commits, {})
        self.assertIsNone(repo.branches["main"])
        self.assertEqual(repo.author, "Bob")

    # 한 테스트에 셋을 몰아 두면 앞 명령이 막힐 때 뒤 명령 검사가 가려진다
    def test_INIT_전에는_commit_이_거절된다(self):
        with self.assertRaises(NotInitialized):
            Repository().commit("nope")

    def test_INIT_전에는_branch_가_거절된다(self):
        with self.assertRaises(NotInitialized):
            Repository().create_branch("feature")

    def test_INIT_전에는_switch_가_거절된다(self):
        with self.assertRaises(NotInitialized):
            Repository().switch("main")


class CommitTest(unittest.TestCase):
    """COMMIT 은 커밋을 등록하고 현재 브랜치를 그 위로 민다."""

    def test_첫_커밋은_부모가_없다(self):
        repo = fresh()
        commit = repo.commit("Initial commit")
        self.assertEqual(commit.parents, ())

    def test_커밋이_저장소에_등록된다(self):
        repo = fresh()
        commit = repo.commit("Initial commit")
        self.assertIs(repo.commits[commit.hash], commit)

    def test_현재_브랜치가_새_커밋을_가리킨다(self):
        repo = fresh()
        commit = repo.commit("Initial commit")
        self.assertEqual(repo.branches["main"], commit.hash)

    def test_연속_커밋의_부모는_직전_커밋이다(self):
        # branches[head] 를 미는 단계를 빠뜨리면 둘 다 부모가 first 가 되어
        # 납작한 그래프가 된다. 그 회귀를 막는 테스트.
        repo = fresh()
        first = repo.commit("first")
        second = repo.commit("second")
        third = repo.commit("third")
        self.assertEqual(second.parents, (first.hash,))
        self.assertEqual(third.parents, (second.hash,))

    def test_작성자와_메시지가_그대로_담긴다(self):
        repo = fresh("Alice")
        commit = repo.commit("Add login feature")
        self.assertEqual(commit.author, "Alice")
        self.assertEqual(commit.message, "Add login feature")

    def test_커밋은_불변이다(self):
        repo = fresh()
        commit = repo.commit("first")
        with self.assertRaises(Exception):
            commit.message = "바뀌면 해시와 어긋난다"

    def test_HEAD_는_커밋해도_그대로다(self):
        repo = fresh()
        repo.commit("first")
        self.assertEqual(repo.head, "main")


class HashTest(unittest.TestCase):
    """해시는 세션 내 유일해야 한다 (과제 §4)."""

    def test_같은_메시지를_반복해도_해시가_겹치지_않는다(self):
        repo = fresh()
        hashes = {repo.commit("same message").hash for _ in range(200)}
        self.assertEqual(len(hashes), 200)
        self.assertEqual(len(repo.commits), 200)

    def test_절단_충돌이_나면_다른_해시로_다시_만든다(self):
        # 200개 커밋 테스트로는 이 경로를 못 잡는다. 6자리 절단의 첫 충돌은
        # 수천 개째에나 나오기 때문이다. 그래서 충돌을 직접 만들어 준다.
        #
        # 재시도 때 sha256 입력이 그대로면 같은 후보가 다시 나와 무한 루프가 된다.
        # 그 버그가 있으면 이 테스트는 실패가 아니라 '멈춘다'.
        repo = fresh()
        counter_before = repo._counter
        first = repo._new_hash("msg", 1.0, ())

        repo.commits[first] = Commit(
            hash=first, message="자리를 막는 커밋", author="Alice",
            timestamp=1.0, parents=(),
        )
        repo._counter = counter_before  # 같은 입력에서 다시 출발하게 되돌린다

        again = repo._new_hash("msg", 1.0, ())
        self.assertNotEqual(again, first)
        self.assertNotIn(again, repo.commits)

    def test_해시는_짧은_16진_문자열이다(self):
        from mini_git.repository import HASH_LENGTH

        commit = fresh().commit("first")
        self.assertEqual(len(commit.hash), HASH_LENGTH)
        int(commit.hash, 16)  # 16진수로 못 읽으면 여기서 터진다


class BranchTest(unittest.TestCase):
    """BRANCH 는 만들기만 하고, SWITCH 만 HEAD 를 옮긴다."""

    def test_새_브랜치는_현재_커밋을_가리킨다(self):
        repo = fresh()
        commit = repo.commit("first")
        repo.create_branch("feature")
        self.assertEqual(repo.branches["feature"], commit.hash)

    def test_BRANCH_는_HEAD_를_옮기지_않는다(self):
        # 세션 중 가장 많이 헷갈렸던 곳. git branch f1 뒤에도 HEAD 는 그대로다.
        repo = fresh()
        repo.commit("first")
        repo.create_branch("feature")
        self.assertEqual(repo.head, "main")

    def test_커밋_전에_만든_브랜치는_아무것도_안_가리킨다(self):
        repo = fresh()
        repo.create_branch("feature")
        self.assertIsNone(repo.branches["feature"])

    def test_같은_이름은_거절된다(self):
        repo = fresh()
        with self.assertRaises(BranchExists):
            repo.create_branch("main")


class SwitchTest(unittest.TestCase):
    """SWITCH 는 HEAD 만 바꾼다."""

    def test_HEAD_가_옮겨간다(self):
        repo = fresh()
        repo.create_branch("feature")
        repo.switch("feature")
        self.assertEqual(repo.head, "feature")

    def test_없는_브랜치는_거절된다(self):
        repo = fresh()
        with self.assertRaises(UnknownBranch):
            repo.switch("nonexistent")

    def test_SWITCH_는_branches_를_건드리지_않는다(self):
        repo = fresh()
        repo.commit("first")
        repo.create_branch("feature")
        before = dict(repo.branches)
        repo.switch("feature")
        self.assertEqual(repo.branches, before)


class DivergingBranchTest(unittest.TestCase):
    """갈라졌다가 각자 커밋하면 DAG 가 갈라진다."""

    def test_두_브랜치가_같은_부모에서_갈라진다(self):
        repo = fresh()
        base = repo.commit("Initial commit")

        repo.create_branch("feature")
        repo.switch("feature")
        login = repo.commit("Add login feature")

        repo.switch("main")
        payment = repo.commit("Add payment feature")

        self.assertEqual(login.parents, (base.hash,))
        self.assertEqual(payment.parents, (base.hash,))
        self.assertEqual(repo.branches["feature"], login.hash)
        self.assertEqual(repo.branches["main"], payment.hash)

    def test_커밋은_어느_쪽에서도_해시로_찾을_수_있다(self):
        repo = fresh()
        base = repo.commit("Initial commit")
        repo.create_branch("feature")
        repo.switch("feature")
        login = repo.commit("Add login feature")

        self.assertEqual(len(repo.commits), 2)
        self.assertIn(base.hash, repo.commits)
        self.assertIn(login.hash, repo.commits)

    def test_브랜치와_HEAD_가_가리키는_곳이_늘_있다(self):
        repo = fresh()
        repo.create_branch("empty")  # 커밋 전에 만든 브랜치는 아무것도 안 가리킨다
        repo.commit("Initial commit")
        repo.create_branch("feature")
        repo.switch("feature")
        repo.commit("Add login feature")
        repo.switch("main")
        repo.commit("Add payment feature")

        self.assertIn(repo.head, repo.branches)
        self.assertIsNone(repo.branches["empty"])
        for name, commit_hash in repo.branches.items():
            if commit_hash is not None:
                self.assertIn(commit_hash, repo.commits, name)


if __name__ == "__main__":
    unittest.main()
