"""위상 정렬 회귀 테스트.

핵심 스펙은 딱 하나다 — **모든 부모가 자식보다 앞에 온다.**
순서를 통째로 하드코딩하지 않고 이 불변식을 인덱스로 검사한다. 그래야
타이브레이크 기준을 바꿔도 테스트가 안 깨지고, 진짜 요구만 못박힌다.

Repository 를 세우지 않고 손으로 만든 그래프를 넣는다. graph.py 가 저장소가
아니라 {해시 → Commit} 딕셔너리를 받도록 만든 이유가 이것이다.
"""

import unittest

from mini_git.graph import (
    ancestors,
    shortest_path,
    topological_order,
    undirected_adjacency,
)
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
                if parent not in commits:
                    continue  # 그래프 밖의 부모는 순서를 따질 대상이 아니다
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

    def test_부모가_자식보다_늦게_만들어져도_먼저_나온다(self):
        # build() 는 나열 순서대로 timestamp 를 매기고, 다른 테스트들은 부모를
        # 먼저 나열한다. 그래서 timestamp 순서가 우연히 위상 순서와 일치해,
        # "전부 timestamp 로 정렬" 하기만 해도 통과해 버린다.
        # 여기서는 자식을 먼저 나열해 그 우연을 깬다 — 부모의 timestamp 가 더 크다.
        commits = build(("bb", ("aa",)), ("aa", ()))
        self.assertEqual(commits["bb"].timestamp, 0.0)
        self.assertEqual(commits["aa"].timestamp, 1.0)

        order = self.assert_parents_first(commits)
        self.assertEqual([c.hash for c in order], ["aa", "bb"])

    def test_timestamp_가_거꾸로인_갈라진_그래프(self):
        #   cc ──┬── bb ──┬── aa      나열은 자식부터, timestamp 도 자식이 작다
        #   dd ──┘
        commits = build(("aa", ("bb", "dd")), ("bb", ("cc",)), ("cc", ()), ("dd", ()))
        self.assert_parents_first(commits)

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

    def test_없는_부모를_가진_커밋이_진짜_부모도_기다린다(self):
        # 위 테스트는 커밋이 하나뿐이라, 진입차수를 잘못 세도 통과할 수 있다.
        # (후보가 하나면 무엇을 꺼내든 답이 같다.)
        # 부모 하나는 저장소에 있고 하나는 없는 커밋으로 그 구멍을 막는다.
        commits = {
            "cc": Commit(hash="cc", message="자식", author="Alice",
                         timestamp=0.0, parents=("aa", "사라진부모")),
            "aa": Commit(hash="aa", message="부모", author="Alice",
                         timestamp=9.0, parents=()),
        }
        self.assertEqual(
            [c.hash for c in self.assert_parents_first(commits)], ["aa", "cc"]
        )

    def test_사이클이_있으면_ValueError(self):
        # 실제 저장소에서는 부모가 늘 먼저 저장되고 Commit 이 불변이라 만들 수 없는 입력이다.
        #   rr <- aa <-> bb   rr 은 나가지만, 그 뒤 aa 와 bb 가 서로를 기다린다.
        commits = build(("rr", ()), ("aa", ("rr", "bb")), ("bb", ("aa",)))
        with self.assertRaises(ValueError):
            topological_order(commits)


def diamond() -> dict[str, Commit]:
    """마름모. aa 에서 갈라져 dd 에서 다시 만난다 (머지 커밋 모양).

        aa ──┬── bb ──┬── dd
             └── cc ──┘

    해시 길이를 전부 2로 맞춘 것은 일부러다. shortest_path 의 사전순 선택은
    해시 길이가 같다는 전제 위에서만 그리디로 옳다.
    """
    return build(("aa", ()), ("bb", ("aa",)), ("cc", ("aa",)), ("dd", ("bb", "cc")))


class AdjacencyTest(unittest.TestCase):
    """무방향 인접 목록은 양쪽에 서로를 넣는다."""

    def test_부모와_자식이_서로를_이웃으로_갖는다(self):
        adjacency = undirected_adjacency(build(("aa", ()), ("bb", ("aa",))))
        self.assertEqual(adjacency["aa"], {"bb"})
        self.assertEqual(adjacency["bb"], {"aa"})

    def test_저장소에_없는_부모는_간선이_되지_않는다(self):
        commits = {
            "bb": Commit(
                hash="bb", message="고아", author="Alice",
                timestamp=1.0, parents=("없는부모",),
            )
        }
        self.assertEqual(undirected_adjacency(commits), {"bb": set()})


