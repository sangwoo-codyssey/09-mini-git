# Mini Git

커밋이 언제 어떻게 쌓였는지 기록하는 작은 Git 이다. `mini-git>` 프롬프트 하나에서 명령 8개
(`INIT` · `BRANCH` · `SWITCH` · `COMMIT` · `LOG` · `PATH` · `ANCESTORS` · `SEARCH`)를 처리한다.

커밋들은 부모를 가리키는 **DAG(방향 비순환 그래프)** 로 저장되고, 명령마다 이 그래프를 다르게 읽는다.

| 명령 | 그래프를 읽는 방식 | 알고리즘 |
|---|---|---|
| `LOG` | 부모가 자식보다 먼저 오게 늘어놓는다 | 위상 정렬 |
| `ANCESTORS` | 부모 쪽으로만 거슬러 올라간다 | BFS (방향 있음) |
| `PATH` | 방향을 지우고 간선 수가 가장 적은 길을 찾는다 | BFS (무방향) |
| `LOG --sort-by` | 위상 순서를 입력으로 받아 다시 정렬한다 | 병합 정렬 (직접 구현) |
| `SEARCH` | 그래프를 돌지 않고 미리 만든 색인을 조회한다 | 역색인 |

표준 라이브러리만 쓴다. `sorted()` · `list.sort()` 는 쓰지 않는다.

## 빠른 시작

Python **3.10 이상**이 필요하다. macOS 기본 `python3` 는 3.9 라서, `run.sh` 가 3.10 이상인
인터프리터(`python3.14` … `python3.10`)를 자동으로 찾는다. 직접 고르려면 `PYTHON` 환경변수를 쓴다.

```bash
./run.sh run          # REPL 실행 (= python main.py)
./run.sh test         # 테스트 160개
./run.sh bench        # 순회 검색 vs 역색인 측정
PYTHON=python3.12 ./run.sh run
```

`exit` · `quit` · Ctrl-D 로 끝난다. Ctrl-C 는 지금 입력하던 줄만 버린다.

## 명령어

| 명령 | 하는 일 |
|---|---|
| `INIT <user_name>` | 저장소를 새로 만든다. `main` 브랜치(아직 커밋 없음)를 만들고 HEAD 를 그 위에 두고, 현재 사용자를 정한다. 다시 하면 처음 상태로 돌아간다 |
| `BRANCH <branch_name>` | 현재 브랜치가 가리키는 커밋에서 새 브랜치를 만든다. HEAD 는 옮기지 않는다 |
| `SWITCH <branch_name>` | HEAD 를 그 브랜치로 옮긴다. 이후 `COMMIT` 은 이 브랜치를 앞으로 민다 |
| `COMMIT <message>` | 현재 브랜치의 끝 커밋을 부모로 하는 새 커밋을 만들고, 역색인을 갱신한다 |
| `LOG` | 모든 커밋을 **부모가 자식보다 먼저** 오도록 출력한다 |
| `LOG --sort-by=date\|author` | 시각 또는 작성자 기준으로 정렬해 출력한다. 같은 값끼리는 위상 순서를 유지한다 |
| `PATH <commit1> <commit2>` | 커밋-부모 연결을 무방향으로 본 최단 경로. 여럿이면 `a -> b -> …` 문자열이 사전순으로 가장 작은 것. 없으면 `No path` |
| `ANCESTORS <commit_hash>` | 그 커밋에서 부모 쪽으로 닿는 모든 조상 (자기 자신은 빼고) |
| `SEARCH <keyword>` | 메시지에 그 키워드가 있는 커밋 (역색인) |
| `SEARCH --author=<name>` | 그 작성자의 커밋 (역색인) |

입력 규칙

- 명령 이름은 대소문자를 가리지 않는다. `INIT` 과 `init` 이 같다.
- 공백이 든 인자는 따옴표로 감싼다. `COMMIT "Add login feature"`, `INIT 'Alice Kim'`.
  여는 따옴표와 같은 문자로만 닫히므로 `"it's fine"` 안의 `'` 는 그냥 글자다.
