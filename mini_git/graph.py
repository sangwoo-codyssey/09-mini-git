"""커밋 그래프 위의 탐색 알고리즘.

`Repository` 는 상태를 들고 있고, 여기 함수들은 그 상태를 읽기만 한다.
그래서 인자로 `Repository` 가 아니라 `{해시 → Commit}` 딕셔너리를 받는다 —
테스트가 저장소를 세우지 않고 손으로 만든 그래프를 바로 넣을 수 있다.

⚠️ **간선 방향에 주의.** `Commit.parents` 는 자식이 부모를 가리키는 방향이다.
그런데 `LOG` 는 부모를 먼저 내야 하므로, 진행 방향은 그 반대인 부모→자식이다.
그래서 위상 정렬을 하려면 자식 목록을 따로 만들어 방향을 뒤집어야 한다.

    저장된 방향        c ──parents──> b ──parents──> a
    출력 순서          a ──────────>  b ──────────>  c
"""

from mini_git.repository import Commit


def _tiebreak_key(commit: Commit):
    """진입차수가 동시에 0이 된 커밋들 사이의 순서를 정하는 기준값.

    위상 정렬만으로는 순서가 하나로 정해지지 않는다. 갈라진 두 브랜치의 커밋은
    서로 조상 관계가 아니라 어느 쪽을 먼저 내도 "부모가 먼저" 규칙을 어기지 않기
    때문이다. 기준이 없으면 출력이 실행마다 흔들려 테스트를 못 쓴다.

    작은 값이 먼저 나온다.

    Args:
        commit: 후보 커밋.

    Returns:
        서로 비교 가능한 값. 두 커밋에 대해 절대 같은 값이 나오면 안 된다
        (같아지면 순서가 다시 미정이 된다).
    """
    # timestamp 가 1순위 — 만들어진 순서대로 나오는 것이 사람이 읽기에 자연스럽고
    # 과제 §8 예시의 출력 순서와도 맞는다. 다만 time.time() 이 같은 값을 두 번 낼
    # 수 있으므로 hash 를 2순위로 받쳐 둔다. hash 는 세션 내 유일하도록 만들어
    # 뒀으니(Repository._new_hash) 두 커밋의 기준값이 같아지는 일은 없다.
    return (commit.timestamp, commit.hash)


def _pop_smallest(ready: list[str], commits: dict[str, Commit]) -> str:
    """`ready` 에서 기준값이 가장 작은 해시를 빼서 돌려준다.

    `min()` 이나 `sorted()` 를 쓰지 않고 직접 훑는다. 과제가 정렬 표준 API 를
    금지하기도 하고, 후보가 몇 개 안 되는 목록이라 선형 탐색으로 충분하다.
    """
    best = 0
    for i in range(1, len(ready)):
        if _tiebreak_key(commits[ready[i]]) < _tiebreak_key(commits[ready[best]]):
            best = i
    return ready.pop(best)


def topological_order(commits: dict[str, Commit]) -> list[Commit]:
    """부모가 자식보다 항상 먼저 오는 순서로 커밋을 늘어놓는다 (Kahn 알고리즘).

    ① 각 커밋의 진입차수 = "저장소 안에 실제로 있는" 부모의 수
    ② 방향을 뒤집어 부모 → 자식 목록을 만든다
    ③ 진입차수 0인 것들(= 부모가 없는 뿌리)로 시작한다
    ④ 하나 꺼내 출력하고, 그 자식들의 진입차수를 1씩 줄인다
    ⑤ 0이 된 자식을 후보에 넣는다. 후보가 빌 때까지 반복

    ①의 "저장소 안에 실제로 있는" 이 중요하다. 부모 해시가 `commits` 에 없으면
    (지금은 생길 수 없지만) 그 간선은 셈에서 빼야 한다. 안 그러면 진입차수가
    영원히 0이 안 되어 그 커밋이 통째로 출력에서 사라진다.

    Args:
        commits: `{해시 → Commit}`. `Repository.commits` 를 그대로 넣으면 된다.

    Returns:
        위상 순서로 늘어놓은 `Commit` 목록. 빈 저장소면 빈 목록.

    Raises:
        RuntimeError: 순환이 있어 전부 출력하지 못했을 때. 커밋은 만들 때
            부모가 이미 존재하므로 순환은 생길 수 없다 — 이게 터지면 우리 버그다.
    """
    indegree: dict[str, int] = {}
    children: dict[str, list[str]] = {commit_hash: [] for commit_hash in commits}

    for commit_hash, commit in commits.items():
        known_parents = [p for p in commit.parents if p in commits]
        indegree[commit_hash] = len(known_parents)
        for parent in known_parents:
            children[parent].append(commit_hash)

    ready = [h for h, degree in indegree.items() if degree == 0]

    order: list[Commit] = []
    while ready:
        commit_hash = _pop_smallest(ready, commits)
        order.append(commits[commit_hash])
        for child in children[commit_hash]:
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)

    if len(order) != len(commits):
        raise RuntimeError(
            f"커밋 그래프에 순환이 있다: {len(commits)}개 중 {len(order)}개만 정렬됐다"
        )
    return order
