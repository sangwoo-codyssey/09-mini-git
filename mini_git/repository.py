import hashlib
import time
from dataclasses import dataclass, field

from mini_git.errors import BranchExists, NotInitialized, UnknownBranch
from mini_git.search import InvertedIndex

DEFAULT_BRANCH = "main"
HASH_LENGTH = 6


@dataclass(frozen=True)
class Commit:

    hash: str
    message: str
    author: str
    timestamp: float
    parents: tuple[str, ...]

    @property
    def formatted_time(self) -> str:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.timestamp))


@dataclass
class Repository:

    commits: dict[str, Commit] = field(default_factory=dict)
    branches: dict[str, str | None] = field(default_factory=dict)
    head: str | None = None
    author: str | None = None
    index: InvertedIndex = field(default_factory=InvertedIndex)
    _counter: int = 0


    @property
    def initialized(self) -> bool:
        return self.head is not None

    def require_initialized(self) -> None:
        if not self.initialized:
            raise NotInitialized()

    @property
    def head_commit(self) -> str | None:
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
        self.index.clear()  # 역색인 — 학습목표 5 에서 다룬다
        self._counter = 0  # 해시 카운터 — 해시 단계에서 다룬다

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
        self.index.add(commit)  # 역색인 — 학습목표 5 에서 다룬다
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