- 옵션은 `--key=value` 하나의 형식만 쓴다.
- 키워드 검색은 공백으로 쪼갠 단어 단위이고 대소문자를 가리지 않는다. `SEARCH Login` 도 `login` 을 찾는다.

### 에러 메시지

사용자 입력 때문에 생긴 오류는 메시지만 출력하고 REPL 은 계속 돈다.
그 밖의 예외는 프로그램 버그이므로 숨기지 않고 그대로 드러나게 둔다.

| 메시지 | 언제 |
|---|---|
| `Not initialized: run INIT <user_name> first` | `INIT` 전에 다른 명령 |
| `Invalid args: …` | 인자 개수 · 형식이 틀림, 모르는 옵션, `--sort-by` 값이 `date` · `author` 가 아님 |
| `Unknown command: <name>` | 없는 명령 |
| `Unknown branch: <name>` | `SWITCH` 할 브랜치가 없음 |
| `Unknown commit: <hash>` | `PATH` · `ANCESTORS` 에 없는 해시 |
| `Branch already exists: <name>` | 같은 이름으로 `BRANCH` (덮어쓰면 기존 브랜치의 커밋을 잃는다) |
| `Unclosed quote: <quote>` | 따옴표가 닫히지 않은 채 줄이 끝남 |

## 동작 예시

해시는 커밋 시각이 재료에 들어가서 실행할 때마다 달라진다. 아래는 실제 실행 결과다.

```
mini-git> LOG
Not initialized: run INIT <user_name> first
mini-git> INIT Alice
Initialized repository.
Current branch: main
Current user: Alice
mini-git> COMMIT "Add login page"
[main ef3c06] Add login page
mini-git> BRANCH feature
Created branch: feature
mini-git> SWITCH feature
Switched to branch: feature
mini-git> COMMIT "Fix login bug"
[feature a25dab] Fix login bug
mini-git> COMMIT "Add search index"
[feature 3923ea] Add search index
mini-git> SWITCH main
Switched to branch: main
mini-git> COMMIT "Update README"
[main ad1517] Update README
mini-git> LOG
commit ef3c06 (Alice, 2026-10-30 13:12:00)
Add login page
commit a25dab (Alice, 2026-10-30 13:12:00)
Fix login bug
commit 3923ea (Alice, 2026-10-30 13:12:00) [feature]
Add search index
commit ad1517 (Alice, 2026-10-30 13:12:00) [main]
Update README
mini-git> PATH 3923ea ad1517
Path: 3923ea -> a25dab -> ef3c06 -> ad1517
mini-git> ANCESTORS 3923ea
commit ef3c06 (Alice, 2026-10-30 13:12:00)
Add login page
commit a25dab (Alice, 2026-10-30 13:12:00)
Fix login bug
mini-git> ANCESTORS ef3c06
No ancestors.
mini-git> SEARCH login
Found 2 commits:
commit ef3c06 (Alice, 2026-10-30 13:12:00)
Add login page
commit a25dab (Alice, 2026-10-30 13:12:00)
Fix login bug
mini-git> SWITCH nope
Unknown branch: nope
mini-git> PATH ef3c06 zzzzzz
Unknown commit: zzzzzz
mini-git> LOG --sort-by=size
Invalid args: LOG --sort-by must be one of: date|author
```

- `LOG` 의 `[feature]` · `[main]` 은 그 커밋을 끝으로 가리키는 브랜치다.
- `LOG` 순서: `ef3c06` 이 나간 뒤 후보는 `a25dab` 와 `ad1517` 이고, 해시가 작은 `a25dab` 가 먼저다.
  그다음 후보 `3923ea` · `ad1517` 중 `3923ea`. 어느 줄을 봐도 부모가 위에 있다.
- `PATH` 는 갈라진 두 브랜치의 끝을 공통 조상 `ef3c06` 을 거쳐 잇는다.

`No path` 는 뿌리가 둘일 때 나온다. 커밋 전에 만든 브랜치는 아무 커밋도 가리키지 않으므로,
거기서 한 첫 커밋은 부모가 없는 두 번째 뿌리가 된다.