class AncestorsTest(unittest.TestCase):
    """조상은 부모 방향으로만 올라간다 — 무방향이 아니다."""

    def test_뿌리는_조상이_없다(self):
        self.assertEqual(ancestors(build(("aa", ())), "aa"), {})

    def test_자기_자신은_조상이_아니다(self):
        commits = build(("aa", ()), ("bb", ("aa",)))
        self.assertEqual(set(ancestors(commits, "bb")), {"aa"})

    def test_체인을_끝까지_올라간다(self):
        commits = build(("aa", ()), ("bb", ("aa",)), ("cc", ("bb",)), ("dd", ("cc",)))
        self.assertEqual(set(ancestors(commits, "dd")), {"aa", "bb", "cc"})

    def test_머지_커밋은_양쪽_조상을_모두_갖는다(self):
        self.assertEqual(set(ancestors(diamond(), "dd")), {"aa", "bb", "cc"})

    def test_형제와_자손은_조상이_아니다(self):
        # bb 의 조상은 aa 뿐. 형제 cc 도, 자손 dd 도 아니다.
        # 무방향으로 돌면 셋 다 딸려 오므로, 방향을 지키는지 검사한다.
        self.assertEqual(set(ancestors(diamond(), "bb")), {"aa"})


class ShortestPathTest(unittest.TestCase):
    """간선을 무방향으로 보고 간선 수 최소 경로를 찾는다."""

    def test_같은_커밋이면_자기_자신_하나(self):
        self.assertEqual(shortest_path(build(("aa", ())), "aa", "aa"), ["aa"])

    def test_부모에서_자식으로_내려갈_수_있다(self):
        commits = build(("aa", ()), ("bb", ("aa",)))
        self.assertEqual(shortest_path(commits, "aa", "bb"), ["aa", "bb"])

    def test_자식에서_부모로_올라갈_수_있다(self):
        commits = build(("aa", ()), ("bb", ("aa",)))
        self.assertEqual(shortest_path(commits, "bb", "aa"), ["bb", "aa"])

    def test_형제끼리는_공통_부모를_거쳐_간다(self):
        # 방향을 지키면 bb 와 cc 는 서로 도달 불가다. 무방향이라 길이 2로 이어진다.
        self.assertEqual(shortest_path(diamond(), "bb", "cc"), ["bb", "aa", "cc"])

    def test_끊긴_그래프에는_경로가_없다(self):
        commits = build(("aa", ()), ("bb", ("aa",)), ("xx", ()), ("yy", ("xx",)))
        self.assertIsNone(shortest_path(commits, "bb", "yy"))

    def test_최단_경로가_여럿이면_사전순으로_작은_것(self):
        # aa->bb->dd 와 aa->cc->dd 둘 다 길이 2. "bb" < "cc" 이므로 앞의 것.
        self.assertEqual(shortest_path(diamond(), "aa", "dd"), ["aa", "bb", "dd"])

    def test_사전순_선택은_해시_이름에만_달렸다(self):
        # 같은 모양인데 가운데 두 해시 이름만 바꾼다. 선택이 따라 바뀌어야 한다.
        commits = build(("aa", ()), ("zz", ("aa",)), ("mm", ("aa",)), ("dd", ("zz", "mm")))
        self.assertEqual(shortest_path(commits, "aa", "dd"), ["aa", "mm", "dd"])

    def test_먼_길로_돌아가지_않는다(self):
        #   aa - bb - cc - dd   그리고   aa - dd  로 바로 가는 지름길
        commits = build(
            ("aa", ()), ("bb", ("aa",)), ("cc", ("bb",)), ("dd", ("aa", "cc"))
        )
        self.assertEqual(shortest_path(commits, "aa", "dd"), ["aa", "dd"])

    def test_부모가_둘인_커밋을_지나는_최단_경로(self):
        #   aa - bb - cc - dd   그리고   aa - cc  로 바로 잇는 간선 (cc 의 부모는 aa, bb 둘)
        commits = build(
            ("aa", ()), ("bb", ("aa",)), ("cc", ("aa", "bb")), ("dd", ("cc",))
        )
        self.assertEqual(shortest_path(commits, "aa", "dd"), ["aa", "cc", "dd"])


if __name__ == "__main__":
    unittest.main()
