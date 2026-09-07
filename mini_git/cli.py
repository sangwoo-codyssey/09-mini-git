"""REPL 루프.

읽고(read) → 파싱하고 실행하고(eval) → 출력하고(print) → 반복(loop).

Phase 0 에서는 실행할 명령이 아직 없으므로, 파싱 결과를 그대로 보여주는
확인용 출력을 낸다. Phase 1 에서 Repository 가 생기면 이 자리에 명령 라우팅이
들어가고 확인용 출력은 사라진다.
"""

import sys

from mini_git.errors import MiniGitError
from mini_git.parser import Command, parse

PROMPT = "mini-git> "
EXIT_WORDS = frozenset({"exit", "quit"})


def describe(command: Command) -> str:
    """파싱 결과를 한 줄로 보여준다 (Phase 0 확인용)."""
    return (
        f"name={command.name!r}  "
        f"args={list(command.args)!r}  "
        f"options={command.options!r}"
    )


def main() -> int:
    """REPL 을 돌린다. 종료 코드를 돌려준다."""
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
            command = parse(line)
        except MiniGitError as exc:
            print(exc, file=sys.stderr)
            continue

        if command is None:   # 빈 줄
            continue

        print(describe(command))