```
mini-git> INIT Bob
Initialized repository.
Current branch: main
Current user: Bob
mini-git> BRANCH side
Created branch: side
mini-git> COMMIT "root a"
[main 4e1675] root a
mini-git> SWITCH side
Switched to branch: side
mini-git> COMMIT "root b"
[side cf68ab] root b
mini-git> PATH 4e1675 cf68ab
No path
```

## 구조 — 한 줄이 출력이 되기까지

```
입력 한 줄
  │
  ▼
cli.run_line ──── REPL 한 줄. MiniGitError 는 메시지만 찍고 계속
  │
  ▼
parser.parse ──── 문자열 → Command(name, args, options). 저장소는 모른다
  │
  ▼
commands.execute ─ HANDLERS[name] 로 핸들러를 고른다. 인자 개수 검사, 출력 문자열 만들기
  │
  ├──▶ Repository ─────────── 상태와 규칙 (커밋 · 브랜치 · HEAD · 사용자 · 색인)
  └──▶ graph · sorting · search  알고리즘. {해시: Commit} 만 받는다
```

```
09-mini-git/
├── main.py              진입점 → cli.main()
├── run.sh               run / test / bench
├── benchmark.py         순회 검색 vs 역색인 측정
├── mini_git/
│   ├── cli.py           REPL 루프, run_line (테스트 진입점)
│   ├── parser.py        한 줄 → Command (따옴표 · 대소문자 · --key=value)
│   ├── commands.py      명령 이름 → 핸들러, 인자 검사, 출력 형식
│   ├── repository.py    Commit, Repository, 해시 생성
│   ├── graph.py         위상 정렬 · 무방향 인접 목록 · 조상 · 최단 경로
│   ├── sorting.py       병합 정렬
│   ├── search.py        순회 검색, 역색인
│   └── errors.py        사용자 입력 오류 (MiniGitError 계열)
└── tests/               160개
```

층을 나눈 기준은 "누가 무엇을 아는가" 다.

- **parser** 는 문자열을 구조로 바꾸기만 한다. "그런 브랜치가 있나" 같은 판단은 하지 않는다.
- **commands** 는 인자 개수와 출력 형식을 맡는다. print 하지 않고 문자열을 돌려주므로,
  테스트가 화면 출력을 가로채지 않고 반환값을 바로 비교한다.
- **Repository** 는 상태를 바꾸는 규칙(브랜치 이동, 커밋 생성, 색인 갱신)을 맡는다.
- **graph · sorting · search** 는 `Repository` 가 아니라 `{해시: Commit}` dict 만 받는다.
  그래서 테스트는 저장소를 세우지 않고 손으로 만든 그래프를 바로 넣고, 여러 명령이 같은 함수를 나눠 쓴다.

| 함수 | 쓰는 곳 |
|---|---|
| `topological_order` | `LOG`, 그리고 `ANCESTORS` · `SEARCH` 결과의 출력 순서 |
| `merge_sort` | `LOG --sort-by` (입력은 `topological_order` 의 결과) |
| `undirected_adjacency` | `shortest_path` |

## 자료구조

### `Commit`

```python
@dataclass(frozen=True)
class Commit:
    hash: str
    message: str
    author: str
    timestamp: float
    parents: tuple[str, ...]   # 부모 해시. 첫 커밋은 (), 머지라면 둘 이상
```

`frozen` 이라 만든 뒤에는 부모를 바꿀 수 없다. 아래 DAG 성질이 여기서 나온다.

### `Repository`

| 필드 | 값 | 책임 |
|---|---|---|
| `commits` | `{해시: Commit}` | 커밋 저장소. 해시로 평균 O(1) 조회 |
| `branches` | `{브랜치 이름: 끝 커밋 해시 \| None}` | 브랜치마다 끝 커밋 하나만 기억한다. 커밋 전이면 `None` |
| `head` | 현재 브랜치 **이름** | `COMMIT` 이 어느 브랜치를 밀지 정한다. `SWITCH` 만 바꾼다 |
| `author` | 현재 사용자 | 새 커밋의 작성자. `INIT` 이 정한다 |
| `index` | `InvertedIndex` | 검색 색인. 커밋과 함께 움직인다 |

