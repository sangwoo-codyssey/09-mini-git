"""REPL 루프.

읽고(read) → 파싱하고 실행하고(eval) → 출력하고(print) → 반복(loop).

루프가 잡는 것은 `MiniGitError` 계열뿐이다. 사용자 입력 때문에 생긴 오류는
메시지만 찍고 계속 돌지만, 그 밖의 예외는 우리 쪽 버그이므로 그대로 터지게 둔다.
조용히 삼키면 저장소가 반쯤 망가진 채로 계속 도는 편이 더 나쁘다.
"""

import sys

from mini_git.commands import execute
from mini_git.errors import MiniGitError
from mini_git.parser import parse
from mini_git.repository import Repository

PROMPT = "mini-git> "
EXIT_WORDS = frozenset({"exit", "quit"})


def run_line(repo: Repository, line: str) -> str | None:
    """한 줄을 파싱해 실행한다. 출력할 것이 없으면 None.

    빈 줄에는 아무 일도 일어나지 않는다 (오류가 아니라 "실행할 것이 없음").

    Raises:
        MiniGitError: 파싱 또는 실행이 실패했을 때.
    """
    command = parse(line)
    if command is None:
        return None
    return execute(repo, command)


def main() -> int:
    """REPL 을 돌린다. 종료 코드를 돌려준다."""
    repo = Repository()

    while True:
        try:
            line = input(PROMPT)
        except EOFError:      # Ctrl-D
            print()
            return 0
        except KeyboardInterrupt:  # Ctrl-C 는 현재 줄만 버리고 계속
            print()
            continue

        if line.strip().lower() in EXIT_WORDS:
            return 0

        try:
            output = run_line(repo, line)
        except MiniGitError as exc:
            print(exc, file=sys.stderr)
            continue

        if output is not None:
            print(output)
