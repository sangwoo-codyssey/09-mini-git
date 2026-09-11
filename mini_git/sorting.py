"""정렬 알고리즘 직접 구현.

과제 §7 이 `sorted()` / `list.sort()` 를 전면 금지한다. §3 학습목표 4 는
평균/최악 시간복잡도와 안정 정렬 여부를 설명할 수 있어야 한다고 요구하므로,
그 둘을 아래에 남긴다.

**병합 정렬(merge sort)**

    평균     O(n log n)
    최악     O(n log n)   ← 입력이 어떻게 생겼든 같다
    공간     O(n)         ← 병합할 때 새 목록을 만든다
    안정성   안정         ← 키가 같으면 원래 순서를 보존한다

퀵 정렬이 아니라 병합 정렬을 고른 이유가 뒤의 두 줄이다.

- **최악이 평균과 같다.** 퀵 정렬은 평균 O(n log n) 이지만 피벗이 계속 치우치면
  O(n²) 로 떨어진다. 이미 정렬된 입력에서 그렇게 되기 쉬운데, 커밋 목록은
  `topological_order` 를 거쳐 들어오므로 거의 정렬된 상태다 — 가장 나쁜 조합이다.
- **안정 정렬이다.** 이 성질을 `LOG --sort-by` 가 직접 써먹는다. 아래 설명 참고.

**안정성을 왜 쓰는가**

`LOG --sort-by=author` 는 작성자 이름만 보고 정렬한다. 같은 작성자의 커밋이
수두룩할 텐데, 그 안의 순서는 무엇이 정할까? 답은 "정렬 전 순서" 다.
들어오는 목록이 이미 위상 순서(부모가 자식보다 먼저)로 늘어서 있으므로,
안정 정렬은 그 순서를 그대로 남긴다. 2순위 비교 기준을 따로 만들 필요가 없다.

불안정 정렬을 쓰면 같은 작성자끼리의 순서가 실행마다 흔들려, 2순위 기준을
직접 짜 넣어야 한다. 안정성은 그 일을 공짜로 해준다.
"""

from typing import Any, Callable, TypeVar

T = TypeVar("T")
Key = Callable[[T], Any]
Pair = tuple[Any, Any]   # (키, 원소)


def _merge(left: list[Pair], right: list[Pair]) -> list[Pair]:
    """이미 정렬된 두 목록을 정렬을 유지한 채 하나로 합친다.

    양쪽 맨 앞을 견줘 작은 쪽을 꺼내 놓기를 반복하고, 한쪽이 바닥나면 남은
    쪽을 통째로 붙인다. 각 원소를 정확히 한 번씩만 보므로 O(len(left) + len(right)).

    ⚠️ **이 함수가 정렬 전체의 안정성을 혼자 결정한다.** `merge_sort` 는 목록을
    앞쪽(`left`)과 뒤쪽(`right`)으로 자르므로, 키가 같을 때 어느 쪽을 먼저
    꺼내느냐가 곧 "원래 순서를 지키느냐" 가 된다.

    원소가 아니라 `(키, 원소)` 쌍을 다룬다. 키는 `merge_sort` 가 미리 뽑아
    붙여 놓은 것이라 여기서는 꺼내 쓰기만 한다 — `[0]` 이 그 키다.

    Args:
        left: 이미 정렬된 `(키, 원소)` 쌍 목록. 원본에서 **앞쪽**에 있던 것들이다.
        right: 이미 정렬된 `(키, 원소)` 쌍 목록. 원본에서 **뒤쪽**에 있던 것들이다.

    Returns:
        둘을 합쳐 정렬된 새 목록. 길이는 두 목록의 길이 합.

    Note:
        쌍끼리 통째로 비교하지 않고 `[0]` 만 견준다. 튜플 비교는 키가 같을 때
        원소끼리 비교로 넘어가는데, `Commit` 처럼 `<` 가 없는 객체에서 터진다.
    """
    left_index = 0
    right_index = 0
    result = []

    while len(result) != len(left)+len(right):

        left_value = None
        right_value = None

        if left_index < len(left):
            left_value = left[left_index][0]

        if right_index < len(right):
            right_value = right[right_index][0]

        if right_value is None:
            result.append(left[left_index])
            left_index += 1
        elif left_value is None:
            result.append(right[right_index])
            right_index += 1
        elif left_value <= right_value:
            result.append(left[left_index])
            left_index += 1
        else:
            result.append(right[right_index])
            right_index += 1

    return result