`head` 에 해시가 아니라 이름을 담는 이유: 해시를 담으면 지금 어느 브랜치에 있는지를 해시로 거꾸로 찾아야 하는데,
두 브랜치가 같은 커밋을 가리키면 어느 쪽인지 정할 수 없다.

### 커밋 그래프는 왜 DAG 인가

- **방향**: 자식이 `parents` 로 부모를 가리킨다.
- **사이클이 없다**: `COMMIT` 은 늘 이미 저장된 커밋(`branches[head]`)만 부모로 삼고,
  `Commit` 은 `frozen` 이라 나중에 부모를 바꿀 수 없다. 과거 커밋이 미래 커밋을 가리킬 길이 없다.
- **사이클이 생기면**: "부모가 먼저" 를 만족하는 순서 자체가 없어서 `LOG` 가 성립하지 않는다.
  `topological_order` 는 후보가 하나도 없어 `ValueError` 를 낸다. 조상 탐색도 본 것을 검사하지 않으면 끝없이 돈다.

### 해시 — 빠른 조회와 중복 방지

```python
def _new_hash(self, message, timestamp, parents) -> str:
    while True:
        material = message + str(timestamp) + ",".join(parents) + str(self._counter)
        candidate = hashlib.sha256(material.encode()).hexdigest()[:HASH_LENGTH]   # 앞 6자리
        if candidate not in self.commits:
            return candidate
        self._counter += 1
```

- `commits` 가 dict 라서 `해시 in commits` 와 `commits[해시]` 가 평균 O(1) 이다.
  list 였다면 한 번에 O(n), 커밋 n개를 만드는 동안 중복 검사만으로 O(n²) 이 된다.
- 앞 6자리(16⁶ = 16,777,216가지)만 쓰므로 겹칠 수 있다. 이미 있으면 `_counter` 를 올려 재료를 바꾸고 다시 만든다.
  그래서 돌려주는 해시는 세션 안에서 늘 유일하다. 이 재시도 경로는 드물게만 밟히므로
  `test_절단_충돌이_나면_다른_해시로_다시_만든다` 가 충돌을 직접 심어 확인한다.
- `_new_hash` 는 해시를 돌려주기만 하고, 저장은 `commit()` 이 한다.

### 역색인 — 언제, 어떻게 갱신하나

```python
# Repository.commit()
self.commits[commit_hash] = commit       # ① 저장
self.branches[self.head] = commit_hash   # ② 브랜치 이동
self.index.add(commit)                   # ③ 바로 색인 갱신

# InvertedIndex.add()
for token in tokenize_message(commit.message):          # split + lower, set 이라 중복 없음
    self.by_keyword.setdefault(token, []).append(commit.hash)
self.by_author.setdefault(commit.author.lower(), []).append(commit.hash)
```

- 두 색인: `by_keyword` `{"login": ["ef3c06", "a25dab"], …}`, `by_author` `{"alice": […]}`. 키는 소문자다.
- 커밋을 저장한 직후 같은 `commit()` 안에서 갱신한다. `INIT` 은 `index.clear()` 로 비운다.
  커밋은 지워지지 않으므로 추가만 있다.
- 저장과 색인이 어긋나면 에러 없이 검색 결과만 틀린다. 그래서 순회 검색을 지우지 않고 남겨 두고,
  `EquivalenceTest` · `test_저장소_전체가_순회와_일치한다` 가 두 방식의 결과가 같은지 확인한다.

## 알고리즘

### `LOG` — 위상 정렬

```python
def topological_order(commits):
    remaining = dict(commits)                  # 입력은 건드리지 않는다
    order = []
    while remaining:
        candidates = []
        for commit in remaining.values():
            if not commit.parents:
                candidates.append(commit)
            else:
                has_remaining_parent = False
                for parent in commit.parents:
                    if parent in remaining:
                        has_remaining_parent = True
                        break
                if not has_remaining_parent:
                    candidates.append(commit)
        chosen = min(candidates, key=_hash_of)
        order.append(chosen)
        del remaining[chosen.hash]
    return order
```

