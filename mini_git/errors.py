"""사용자 입력으로 생기는 오류들.

REPL 은 이 계열의 예외를 잡아 메시지만 출력하고 계속 돈다. 프로그램이 죽는 것은
버그일 때뿐이므로, 여기 없는 예외가 올라오면 그대로 터지게 둔다.

메시지 문구는 과제 §4 의 표준을 따른다.
"""


class MiniGitError(Exception):
    """REPL 이 잡아서 메시지만 출력할 오류의 최상위 타입."""


class InvalidArgs(MiniGitError):
    """인자 개수나 형식이 명령의 요구와 맞지 않는다."""

    def __init__(self, detail: str = "") -> None:
        super().__init__(f"Invalid args: {detail}" if detail else "Invalid args")


class ParseError(MiniGitError):
    """한 줄을 토큰으로 쪼갤 수 없다. 지금은 따옴표 미닫힘이 유일한 경우다."""

    def __init__(self, quote_char: str) -> None:
        super().__init__(f"Unclosed quote: {quote_char}")


class UnknownCommand(MiniGitError):
    """명령 이름을 모른다."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Unknown command: {name}")


class UnknownBranch(MiniGitError):
    """그런 이름의 브랜치가 없다."""

    def __init__(self, name: str) -> None:
        super().__init__(f"Unknown branch: {name}")


class UnknownCommit(MiniGitError):
    """그런 해시의 커밋이 없다."""

    def __init__(self, commit_hash: str) -> None:
        super().__init__(f"Unknown commit: {commit_hash}")