def _sort_pairs(pairs: list[Pair]) -> list[Pair]:
    """`(키, 원소)` 쌍 목록을 키 기준으로 정렬한다 — 병합 정렬의 재귀 뼈대.

    쪼개는 것 자체는 아무 일도 하지 않는다. 길이 1이 될 때까지 반으로 자르고,
    합치면서 비로소 정렬된다 — 일은 전부 `_merge` 가 한다.

        [c, a, b]
          ├── [c]          길이 1 이면 이미 정렬된 것이다
          └── [a, b]
                ├── [a]
                └── [b]
                     └── _merge([a], [b]) -> [a, b]
          └── _merge([c], [a, b]) -> [a, b, c]

    `pairs[:middle]` 은 사본을 만든다. 층마다 원소 전체가 한 번씩 복사되므로
    쪼개는 것만으로 O(n log n) 만큼 복사가 일어난다. 인덱스 범위만 넘기면
    없앨 수 있지만, `left` / `right` 라는 이름이 주는 "앞 절반 / 뒤 절반" 직관이
    인덱스 산수 뒤로 숨는다. 다루는 커밋이 수백 개 규모라 읽기 쉬운 쪽을 택했다.
    """
    if len(pairs) <= 1:
        return pairs

    middle = len(pairs) // 2
    return _merge(_sort_pairs(pairs[:middle]), _sort_pairs(pairs[middle:]))


def merge_sort(items: list[T], key: Key) -> list[T]:
    """`key` 가 뽑아낸 값의 오름차순으로 정렬한 **새 목록**을 돌려준다.

    원본을 건드리지 않는다. 제자리 정렬이 메모리는 덜 쓰지만, 부르는 쪽이
    원본을 계속 쓰고 있는데 몰래 순서가 바뀌는 사고가 더 비싸다.

    세 단계로 돈다.

        ① 포장   원소마다 key() 를 한 번씩 불러 (키, 원소) 쌍을 만든다
        ② 정렬   쌍 목록을 키 기준으로 병합 정렬한다
        ③ 해체   쌍에서 원소만 도로 빼낸다

    ①이 있는 이유는 호출 횟수다. 정렬하면서 그때그때 `key()` 를 부르면 같은
    원소의 키를 층마다 다시 계산해 원소당 O(log n) 번 불린다 — 1000개에서
    18.7회까지 나왔다. 미리 한 번씩 뽑아 두면 정확히 n 번으로 끝난다.
    키가 값싼 지금은 체감이 없지만, 문자열 정규화나 날짜 파싱처럼 비싼 키라면
    이 차이가 실행 시간을 지배한다. 파이썬 내장 `sorted(key=...)` 도 같은 이유로
    같은 수법을 쓴다 (decorate–sort–undecorate).

    Args:
        items: 정렬할 목록. 바뀌지 않는다.
        key: 원소에서 비교할 값을 뽑는 함수. 이 인자 하나로 비교 기준을
            갈아끼운다 (과제 §7 "비교 기준을 바꿔 정렬할 수 있어야 한다").
            원소당 정확히 한 번 불린다.

    Returns:
        정렬된 새 목록.
    """
    pairs = [(key(item), item) for item in items]     # ① 포장
    pairs = _sort_pairs(pairs)                        # ② 정렬
    return [item for _, item in pairs]                # ③ 해체