- 매 바퀴 "부모가 없거나, 부모가 전부 이미 나간" 커밋을 후보로 모으고 그중 해시가 가장 작은 것을 내보낸다.
- 동률 규칙을 해시로 정해 두어 같은 입력이면 늘 같은 순서가 나온다. `Commit` 끼리는 크기를 비교할 수 없어서
  `key=_hash_of` 로 해시를 비교한다.
- 부모 해시가 입력에 없으면 이미 나간 것으로 본다. `ANCESTORS` · `SEARCH` 결과처럼 커밋 일부만 넘겨도 동작한다.
- 테스트는 순서를 통째로 박지 않고 "모든 부모가 자식보다 앞" 이라는 성질을 검사한다.
  커밋을 자식부터 나열해 timestamp 가 위상 순서와 거꾸로인 경우도 넣어, "시각 순 정렬" 로는 통과하지 못하게 했다.
- 바퀴 n번 × 바퀴마다 남은 커밋 전체 훑기 = **O(n²)**. 아래 "규모" 절 참고.

### `ANCESTORS` — 부모 쪽 BFS

```python
def ancestors(commits, start):
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
```

- 조상은 부모, 부모의 부모…처럼 **위로만** 가는 말이라 `.parents` 만 따라간다. 자식과 형제는 조상이 아니다.
- 이미 처리했거나(`visited`) 줄에 서 있는(`to_visit`) 커밋은 다시 넣지 않는다.
  머지로 두 길이 같은 조상에서 만나도 한 번만 담는다.
- `start` 자신은 결과에 들어가지 않는다. 조상이 없으면 빈 dict → `No ancestors.`

### `PATH` — 무방향 BFS 와 사전순 최소

```python
def shortest_path(commits, source, target):
    if source == target:
        return [source]
    adjacency = undirected_adjacency(commits)   # {해시: 이웃 set}, 간선을 양쪽에 적는다
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
            return None                        # 핸들러가 "No path" 출력
        current = to_visit.pop(0)
    path = [current]
    while current != source:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path
```

- **무방향인 이유**: 과제가 "커밋-부모 연결을 무방향 간선으로 간주" 하라고 정했다. 방향을 지키면 조상과 자손 사이만
  이어지고, 갈라진 브랜치의 두 끝(위 예시의 `3923ea` 와 `ad1517`)은 서로 닿지 않는다. 무방향이면 공통 조상으로
  올라갔다가 내려와서 잇는다.
- **BFS 라서 최단이다**: 줄 앞에서 꺼내므로(`pop(0)`) 출발점에서 가까운 커밋부터 한 겹씩 본다.
  처음 도착한 경로가 곧 간선 수가 가장 적은 경로다. 뒤에서 꺼내면(`pop()`) 먼 쪽으로 파고들다 먼저 도착해
  더 긴 경로를 돌려줄 수 있다.
- **사전순 최소**: 이웃을 `min` 으로 작은 해시부터 줄에 넣고, 줄 앞에서 꺼내고, 처음 적은 "온 곳"(`came_from`)을
  덮어쓰지 않는다. 해시 길이가 6으로 모두 같으므로 해시 순서가 곧 `a -> b -> …` 문자열의 사전순이다.
- **줄에 선 커밋을 다시 넣지 않는 이유**: 넣으면 `came_from` 이 나중에 발견한 더 먼 곳으로 덮어써진다.
  `test_부모가_둘인_커밋을_지나는_최단_경로` 가 이 경우를 막는다.

  ```
  aa ─ bb ─ cc ─ dd,  aa ─ cc  (cc 의 부모가 aa, bb 둘)
  다시 넣으면  came_from[cc] = bb  →  [aa, bb, cc, dd]  (간선 3)
  지금 코드    came_from[cc] = aa  →  [aa, cc, dd]      (간선 2)
  ```

- **경로가 없으면** 줄이 비는 순간 `None` 을 돌려준다. 빈 list `[]` 가 아니라 `None` 으로 "경로 없음" 을 나타내고,
  핸들러가 `path is None` 으로 그것을 알아본다.

