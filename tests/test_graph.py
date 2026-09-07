"""위상 정렬 회귀 테스트.

핵심 스펙은 딱 하나다 — **모든 부모가 자식보다 앞에 온다.**
순서를 통째로 하드코딩하지 않고 이 불변식을 인덱스로 검사한다. 그래야
타이브레이크 기준을 바꿔도 테스트가 안 깨지고, 진짜 요구만 못박힌다.

Repository 를 세우지 않고 손으로 만든 그래프를 넣는다. graph.py 가 저장소가
아니라 {해시 → Commit} 딕셔너리를 받도록 만든 이유가 이것이다.
"""

import unittest

from mini_git.graph import topological_order
from mini_git.repository import Commit


def build(*specs: tuple[str, tuple[str, ...]]) -> dict[str, Commit]:
    """`("b", ("a",))` 같은 (해시, 부모들) 쌍으로 그래프를 만든다.

    timestamp 는 나열 순서대로 0, 1, 2... 를 준다. 실제 저장소에서도 부모가
    자식보다 먼저 만들어지므로 이 규칙이 현실과 어긋나지 않는다.
    """
    return {
        commit_hash: Commit(
            hash=commit_hash,
            message=f"msg {commit_hash}",
            author="Alice",
            timestamp=float(i),
            parents=parents,
        )
        for i, (commit_hash, parents) in enumerate(specs)
    }


class TopologicalOrderTest(unittest.TestCase):
    def assert_parents_first(self, commits: dict[str, Commit]):
        """모든 커밋에 대해, 그 부모들이 자기보다 앞에 있는지 확인한다."""
        order = topological_order(commits)
        position = {commit.hash: i for i, commit in enumerate(order)}

        self.assertEqual(len(order), len(commits), "커밋이 빠지거나 중복됐다")
        for commit in order:
            for parent in commit.parents:
                self.assertLess(
                    position[parent],
                    position[commit.hash],
                    f"부모 {parent} 가 자식 {commit.hash} 보다 뒤에 있다",
                )
        return order

    def test_빈_저장소는_빈_목록(self):
        self.assertEqual(topological_order({}), [])

    def test_커밋_하나(self):
        order = topological_order(build(("a", ())))
        self.assertEqual([c.hash for c in order], ["a"])

    def test_선형_체인은_부모부터_나온다(self):
        order = self.assert_parents_first(
            build(("a", ()), ("b", ("a",)), ("c", ("b",)))
        )
        self.assertEqual([c.hash for c in order], ["a", "b", "c"])

    def test_갈라진_그래프(self):
        #   a ──┬── b        (feature)
        #       └── c        (main)
        self.assert_parents_first(build(("a", ()), ("b", ("a",)), ("c", ("a",))))

    def test_머지처럼_부모가_둘인_커밋(self):
        #   a ──┬── b ──┬── d      d 의 부모는 b, c 둘
        #       └── c ──┘
        order = self.assert_parents_first(
            build(("a", ()), ("b", ("a",)), ("c", ("a",)), ("d", ("b", "c")))
        )
        self.assertEqual(order[0].hash, "a")   # 뿌리가 유일하므로 첫 자리는 정해진다
        self.assertEqual(order[-1].hash, "d")  # 모든 것의 자손이므로 마지막

    def test_뿌리가_여럿일_수_있다(self):
        # INIT 을 다시 하지 않는 한 뿌리는 하나지만, 알고리즘은 여럿도 견뎌야 한다.
        self.assert_parents_first(
            build(("a", ()), ("x", ()), ("b", ("a",)), ("y", ("x",)))
        )

    def test_깊고_넓은_그래프(self):
        # a 에서 갈라진 가지 5개, 각각 길이 4
        specs: list[tuple[str, tuple[str, ...]]] = [("root", ())]
        for branch in range(5):
            parent = "root"
            for depth in range(4):
                name = f"b{branch}d{depth}"
                specs.append((name, (parent,)))
                parent = name
        self.assert_parents_first(build(*specs))

    def test_같은_입력이면_항상_같은_순서(self):
        # 타이브레이크 기준이 없으면 dict 순회 순서에 끌려다닌다.
        commits = build(("a", ()), ("b", ("a",)), ("c", ("a",)), ("d", ("a",)))
        first = [c.hash for c in topological_order(commits)]
        for _ in range(5):
            self.assertEqual([c.hash for c in topological_order(commits)], first)

    def test_저장소에_없는_부모는_간선에서_뺀다(self):
        # 부모 해시가 commits 에 없으면 진입차수가 영원히 0이 안 되어
        # 그 커밋이 출력에서 통째로 사라진다. 그 회귀를 막는다.
        orphan = {
            "b": Commit(
                hash="b", message="부모를 잃은 커밋", author="Alice",
                timestamp=1.0, parents=("사라진부모",),
            )
        }
        self.assertEqual([c.hash for c in topological_order(orphan)], ["b"])


if __name__ == "__main__":
    unittest.main()
