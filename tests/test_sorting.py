"""정렬 회귀 테스트.

정답과 비교할 때 `sorted()` 를 오라클로 쓰지 않는다. 과제가 금지한 API 를
테스트에서 슬쩍 쓰면 "직접 구현했다" 는 주장이 흐려지고, 무엇보다 불필요하다.
대신 정렬 결과가 갖춰야 할 두 가지 성질을 직접 검사한다.

    ① 이웃한 두 원소의 키가 뒤집혀 있지 않다
    ② 원소 구성이 입력과 똑같다 (빠지거나 늘어난 것이 없다)

②가 없으면 ①은 쉽게 속는다 — 빈 목록도, 원소 하나짜리도 ①을 통과한다.
"""

import unittest

from mini_git.sorting import merge_sort


class Item:
    """같은 키를 여러 개 만들 수 있는 최소한의 원소.

    안정성을 검사하려면 "키는 같은데 서로 구별되는" 원소가 필요하다.
    tuple 이나 int 로는 키가 같으면 원소도 같아져서 순서가 지켜졌는지 알 수 없다.
    """

    def __init__(self, key, tag):
        self.key = key
        self.tag = tag

    def __repr__(self):
        return f"{self.key}:{self.tag}"


by_key = lambda item: item.key


class SortingPropertyTest(unittest.TestCase):
    """정렬 결과가 갖춰야 할 성질."""

    def assert_sorted(self, result, original, key):
        for i in range(1, len(result)):
            self.assertLessEqual(
                key(result[i - 1]), key(result[i]),
                f"{i - 1}번과 {i}번이 뒤집혀 있다: {result}",
            )
        self.assertEqual(len(result), len(original), "원소 개수가 달라졌다")
        for item in original:
            self.assertIn(item, result, f"{item!r} 가 사라졌다")

    def sort_ints(self, numbers):
        result = merge_sort(numbers, key=lambda n: n)
        self.assert_sorted(result, numbers, lambda n: n)
        return result

    def test_빈_목록(self):
        self.assertEqual(merge_sort([], key=lambda n: n), [])

    def test_원소_하나(self):
        self.assertEqual(self.sort_ints([7]), [7])

    def test_이미_정렬된_입력(self):
        self.assertEqual(self.sort_ints([1, 2, 3, 4, 5]), [1, 2, 3, 4, 5])

    def test_역순_입력(self):
        self.assertEqual(self.sort_ints([5, 4, 3, 2, 1]), [1, 2, 3, 4, 5])

    def test_뒤섞인_입력(self):
        self.assertEqual(self.sort_ints([3, 1, 4, 1, 5, 9, 2, 6]), [1, 1, 2, 3, 4, 5, 6, 9])

    def test_홀수_길이도_짝수_길이도(self):
        self.sort_ints([2, 1, 3])
        self.sort_ints([2, 1, 3, 0])

    def test_전부_같은_값(self):
        self.assertEqual(self.sort_ints([4, 4, 4, 4]), [4, 4, 4, 4])

    def test_큰_입력(self):
        # 선형 합동 생성기로 재현 가능한 난수열을 만든다 (random 모듈 불필요).
        numbers, seed = [], 12345
        for _ in range(500):
            seed = (seed * 1103515245 + 12345) % 2147483648
            numbers.append(seed % 1000)
        self.sort_ints(numbers)


class StabilityTest(unittest.TestCase):
    """같은 키끼리는 입력 순서를 보존한다.

    이 성질이 없으면 LOG --sort-by=author 의 같은 작성자끼리 순서가 흔들린다.
    """

    def test_같은_키의_원래_순서가_보존된다(self):
        items = [Item(2, "a"), Item(1, "b"), Item(2, "c"), Item(1, "d"), Item(2, "e")]
        result = merge_sort(items, key=by_key)
        self.assertEqual([i.tag for i in result], ["b", "d", "a", "c", "e"])

    def test_전부_같은_키면_순서가_그대로다(self):
        items = [Item(1, tag) for tag in "abcdefgh"]
        result = merge_sort(items, key=by_key)
        self.assertEqual([i.tag for i in result], list("abcdefgh"))

    def test_쪼개기_경계를_넘어서도_보존된다(self):
        # 길이 7 은 3/4 로 갈린다. 경계 양쪽에 같은 키를 흩어 두면
        # 병합에서 뒤쪽을 먼저 꺼내는 순간 순서가 깨진다.
        items = [Item(1, "a"), Item(1, "b"), Item(1, "c"),
                 Item(1, "d"), Item(1, "e"), Item(1, "f"), Item(1, "g")]
        result = merge_sort(items, key=by_key)
        self.assertEqual([i.tag for i in result], list("abcdefg"))


class KeyFunctionTest(unittest.TestCase):
    """비교 기준은 key 함수 하나로 갈아끼운다 (과제 §7)."""

    def test_기준을_바꾸면_결과가_바뀐다(self):
        items = [Item(3, "z"), Item(1, "y"), Item(2, "x")]
        self.assertEqual(
            [i.tag for i in merge_sort(items, key=lambda i: i.key)], ["y", "x", "z"]
        )
        self.assertEqual(
            [i.tag for i in merge_sort(items, key=lambda i: i.tag)], ["x", "y", "z"]
        )

    def test_문자열_키도_된다(self):
        names = ["Charlie", "alice", "Bob"]
        self.assertEqual(merge_sort(names, key=lambda s: s.lower()),
                         ["alice", "Bob", "Charlie"])


class NoMutationTest(unittest.TestCase):
    """원본을 건드리지 않는다."""

    def test_입력_목록이_그대로_남는다(self):
        numbers = [3, 1, 2]
        merge_sort(numbers, key=lambda n: n)
        self.assertEqual(numbers, [3, 1, 2])

    def test_새_목록을_돌려준다(self):
        numbers = [1]
        self.assertIsNot(merge_sort(numbers, key=lambda n: n), numbers)


if __name__ == "__main__":
    unittest.main()