### `LOG --sort-by` — 병합 정렬 (직접 구현)

| 평균 | 최악 | 추가 공간 | 안정성 |
|---|---|---|---|
| O(n log n) | O(n log n) | O(n) | 안정 |

```python
def merge_sort(items, key):
    pairs = [(key(item), item) for item in items]   # ① 포장: key() 를 원소당 한 번
    pairs = _sort_pairs(pairs)                      # ② 정렬
    return [item for _, item in pairs]              # ③ 해체. 원본 목록은 그대로

def _sort_pairs(pairs):
    if len(pairs) <= 1:
        return pairs
    middle = len(pairs) // 2
    return _merge(_sort_pairs(pairs[:middle]), _sort_pairs(pairs[middle:]))
```

- **왜 n log n**: 반씩 나누면 층이 log n 개이고, 층마다 원소 전체를 한 번씩 합친다. 입력 모양과 상관없이 같다.
- **안정성**: `_merge` 가 `left_value <= right_value` 일 때 왼쪽(원래 앞에 있던 것)을 먼저 꺼낸다.
  `<=` 를 `<` 로 바꾸면 같은 병합 정렬이 불안정해지므로, `test_전부_같은_키면_순서가_그대로다` 가 지킨다.
- **안정성을 쓰는 곳**: `LOG --sort-by=author` 는 위상 순서를 입력으로 받는다. 같은 작성자끼리는 부모 → 자식 순서가
  그대로 남으므로 2순위 비교 기준을 따로 만들지 않았다.
- **퀵 정렬이 아닌 이유**: 퀵 정렬은 평균 O(n log n) 이지만 피벗이 치우치면 최악 O(n²) 이다.
  입력이 위상 순서라 이미 거의 정렬돼 있어서 그 최악에 걸리기 쉽다.
- **비교 기준 바꾸기**: `key` 인자 하나로 `date`(`timestamp`)와 `author` 를 갈아끼운다.
- **포장을 하는 이유**: 정렬 중에 `key()` 를 그때그때 부르면 같은 원소의 키를 층마다 다시 계산한다.
  미리 한 번씩 뽑아 두면 정확히 n 번이다.
- `min()` 은 쓴다. 전체 순서를 만들지 않고 최솟값 하나만 O(n) 으로 찾기 때문이다.
  전체 순서가 정말 필요한 곳은 `--sort-by` 하나이고, 거기는 직접 구현한 병합 정렬을 쓴다.

### `SEARCH` — 역색인이 순회보다 빠른 이유

| | 순회 (`scan_by_keyword`) | 역색인 (`find_by_keyword`) |
|---|---|---|
| 묻는 방향 | 커밋마다 "이 키워드 있니?" | 키워드에게 "누가 너를 가졌니?" 한 번 |
| 검색 비용 | O(커밋 수 × 메시지 길이) | dict 조회 평균 O(1) + 결과 복사 O(찾은 수) |
| 커밋 비용 | 없음 | 메시지를 한 번 쪼개 색인에 꽂기 O(메시지 길이) |
| 메모리 | 추가 없음 | 토큰마다 해시 목록 |

`./run.sh bench` (검색 1회 평균, 마이크로초):

| 커밋 수 | 키워드 순회 | 키워드 역색인 | 작성자 순회 | 작성자 역색인 |
|---:|---:|---:|---:|---:|
| 100 | 28.2 | 0.1 | 2.5 | 0.1 |
| 1,000 | 310.1 | 0.3 | 23.7 | 0.3 |
| 10,000 | 2,981.5 | 2.9 | 227.7 | 2.4 |
| 50,000 | 15,615.5 | 19.9 | 1,151.0 | 15.9 |

순회는 커밋이 10배면 약 10배 느려진다. 역색인 쪽도 조금씩 느는데, 이 벤치에서는 `login` 을 가진 커밋이
전체의 일정 비율이라 **결과 목록을 복사하는 비용**이 찾은 수만큼 늘기 때문이다. 결과가 없는 키워드로 재면
1,000개 0.16µs, 10,000개 0.18µs 로 조회 자체는 저장소 크기와 상관이 없다.

