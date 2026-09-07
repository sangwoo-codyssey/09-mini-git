"""명령 이름 → 핸들러 라우팅, 그리고 출력 문구.

층이 셋이다. 파서는 "무엇을 요청했나" 만 알고(저장소를 모른다), 여기 핸들러가
"인자 개수가 맞나" 를 보고, `Repository` 가 "그 브랜치가 있나" 를 판단한다.
이 경계 덕에 파서 테스트는 저장소 없이, 저장소 테스트는 문자열 파싱 없이 돈다.

핸들러는 출력을 직접 print 하지 않고 문자열로 돌려준다. 그래야 테스트가
표준출력을 가로채지 않고 반환값만 비교하면 된다.
"""

from typing import Callable

from mini_git.errors import InvalidArgs, UnknownCommand
from mini_git.graph import topological_order
from mini_git.parser import Command
from mini_git.repository import Commit, Repository

Handler = Callable[[Repository, Command], str]


def _one_arg(command: Command, what: str) -> str:
    """위치 인자가 정확히 하나인지 확인하고 그것을 돌려준다.

    공백이 든 값은 따옴표로 감싸야 한다는 것을 여기서 알려준다. 따옴표 없이
    `INIT Alice Kim` 을 치면 인자가 둘이 되는데, 조용히 첫 번째만 쓰면 사용자는
    이름이 잘린 것을 눈치채지 못한다.
    """
    if len(command.args) != 1:
        raise InvalidArgs(
            f"{command.name.upper()} takes exactly one argument (<{what}>); "
            "quote it if it contains spaces"
        )
    return command.args[0]


def handle_init(repo: Repository, command: Command) -> str:
    """INIT <user_name> — 저장소를 초기화한다."""
    author = _one_arg(command, "user_name")
    repo.init(author)
    return (
        "Initialized repository.\n"
        f"Current branch: {repo.head}\n"
        f"Current user: {repo.author}"
    )


def handle_branch(repo: Repository, command: Command) -> str:
    """BRANCH <branch_name> — 현재 커밋을 가리키는 새 브랜치를 만든다."""
    name = _one_arg(command, "branch_name")
    repo.create_branch(name)
    return f"Created branch: {name}"


def handle_switch(repo: Repository, command: Command) -> str:
    """SWITCH <branch_name> — HEAD 를 옮긴다."""
    name = _one_arg(command, "branch_name")
    repo.switch(name)
    return f"Switched to branch: {name}"


def handle_commit(repo: Repository, command: Command) -> str:
    """COMMIT <message> — 현재 HEAD 를 부모로 하는 커밋을 만든다."""
    message = _one_arg(command, "message")
    commit = repo.commit(message)
    return f"[{repo.head} {commit.hash}] {commit.message}"


def _branch_tips(repo: Repository) -> dict[str, list[str]]:
    """`{커밋 해시 → 그 커밋을 가리키는 브랜치 이름들}`.

    `branches` 는 이름 → 해시 방향이라 출력에 `[main]` 을 붙이려면 뒤집어야 한다.
    아직 커밋이 없는 브랜치는 None 을 가리키므로 걸러낸다 (git 의 unborn branch).
    """
    tips: dict[str, list[str]] = {}
    for name, commit_hash in repo.branches.items():
        if commit_hash is not None:
            tips.setdefault(commit_hash, []).append(name)
    return tips


def _format_commit(commit: Commit, branches: list[str]) -> str:
    """커밋 하나를 두 줄로 그린다 (과제 §8 예시 형식).

        commit a1b2c3 (Alice, 2024-01-15 09:00:00) [main]
        Initial commit
    """
    label = f" [{', '.join(branches)}]" if branches else ""
    return (
        f"commit {commit.hash} ({commit.author}, {commit.formatted_time}){label}\n"
        f"{commit.message}"
    )


def handle_log(repo: Repository, command: Command) -> str:
    """LOG — 부모가 자식보다 먼저 오도록 커밋을 출력한다.

    "최신순" 이 아니다. 과제 §4 가 위상 정렬 성격의 출력을 요구한다.
    """
    repo.require_initialized()
    if command.args or command.options:
        raise InvalidArgs("LOG takes no arguments")

    order = topological_order(repo.commits)
    if not order:
        return "No commits yet."

    tips = _branch_tips(repo)
    return "\n".join(_format_commit(c, tips.get(c.hash, [])) for c in order)


HANDLERS: dict[str, Handler] = {
    "init": handle_init,
    "branch": handle_branch,
    "switch": handle_switch,
    "commit": handle_commit,
    "log": handle_log,
}


def execute(repo: Repository, command: Command) -> str:
    """명령 하나를 실행하고 출력할 문자열을 돌려준다.

    Raises:
        UnknownCommand: 등록되지 않은 명령 이름일 때.
        MiniGitError: 핸들러나 저장소가 던지는 나머지 오류들.
    """
    handler = HANDLERS.get(command.name)
    if handler is None:
        raise UnknownCommand(command.name)
    return handler(repo, command)
