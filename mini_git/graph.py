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


def undirected_adjacency(commits: dict[str, Commit]) -> dict[str, set[str]]:
    """커밋-부모 연결을 **무방향** 간선으로 본 인접 목록.

    `PATH` 가 이걸 쓴다. 과제 §4 는 최단 경로를 "커밋-부모 연결을 무방향 간선으로
    간주했을 때" 로 정의한다. 즉 자식에서 부모로 올라가는 것뿐 아니라 부모에서
    자식으로 내려가는 것도 한 걸음이다. 그래서 형제 커밋 둘 사이에도 공통 부모를
    거쳐 가는 길이 2짜리 경로가 생긴다 — 방향을 지키면 서로 도달할 수 없는데도.

    `topological_order` 와 반대로 여기서는 방향을 지우지, 뒤집지 않는다.
    """
    adjacency: dict[str, set[str]] = {commit_hash: set() for commit_hash in commits}
    for commit_hash, commit in commits.items():
        for parent in commit.parents:
            if parent in commits:
                adjacency[commit_hash].add(parent)
                adjacency[parent].add(commit_hash)
    return adjacency


def _bfs_distances(adjacency: dict[str, set[str]], start: str) -> dict[str, int]:
    """`start` 에서 각 커밋까지의 최소 간선 수.

    도달할 수 없는 커밋은 아예 키로 들어가지 않는다 — "거리를 모른다" 와
    "거리가 무한대다" 를 굳이 구분할 필요가 없기 때문이다.

    큐는 리스트에 읽기 위치(`head`)를 얹어 쓴다. `list.pop(0)` 는 매번 남은
    원소를 전부 앞으로 당겨 O(n) 이라, 그것만으로 BFS 가 O(V²) 가 된다.
    """
    distance = {start: 0}
    queue = [start]
    head = 0

    while head < len(queue):
        node = queue[head]
        head += 1
        for neighbor in adjacency[node]:
            if neighbor not in distance:   # 처음 닿았을 때가 곧 최단이다
                distance[neighbor] = distance[node] + 1
                queue.append(neighbor)
    return distance


def ancestors(commits: dict[str, Commit], start: str) -> dict[str, Commit]:
    """`start` 에서 부모를 따라 올라가 닿는 모든 커밋. **자기 자신은 뺀다.**

    여기서는 `undirected_adjacency` 를 쓰지 않는다. 조상은 방향이 있는 개념이라
    부모 쪽으로만 걸어야 한다. 무방향으로 돌면 형제와 자손까지 딸려 온다.

    Args:
        commits: `{해시 → Commit}`.
        start: 출발 커밋 해시. `commits` 안에 있어야 한다.

    Returns:
        조상들만 담은 `{해시 → Commit}`. 뿌리 커밋이면 빈 딕셔너리.
    """
    seen = {start}
    queue = [start]
    head = 0
    found: dict[str, Commit] = {}

    while head < len(queue):
        node = queue[head]
        head += 1
        for parent in commits[node].parents:
            if parent in commits and parent not in seen:
                seen.add(parent)
                found[parent] = commits[parent]
                queue.append(parent)
    return found


def _next_hop(
    adjacency: dict[str, set[str]], current: str, distance: dict[str, int]
) -> str:
    """`current` 에서 목표 쪽으로 한 칸 나아갈 이웃을 고른다.

    `distance` 는 **목표 커밋으로부터** 잰 거리다(출발점이 아니라). 그래서
    `distance` 가 1 작아지는 이웃으로만 걸으면 걸음마다 목표에 정확히 한 칸씩
    가까워지고, 도착했을 때의 총 걸음 수가 최단 거리와 같아진다.

    그런 이웃이 여럿일 수 있다. 그때 어느 쪽을 고르느냐가 과제 §4 의 사전순
    조건을 결정한다.

    Args:
        adjacency: 무방향 인접 목록.
        current: 지금 서 있는 커밋 해시.
        distance: 목표로부터의 거리. `current` 는 반드시 들어 있다.

    Returns:
        다음으로 밟을 커밋 해시.
    """
    # 정렬하지 않는다. 필요한 것은 최솟값 하나지 전체 순서가 아니다.
    # 조건 ① 을 통과한 것만 후보이므로 "아직 후보 없음" 을 None 으로 표현한다
    # (_pop_smallest 는 모두가 후보라 첫 원소를 그냥 잡을 수 있었다).
    # distance.get() 이 없는 키에 None 을 주므로, 목표에서 도달할 수 없는
    # 이웃은 숫자와 같아질 일이 없어 저절로 걸러진다.
    next_distance = distance[current] - 1

    next_hop = None

    for key in adjacency[current]:
        if distance.get(key) == next_distance:
            if next_hop is None or next_hop > key:
                next_hop = key
    return next_hop


def shortest_path(
    commits: dict[str, Commit], source: str, target: str
) -> list[str] | None:
    """`source` 에서 `target` 까지 간선 수가 가장 적은 경로.

    최단 경로가 여럿이면 `hash1->hash2->...` 문자열이 사전순으로 가장 작은
    것을 고른다(과제 §4).

    ⚠️ 이 사전순 선택은 **모든 해시의 길이가 같다** 는 전제 위에서만 그리디로
    옳다. 길이가 같으면 두 경로 문자열에서 처음 갈라지는 지점이 항상 같은 글자
    위치이므로, 그 자리의 해시를 작게 고르는 것이 곧 문자열을 작게 고르는 것이다.
    `Repository._new_hash` 가 항상 `HASH_LENGTH` 길이로 만들어 주니 성립한다.

    Args:
        commits: `{해시 → Commit}`.
        source: 출발 커밋 해시.
        target: 도착 커밋 해시. 둘 다 `commits` 안에 있어야 한다.

    Returns:
        `source` 로 시작해 `target` 으로 끝나는 해시 목록. 길이 1도 가능하다
        (`source == target`). 경로가 없으면 None.
    """
    adjacency = undirected_adjacency(commits)
    # 목표에서부터 거리를 잰다. 출발점에서 재면 "남은 거리" 를 알 수 없어
    # 어느 이웃이 목표에 가까워지는 쪽인지 판단할 수 없다.
    distance = _bfs_distances(adjacency, target)

    if source not in distance:
        return None

    path = [source]
    current = source
    while current != target:
        current = _next_hop(adjacency, current, distance)
        path.append(current)
    return path