비용을 "검색할 때" 에서 "커밋할 때" 로 옮긴 거래다. 읽기가 쓰기보다 훨씬 잦다는 전제에서 이득이다.

## 복잡도

n = 커밋 수, E = 간선 수(부모 연결 수), k = 결과 커밋 수, L = 메시지 길이.

| 명령 | 시간 | 지배하는 곳 |
|---|---|---|
| `INIT` · `BRANCH` · `SWITCH` | O(1) | dict 대입 |
| `COMMIT` | 평균 O(L) | 해시 생성(평균 한 번에 끝남) + 색인 갱신 |
| `LOG` | O(n²) | `topological_order` 가 바퀴마다 전체를 훑는다 |
| `LOG --sort-by` | O(n²) + O(n log n) | 위상 정렬이 지배 |
| `ANCESTORS` | O(n²) 최악 | list 의 `in visited` · `in to_visit`, `pop(0)` |
| `PATH` | O(n + E) + O(n²) 최악 | 인접 목록 만들기 + 위와 같은 list 연산 |
| `SEARCH` | 평균 O(1) + O(k) + O(k²) | 색인 조회 + 복사 + 출력용 위상 정렬 |

### 커밋이 10배가 되면 — 병목과 개선 방향

한 줄로 이어진 커밋 체인으로 잰 값이다.

| 명령 | 작게 | 10배 | 배수 | 원인 | 개선 방향 |
|---|---|---|---|---|---|
| `LOG` | 500개 0.005초 | 5,000개 0.498초 | 약 100배 | 바퀴(n) × 전체 훑기(n) | 들어오는 간선 수를 미리 세고 0이 된 것만 줄에 세우는 Kahn 방식 + 최솟값을 빨리 꺼내는 힙 → O((n + E) log n) |
| `PATH` | 1,000개 0.006초 | 10,000개 0.591초 | 약 100배 | 이웃마다 list `in` (n) | `visited` 를 set 으로, 줄은 `collections.deque` 의 `popleft` → O(n + E) |
| `ANCESTORS` | 1,000개 0.003초 | 10,000개 0.295초 | 약 100배 | 위와 같음 | 위와 같음 |
| `LOG --sort-by` (정렬만) | 10,000개 0.013초 | 100,000개 0.161초 | 약 12배 | n log n | 그대로 둬도 된다 |
| `SEARCH` (결과 없음) | 1,000개 0.16µs | 10,000개 0.18µs | 거의 그대로 | dict 조회 | 그대로 둬도 된다 |

계산법은 "몇 번 도는가 × 한 번에 얼마나 드는가" 다. 둘 다 커밋 수에 비례하면 10 × 10 = 약 100배가 된다.

## 요구사항이 바뀐다면

### `PATH` 를 "부모 방향만" 허용하면

| 마름모 `aa → bb, cc → dd` | 지금 (무방향) | 부모 방향만 |
|---|---|---|
| `PATH dd aa` (자식 → 조상) | `dd -> bb -> aa` | `dd -> bb -> aa` |
| `PATH aa dd` (조상 → 자손) | `aa -> bb -> dd` | `No path` |
| `PATH bb cc` (형제) | `bb -> aa -> cc` | `No path` |

바꿀 곳은 이웃을 가져오는 한 줄이다. `neighbors = adjacency[current]` 를 `neighbors = set(commits[current].parents)` 로
바꾸면 `undirected_adjacency` 가 필요 없어진다. 조상 → 자손 쪽도 찾으려면 출발과 도착을 바꿔 한 번 더 찾고 뒤집는다.
형제 사이는 어느 방향으로도 길이 없다.

### `LOG --sort-by=author` 가 "부모가 먼저" 도 지켜야 한다면

위상 순서를 만든 뒤 작성자로 다시 정렬하면 다른 작성자의 부모보다 자식이 먼저 나올 수 있다.

