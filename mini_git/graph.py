from mini_git.repository import Commit


def _hash_of(commit: Commit) -> str:
    """commit 객체를 받아 hash 값을 돌려준다.

    Commit 끼리는 크기를 비교할 수 없어서, topological_order 에서 min 의 key 로
    넘겨 후보 중 해시가 가장 작은 커밋을 고르는 데 쓴다.
    """
    return commit.hash


def topological_order(commits: dict[str, Commit]) -> list[Commit]:
    """해시를 키로 커밋을 담은 dict 를 받아, 부모가 자식보다 먼저 오도록 늘어놓은 커밋 list 를 돌려준다.

    부모가 모두 나간 커밋이 여럿이면 그중 해시가 가장 작은 것부터 내보낸다.
    부모 해시가 입력 dict 안에 없으면 그 부모는 이미 나간 것으로 보고, 부모가 없는 커밋처럼 다룬다.
    넘겨준 입력 dict 는 그대로다. dict 를 복사해서 쓴다.
    입력에 사이클이 있으면 ValueError 를 낸다.
    """
    remaining = dict(commits)
    order = []

    while remaining:
        candidates = []
        for commit in remaining.values():
            if not commit.parents:
                candidates.append(commit)
            else:
                has_remaining_parent = False
                for parent in commit.parents:
                    # parent항목이 remaining에 있는지 확인
                    if parent in remaining:
                        has_remaining_parent = True
                        break  # 남은 부모를 하나 만났으면 나머지 부모는 볼 필요 없다
                # 모든 parent가 없으면 candidates에 추가
                if not has_remaining_parent:
                    candidates.append(commit)

        chosen = min(candidates, key=_hash_of)
        order.append(chosen)
        # min이 결정되면 remaining에서 빼기 (hash 키로)
        del remaining[chosen.hash]

    return order


def undirected_adjacency(commits: dict[str, Commit]) -> dict[str, set[str]]:
    """해시를 키로 커밋을 담은 dict 를 받아, 해시를 키로 그 커밋의 이웃 해시들을 set 으로 담은 dict 를 돌려준다.

    부모와 자식이 서로의 이웃이다. 간선 하나를 양쪽 set 에 모두 적어 방향을 없앤다.
    부모 해시가 입력 dict 안에 없으면 그 부모와는 간선을 만들지 않는다.
    이웃이 없는 커밋도 빈 set 을 값으로 키를 가진다.
    """
    adjacency = {}
    for commit in commits.values():
        if commit.hash not in adjacency:
            adjacency[commit.hash] = set()
        for parent in commit.parents:
            if parent in commits:
                adjacency[commit.hash].add(parent)
                if parent not in adjacency:
                    adjacency[parent] = set()
                adjacency[parent].add(commit.hash)
    return adjacency


def ancestors(commits: dict[str, Commit], start: str) -> dict[str, Commit]:
    """해시를 키로 커밋을 담은 dict 와 시작 해시를 받아, 시작 커밋의 조상을 해시를 키로 담은 dict 를 돌려준다.

    부모 쪽으로만 올라간다. 자식이나 형제는 조상이 아니다.
    시작 커밋 자신은 결과에 들어가지 않는다.
    조상이 없으면 빈 dict 를 돌려준다.
    """
    commit = commits[start]
    visited = []
    to_visit = []
    result = {}
    for parent in commit.parents:
        to_visit.append(parent)
    while to_visit:
        commit_hash = to_visit.pop(0)
        visited.append(commit_hash)
        result[commit_hash] = commits[commit_hash]
        for parent in commits[commit_hash].parents:
            if parent not in visited and parent not in to_visit:
                to_visit.append(parent)
                result[parent] = commits[parent]
    return result


def shortest_path(
    commits: dict[str, Commit], source: str, target: str
) -> list[str] | None:
    """해시를 키로 커밋을 담은 dict 와 출발·도착 해시를 받아, 간선 수가 가장 적은 경로를 해시 list 로 돌려준다.

    커밋-부모 연결을 방향 없는 간선으로 보고 undirected_adjacency 의 이웃 표를 따라간다.
    최단 경로가 여럿이면 경로를 이은 문자열이 사전순으로 가장 작은 것을 고른다.
    출발과 도착이 같으면 [출발] 을, 경로가 없으면 None 을 돌려준다.
    """
    if source == target:
        return [source]
    adjacency = undirected_adjacency(commits)
    current = source
    visited = []
    to_visit = []
    came_from = {}
    while True:
        visited.append(current)
        neighbors = adjacency[current]
        if target in neighbors:
            came_from[target] = current
            current = target
            break
        remaining = set(neighbors)
        while remaining:
            smallest = min(remaining)
            if smallest not in visited and smallest not in to_visit:
                to_visit.append(smallest)
                came_from[smallest] = current
            remaining.remove(smallest)
        if not to_visit:
            return None
        current = to_visit.pop(0)
    path = [current]
    while current != source:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path
