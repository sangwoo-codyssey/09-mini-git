"""커밋 검색 — 순회 방식과 역색인 방식.

같은 기능을 두 가지로 구현해 나란히 둔다. 역색인만 있으면 CLI 는 돌지만
"왜 빠른가" 를 보일 수가 없기 때문이다 (과제 §3 학습목표 5).

두 방식은 **질문하는 방향**이 다르다.

    순회    커밋마다 묻는다      "너 이 키워드 갖고 있니?"   → 커밋 수만큼 묻는다
    역색인  키워드에게 묻는다    "너를 가진 커밋이 누구니?"   → 한 번 묻는다

키워드 추출 규칙은 과제 §4 가 정한 최소 기준을 따른다 — 메시지를 공백으로
쪼개고(split) 소문자로 정규화(lower)한 토큰이 키워드다. 그래서 `"Add login"`
은 `{"add", "login"}` 두 개가 되고, `SEARCH Login` 도 같은 것을 찾아낸다.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:      # 순환 임포트를 피한다
    # repository 가 InvertedIndex 를 쓰고 여기가 Commit 을 쓰므로 서로를 참조한다.
    # 타입 힌트로만 필요하고, __future__ annotations 덕에 힌트는 문자열로 남아
    # 실행 시점에는 평가되지 않는다. 그래서 실제 임포트는 하지 않아도 된다.
    from mini_git.repository import Commit


def tokenize_message(message: str) -> set[str]:
    """커밋 메시지에서 키워드를 뽑는다.

    공백으로 쪼개고 소문자로 내린다. 집합으로 돌려주는 이유는 중복 때문이다 —
    `"fix fix fix"` 의 키워드는 `{"fix"}` 하나이고, 색인에 같은 해시를 세 번
    넣을 이유가 없다.

    구두점은 떼지 않는다. 과제가 요구하는 최소 기준이 split + lower 이고,
    여기서 더 나가면 순회 방식과 역색인 방식의 "같은 결과" 를 맞추기 위해
    양쪽에 같은 규칙을 심어야 해서 비교가 지저분해진다.

    예)
        "Add login feature"  -> {"add", "login", "feature"}
        "Fix Fix"            -> {"fix"}
        ""                   -> set()

    Args:
        message: 커밋 메시지.

    Returns:
        소문자 키워드 집합.
    """
    return {token.lower() for token in message.split()}


def scan_by_keyword(commits: dict[str, Commit], keyword: str) -> list[str]:
    """순회 방식 — 모든 커밋을 돌며 키워드를 가진 것을 고른다.

    커밋 하나하나에 대해 메시지를 쪼개 보므로 O(커밋 수 × 메시지 길이) 다.
    검색할 때마다 이 일을 처음부터 다시 한다.

    Args:
        commits: `{해시 → Commit}`.
        keyword: 찾을 키워드. 대소문자를 가리지 않는다.

    Returns:
        조건에 맞는 커밋 해시 목록. 순서는 `commits` 의 순회 순서다.
    """
    needle = keyword.lower()
    return [
        commit_hash
        for commit_hash, commit in commits.items()
        if needle in tokenize_message(commit.message)
    ]


def scan_by_author(commits: dict[str, Commit], author: str) -> list[str]:
    """순회 방식 — 모든 커밋을 돌며 작성자가 맞는 것을 고른다.

    작성자는 이름 전체가 하나의 값이라 쪼갤 필요가 없다. 그래도 커밋 수만큼
    비교하는 것은 같다.
    """
    needle = author.lower()
    return [
        commit_hash
        for commit_hash, commit in commits.items()
        if commit.author.lower() == needle
    ]


class InvertedIndex:
    """키워드·작성자에서 커밋 해시로 바로 가는 역색인.

    순회 검색은 "이 커밋이 키워드를 갖고 있나?" 를 커밋마다 묻는다.
    역색인은 질문을 뒤집어 "이 키워드를 가진 커밋이 누구지?" 를 한 번만 묻는다.
    딕셔너리 조회 한 번이면 끝나므로 저장소가 아무리 커져도 조회 비용이 같다.

    공짜는 아니다. 비용을 **검색할 때에서 커밋할 때로 옮긴** 것이다.
    메시지를 쪼개는 일을 검색마다 반복하는 대신 커밋 한 번에 한 번만 한다.
    쓰기보다 읽기가 훨씬 잦다는 전제 위의 거래이고, 실제 검색 엔진이 다 이렇게 한다.

    과제 §4 가 요구하는 최소 2종을 모두 갖는다.

        by_keyword   {"login": ["aa", "bb"], "add": ["aa", "cc"], ...}
        by_author    {"alice": ["aa", "cc"], "bob": ["bb"], ...}

    둘 다 키를 소문자로 눕혀 둔다. 그래야 `SEARCH Login` 과 `SEARCH login` 이
    같은 것을 찾는다 — 순회 버전이 매번 `lower()` 하던 일을 색인이 미리 해 둔 셈이다.

    ⚠️ 이 색인은 `Repository` 의 상태와 반드시 함께 움직여야 한다.
    커밋이 늘면 `add()`, 저장소를 새로 만들면 `clear()` 가 불려야 한다.
    안 불리면 색인이 조용히 어긋나고, 검색 결과가 틀려도 아무 에러가 안 난다.
    그 사고를 막는 것이 `tests/test_search.py` 의 "순회와 같은 결과" 테스트다.
    """

    def __init__(self) -> None:
        self.by_keyword: dict[str, list[str]] = {}
        self.by_author: dict[str, list[str]] = {}

    def clear(self) -> None:
        """색인을 통째로 비운다. `INIT` 이 저장소를 새로 만들 때 부른다."""
        self.by_keyword = {}
        self.by_author = {}

    def add(self, commit: Commit) -> None:
        """커밋 하나를 두 색인 모두에 꽂는다.

        `Repository.commit()` 이 커밋을 만든 직후에 부른다.

        메시지에서 키워드를 뽑는 것은 `tokenize_message()` 가 해 준다
        (공백 split + 소문자). 작성자는 쪼개지 않고 이름 전체가 키 하나다.

        같은 키워드가 이미 있으면 그 목록에 해시를 덧붙이고, 처음이면 목록을
        새로 만든다. 커밋은 나중에 지워지지 않으므로 제거는 생각하지 않아도 된다.

        Args:
            commit: 방금 만들어진 커밋. `hash` / `message` / `author` 를 쓴다.
        """
        # setdefault 는 키가 없으면 빈 목록을 넣고 그것을 돌려준다. get 으로는
        # 안 된다 — 기본값을 돌려주기만 하고 딕셔너리에 넣지 않아서, append 가
        # 버려지는 임시 목록에 붙는다 (에러도 결과도 없는 무동작이 된다).
        for token in tokenize_message(commit.message):
            self.by_keyword.setdefault(token, []).append(commit.hash)

        # 키워드는 tokenize_message 가 이미 소문자로 내려 주지만 작성자는
        # 그 함수를 안 거친다. find_by_author 가 lower() 로 찾으므로 여기서 맞춘다.
        self.by_author.setdefault(commit.author.lower(), []).append(commit.hash)

    def find_by_keyword(self, keyword: str) -> list[str]:
        """키워드를 가진 커밋 해시 목록. 없으면 빈 목록.

        조회 한 번으로 끝난다 — 저장소에 커밋이 몇 개든 비용이 같다.
        내부 목록을 그대로 내주지 않고 사본을 만든다. 부르는 쪽이 결과를
        정렬하거나 잘라내도 색인이 망가지지 않게 하기 위해서다.
        """
        return list(self.by_keyword.get(keyword.lower(), []))

    def find_by_author(self, author: str) -> list[str]:
        """그 작성자의 커밋 해시 목록. 없으면 빈 목록."""
        return list(self.by_author.get(author.lower(), []))