```
aa(Bob, 뿌리) → bb(Alice), cc(Bob),  bb → dd(Alice)

위상 순서 → 작성자로 정렬    [bb Alice, dd Alice, aa Bob, cc Bob]   bb 가 부모 aa 보다 먼저 ✗
후보를 작성자 우선으로 고름  [aa Bob, bb Alice, dd Alice, cc Bob]   부모 먼저 ✓, 가능한 만큼 작성자끼리
```

정렬을 따로 하지 않고, `topological_order` 가 후보를 고르는 기준을 바꾼다. `min(candidates, key=_hash_of)` 의 key 를
`(작성자, 해시)` 를 돌려주는 함수로 바꾸면, 부모가 다 나간 후보 중에서만 작성자 순으로 고른다.
두 조건이 부딪치면 부모 먼저가 이긴다.

### 해시를 카운터 기반 ↔ 난수 기반으로 바꾸면

| | 카운터 (1, 2, 3 …) | 난수 | 지금 (sha256, 시각 포함) |
|---|---|---|---|
| 재현성 | 같은 명령이면 같은 해시 | 매번 다름 (시드를 고정하면 같음) | 시각 때문에 매번 다름 |
| 테스트 | 해시를 값으로 박아 비교할 수 있다 | 박을 수 없다. 출력에서 꺼내 쓰거나 생성기를 바꿔 끼운다 | 출력에서 꺼내 쓴다 |
| 디버깅 | 만든 순서가 해시에 보인다 | 순서 정보가 없다 | 순서 정보가 없다 |
| 충돌 | 올리기만 하면 없다 | 자릿수가 짧으면 생긴다 → 재시도 필요 | 6자리라 생길 수 있다 → `_counter` 로 재시도 |
| 약점 | 예측할 수 있고, 다른 저장소의 해시와 겹친다 | 버그를 같은 해시로 다시 만들기 어렵다 | 같음 |

재현 가능한 테스트가 필요하면 해시 생성기나 시각을 바깥에서 넣어 줄 수 있게 바꾼다.

## 테스트

```bash
./run.sh test                    # 160개
./run.sh test -k ShortestPath    # 일부만 (unittest 인자를 그대로 넘긴다)
```

| 파일 | 개수 | 다루는 것 |
|---|---:|---|
| `test_parser.py` | 16 | 따옴표 안의 공백 · 대소문자 정규화 · 옵션 분리 · 빈 줄 |
| `test_repository.py` | 26 | INIT · BRANCH · SWITCH · COMMIT 상태 변화, 해시 유일성과 충돌 재시도 |
| `test_graph.py` | 28 | 위상 정렬 성질 · 무방향 인접 목록 · 조상 · 최단 경로와 사전순 · 경로 없음 |
| `test_sorting.py` | 15 | 병합 정렬 결과, 안정성, 원본 보존, 비교 기준 바꾸기 |
| `test_search.py` | 28 | 토큰화 · 순회 · 역색인, 순회와 역색인의 결과 일치 |
| `test_commands.py` | 47 | 명령별 출력 형식과 에러 메시지, INIT 전 거절 |

모든 테스트가 실제 코드를 부른다. mock 이나 스텁은 쓰지 않는다. 그래프 · 정렬 · 검색 테스트는 저장소 없이
`{해시: Commit}` 을 손으로 만들어 넣는다.

## 제약 준수

- 표준 라이브러리만 쓴다 (`hashlib` · `time` · `dataclasses` · `unittest` 등).
- `sorted()` · `list.sort()` 를 프로그램 코드에서 쓰지 않는다. 정렬은 `sorting.merge_sort` 하나다.
- 알고리즘은 함수로 분리했다 (`graph.py` · `sorting.py` · `search.py`).
- 주요 함수에는 docstring 으로 계약(받는 것 · 돌려주는 것), 코드만으로는 안 보이는 결정(동률 규칙, 입력 밖 부모 처리,
  입력을 복사하는지), 경계 입력과 에러를 적었다.

## 브랜치

`main` ← `develop` ← `feature/*`. 기능 단위로 feature 브랜치에서 작업하고 develop 에 `--no-ff` 로 머지한 뒤,
통합이 끝나면 main 에 머지한다.
