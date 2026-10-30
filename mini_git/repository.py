"""커밋 그래프의 저장소.

커밋(`Commit`)과, 커밋 · 브랜치 · HEAD · 현재 사용자 · 역색인을 한데 묶은 상태(`Repository`)를 둔다.
INIT · BRANCH · SWITCH · COMMIT 이 상태를 바꾸는 규칙은 `Repository` 의 메서드다.
그래프를 읽는 알고리즘(위상 정렬, BFS)은 graph.py 가 맡고, 여기서는 상태만 다룬다.
"""

import hashlib
import time
from dataclasses import dataclass, field

from mini_git.errors import BranchExists, NotInitialized, UnknownBranch
from mini_git.search import InvertedIndex

DEFAULT_BRANCH = "main"
HASH_LENGTH = 6


@dataclass(frozen=True)
class Commit:
    """커밋 하나. 만든 뒤에는 바꿀 수 없다(frozen).

    parents 는 부모 커밋 해시의 튜플이다. 첫 커밋이면 비어 있다.
    부모는 늘 이미 저장된 커밋이고 나중에 바꿀 수도 없으므로, 커밋 그래프에는 사이클이 생기지 않는다(DAG).
    """

    hash: str
    message: str
    author: str
    timestamp: float
    parents: tuple[str, ...]

    @property
    def formatted_time(self) -> str:
        """timestamp 를 `YYYY-MM-DD HH:MM:SS` 형식의 지역 시각 문자열로 돌려준다. LOG 출력에 쓴다."""
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.timestamp))


@dataclass
class Repository:
    """저장소 상태와, 그 상태를 바꾸는 규칙.

    commits 는 해시 → Commit 이라 해시로 바로 찾는다.
    branches 는 브랜치 이름 → 그 브랜치의 끝 커밋 해시이고, 아직 커밋이 없으면 None 이다.
    head 는 지금 브랜치의 이름이다(해시가 아니다). INIT 전에는 None 이다.
    index 는 키워드 · 작성자 역색인이고, commit 이 커밋을 저장할 때 같이 갱신한다.
    _counter 는 해시가 겹칠 때 재료를 바꾸는 데 쓴다.
    """

    commits: dict[str, Commit] = field(default_factory=dict)
    branches: dict[str, str | None] = field(default_factory=dict)
    head: str | None = None
    author: str | None = None
    index: InvertedIndex = field(default_factory=InvertedIndex)
    _counter: int = 0


    @property
    def initialized(self) -> bool:
        """INIT 을 했으면 True. head 가 정해졌는지로 판단한다."""
        return self.head is not None

    def require_initialized(self) -> None:
        """INIT 전이면 NotInitialized 를 낸다. 상태를 읽거나 바꾸는 명령이 맨 앞에서 부른다."""
        if not self.initialized:
            raise NotInitialized()

    @property
    def head_commit(self) -> str | None:
        """현재 브랜치의 끝 커밋 해시. 아직 커밋이 없으면 None, INIT 전이면 NotInitialized."""
        self.require_initialized()
        return self.branches[self.head]


    def init(self, author: str) -> None:
        """저장소를 초기화하고 작성자를 author 로 지정한다.

        커밋이 없는 기본 브랜치(main) 하나를 만들고 HEAD 를 그 위에 둔다.
        이미 쓰던 저장소에서 다시 부르면 처음 상태로 되돌린다.
        """
        self.commits = {}
        self.branches = {DEFAULT_BRANCH: None}
        self.head = DEFAULT_BRANCH
        self.author = author
        self.index.clear()
        self._counter = 0

    def create_branch(self, name: str) -> None:
        """현재 브랜치가 가리키는 커밋에서 새 브랜치 name 을 만든다.

        HEAD 는 옮기지 않는다 — 옮기는 것은 switch 다.
        아직 커밋이 없으면 새 브랜치도 아무 커밋을 가리키지 않는다.
        init 전이면 NotInitialized, 이미 있는 이름이면 BranchExists 를 낸다.
        """
        self.require_initialized()
        if name in self.branches:
            raise BranchExists(name)
        self.branches[name] = self.branches[self.head]

    def switch(self, name: str) -> None:
        """HEAD 를 브랜치 name 으로 옮긴다.

        branches 와 commits 는 건드리지 않는다. 이후의 commit 이 이 브랜치를 앞으로 민다.
        init 전이면 NotInitialized, 없는 브랜치면 UnknownBranch 를 낸다.
        """
        self.require_initialized()
        if name not in self.branches:
            raise UnknownBranch(name)
        self.head = name

    def commit(self, message: str) -> Commit:
        """현재 브랜치 위에 새 커밋을 만들어 돌려준다.

        부모는 현재 브랜치가 가리키던 커밋이다. 첫 커밋이면 부모가 없다.
        새 커밋을 commits 에 해시를 키로 저장하고, 현재 브랜치를 새 커밋으로 옮긴다.
        같은 자리에서 역색인(index)에도 넣어, 검색이 바로 새 커밋을 찾는다.
        HEAD 는 그대로다. init 전이면 NotInitialized 를 낸다.
        """
        self.require_initialized()
        timestamp = time.time()
        head_hash = self.branches.get(self.head)
        if head_hash is None:
            parents = ()
        else:
            parents = (head_hash,)
        commit_hash = self._new_hash(message, timestamp, parents)
        commit = Commit(commit_hash, message, self.author, timestamp, parents)
        self.commits[commit_hash] = commit
        self.branches[self.head] = commit_hash
        self.index.add(commit)
        return commit


    def _new_hash(
        self, message: str, timestamp: float, parents: tuple[str, ...]
    ) -> str:
        """커밋 해시를 만든다. 아직 commits 에 없는 값만 돌려준다.

        message·timestamp·parents·_counter 를 이은 문자열의 sha256 에서
        앞 HASH_LENGTH 자리를 쓴다. 앞자리만 쓰므로 기존 해시와 겹칠 수 있고,
        겹치면 _counter 를 올려 재료를 바꾼 뒤 다시 만든다.
        저장은 하지 않는다 — commit 이 한다.
        """
        while True:
            material = message + str(timestamp) + ",".join(parents) + str(self._counter)
            candidate = hashlib.sha256(material.encode()).hexdigest()[:HASH_LENGTH]
            if candidate not in self.commits:
                return candidate
            self._counter += 1
