"""커밋 DAG 와 그 위에서 도는 저장소 상태.

상태는 네 칸뿐이고, 명령마다 건드리는 칸이 다르다.

    Repository                              Commit
    ├── commits   { 해시 → Commit }          ├── hash
    ├── branches  { 이름 → 커밋 해시|None }   ├── message
    ├── head      "main"  (브랜치 이름!)      ├── author
    └── author    "Alice"                    ├── timestamp
                                             └── parents  (튜플, 머지면 2개)

`head` 가 커밋 해시가 아니라 **브랜치 이름**을 담는 것이 이 구조의 중심이다.
실제 git 의 `.git/HEAD` 가 `ref: refs/heads/main` 을 담는 것과 같다. 이 간접 참조
덕분에 `COMMIT` 은 `head` 를 건드릴 필요 없이 `branches[head]` 한 칸만 밀면 되고,
`SWITCH` 는 반대로 `head` 한 칸만 바꾸면 된다.

부모가 자식보다 항상 먼저 존재하므로 이 그래프에는 순환이 생길 수 없다 — DAG 다.
"""

import hashlib
import time
from dataclasses import dataclass, field

from mini_git.errors import BranchExists, NotInitialized, UnknownBranch

DEFAULT_BRANCH = "main"
HASH_LENGTH = 6


@dataclass(frozen=True)
class Commit:
    """커밋 하나. 한 번 만들어지면 절대 바뀌지 않는다.

    불변으로 두는 이유는 해시 때문이다. 해시는 만들 때의 내용으로 결정되는데
    나중에 필드를 고칠 수 있으면 해시가 내용과 어긋난다. frozen 이 그 사고를 막는다.

    Attributes:
        hash: 세션 내 유일한 짧은 식별자. 예) "a1b2c3"
        message: 커밋 메시지.
        author: 작성자 이름.
        timestamp: 생성 시각 (epoch 초, float).
        parents: 부모 커밋 해시들. 최초 커밋은 (), 머지 커밋은 2개.
    """

    hash: str
    message: str
    author: str
    timestamp: float
    parents: tuple[str, ...]

    @property
    def formatted_time(self) -> str:
        """`2024-01-15 09:00:00` 형태의 사람이 읽는 시각."""
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.timestamp))


@dataclass
class Repository:
    """메모리 상의 저장소. 영속성은 과제 범위 밖이라 프로세스와 함께 사라진다."""

    commits: dict[str, Commit] = field(default_factory=dict)
    branches: dict[str, str | None] = field(default_factory=dict)
    head: str | None = None
    author: str | None = None
    _counter: int = 0

    # ---- 상태 확인 -------------------------------------------------------

    @property
    def initialized(self) -> bool:
        """INIT 이 끝났는가. head 가 채워졌는지로 판단한다."""
        return self.head is not None

    def require_initialized(self) -> None:
        """INIT 이 선행돼야 하는 명령들이 맨 앞에서 부른다."""
        if not self.initialized:
            raise NotInitialized()

    @property
    def head_commit(self) -> str | None:
        """HEAD 가 가리키는 커밋 해시. 커밋이 하나도 없으면 None."""
        self.require_initialized()
        return self.branches[self.head]

    # ---- 명령 -----------------------------------------------------------

    def init(self, author: str) -> None:
        """저장소를 초기화한다.

        같은 세션에서 다시 부르면 기존 상태를 전부 버린다 — 새 저장소다.
        `main` 브랜치는 만들어지되 아직 어떤 커밋도 가리키지 않으므로 None 이다.
        "브랜치는 있는데 커밋이 없다" 는 상태를 None 으로 표현하는 셈인데,
        실제 git 의 unborn branch 와 같다.
        """
        self.commits = {}
        self.branches = {DEFAULT_BRANCH: None}
        self.head = DEFAULT_BRANCH
        self.author = author
        self._counter = 0

    def create_branch(self, name: str) -> None:
        """현재 HEAD 가 가리키는 커밋을 함께 가리키는 새 브랜치를 만든다.

        **`head` 는 옮기지 않는다.** 만들기만 하고 그대로 머문다.
        옮기는 것은 `switch` 뿐이다 (`git branch f1` 뒤에도 HEAD 가 그대로인 것과 같다).
        """
        self.require_initialized()
        if name in self.branches:
            raise BranchExists(name)
        self.branches[name] = self.branches[self.head]

    def switch(self, name: str) -> None:
        """HEAD 를 지정한 브랜치로 옮긴다. `branches` 는 건드리지 않는다."""
        self.require_initialized()
        if name not in self.branches:
            raise UnknownBranch(name)
        self.head = name

    def commit(self, message: str) -> Commit:
        """현재 HEAD 를 부모로 하는 커밋을 만들고 브랜치를 그 위로 민다.

        네 단계를 모두 밟아야 한다. 마지막 단계를 빠뜨리면 모든 커밋이 같은
        부모를 갖는 납작한 그래프가 되므로, 회귀 테스트로 못박아 뒀다.

            ① head → branches 로 부모 해시를 얻는다
            ② Commit 을 만든다
            ③ commits 에 등록한다
            ④ branches[head] 를 새 해시로 민다   ← 빠뜨리기 쉬운 곳
        """
        self.require_initialized()
        parent = self.branches[self.head]
        parents = () if parent is None else (parent,)

        timestamp = time.time()
        commit = Commit(
            hash=self._new_hash(message, timestamp, parents),
            message=message,
            author=self.author,
            timestamp=timestamp,
            parents=parents,
        )
        self.commits[commit.hash] = commit
        self.branches[self.head] = commit.hash
        return commit

    # ---- 해시 -----------------------------------------------------------

    def _new_hash(
        self, message: str, timestamp: float, parents: tuple[str, ...]
    ) -> str:
        """이 세션에서 아직 쓰이지 않은 커밋 해시를 만들어 돌려준다.

        내용(message/author/timestamp/parents)만으로 해시를 만들면 과제의
        "세션 내 유일" 조건을 못 지킨다. 09 는 파일을 추적하지 않아 재료가 넷뿐이라,
        같은 부모에서 같은 사람이 같은 메시지로 같은 순간에 커밋하면 넷이 전부
        같아지기 때문이다. 그래서 `self._counter` 를 재료에 섞는다 —
        유일성은 카운터가 보장하고, sha256 은 git 스러운 겉모습만 준다.

        `HASH_LENGTH` 로 잘라 쓰므로 절단 충돌은 여전히 가능하다.
        `self.commits` 에 이미 있는지로 확인하고, 있으면 다시 만든다.
        이때 **입력을 바꾸지 않으면 같은 값이 다시 나와 무한 루프가 된다.**

        Returns:
            `self.commits` 에 없는 해시 문자열.
        """
        while True:
            # 구분자 "/" 를 넣어야 ("ab","c") 와 ("a","bc") 가 다른 입력이 된다.
            material = "/".join(
                [
                    str(self._counter),
                    message,
                    str(self.author),
                    str(timestamp),
                    ",".join(parents),
                ]
            )
            self._counter += 1  # 다음 시도의 입력이 반드시 달라지도록 매번 올린다
            candidate = hashlib.sha256(material.encode()).hexdigest()[:HASH_LENGTH]
            if candidate not in self.commits:
                return candidate
