"""명령 이름 → 핸들러 라우팅, 그리고 출력 문구.

층이 셋이다. 파서는 "무엇을 요청했나" 만 알고(저장소를 모른다), 여기 핸들러가
"인자 개수가 맞나" 를 보고, `Repository` 가 "그 브랜치가 있나" 를 판단한다.
이 경계 덕에 파서 테스트는 저장소 없이, 저장소 테스트는 문자열 파싱 없이 돈다.

핸들러는 출력을 직접 print 하지 않고 문자열로 돌려준다. 그래야 테스트가
표준출력을 가로채지 않고 반환값만 비교하면 된다.
"""

from typing import Callable

from mini_git.errors import InvalidArgs, UnknownCommand, UnknownCommit
from mini_git.graph import ancestors, shortest_path, topological_order
from mini_git.parser import Command
from mini_git.repository import Commit, Repository
from mini_git.sorting import merge_sort

Handler = Callable[[Repository, Command], str]


def _one_arg(command: Command, what: str) -> str:
    """위치 인자가 정확히 하나인지 확인하고 그것을 돌려준다.

    공백이 든 값은 따옴표로 감싸야 한다는 것을 여기서 알려준다. 따옴표 없이
    `INIT Alice Kim` 을 치면 인자가 둘이 되는데, 조용히 첫 번째만 쓰면 사용자는
    이름이 잘린 것을 눈치채지 못한다.
    """
    if len(command.args) != 1 or command.options:
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


SORT_KEYS: dict[str, Callable[[Commit], object]] = {
    "date": lambda commit: commit.timestamp,
    "author": lambda commit: commit.author,
}


def handle_log(repo: Repository, command: Command) -> str:
    """LOG [--sort-by=date|author] — 커밋 목록을 출력한다.

    옵션이 없으면 위상 순서다 — "최신순" 이 아니라 **부모가 자식보다 먼저**.
    과제 §4 가 그렇게 요구한다.

    `--sort-by` 는 그 위상 순서를 입력으로 받아 **안정 정렬**을 한 번 더 얹는다.
    그래서 키가 같은 커밋들(같은 작성자, 같은 초)은 위상 순서를 그대로 유지한다.
    2순위 비교 기준을 따로 만들지 않아도 출력이 흔들리지 않는 이유다.
    """
    repo.require_initialized()
    if command.args:
        raise InvalidArgs("LOG takes no positional arguments")

    unknown = [name for name in command.options if name != "sort-by"]
    if unknown:
        raise InvalidArgs(f"LOG has no such option: --{unknown[0]}")

    sort_by = command.options.get("sort-by")
    if sort_by is not None and sort_by not in SORT_KEYS:
        allowed = "|".join(SORT_KEYS)
        raise InvalidArgs(f"LOG --sort-by must be one of: {allowed}")

    order = topological_order(repo.commits)
    if not order:
        return "No commits yet."

    if sort_by is not None:
        order = merge_sort(order, key=SORT_KEYS[sort_by])

    tips = _branch_tips(repo)
    return "\n".join(_format_commit(c, tips.get(c.hash, [])) for c in order)


def _require_commit(repo: Repository, commit_hash: str) -> str:
    """그 해시의 커밋이 실제로 있는지 확인한다. 없으면 UnknownCommit."""
    if commit_hash not in repo.commits:
        raise UnknownCommit(commit_hash)
    return commit_hash


def _format_many(repo: Repository, commits: dict[str, Commit]) -> str:
    """여러 커밋을 위상 순서로 그린다 (LOG 와 같은 형식)."""
    tips = _branch_tips(repo)
    return "\n".join(
        _format_commit(c, tips.get(c.hash, [])) for c in topological_order(commits)
    )


def handle_ancestors(repo: Repository, command: Command) -> str:
    """ANCESTORS <commit_hash> — 도달 가능한 모든 조상을 출력한다.

    자기 자신은 조상이 아니므로 빼고, 부모 방향으로만 올라간다.
    """
    repo.require_initialized()
    commit_hash = _require_commit(repo, _one_arg(command, "commit_hash"))

    found = ancestors(repo.commits, commit_hash)
    if not found:
        return "No ancestors."
    return _format_many(repo, found)


def handle_path(repo: Repository, command: Command) -> str:
    """PATH <commit1> <commit2> — 무방향 최단 경로를 출력한다.

    경로가 없으면 과제가 지정한 문구 그대로 `No path` 를 낸다.
    """
    repo.require_initialized()
    if len(command.args) != 2 or command.options:
        raise InvalidArgs("PATH takes exactly two arguments (<commit1> <commit2>)")

    source = _require_commit(repo, command.args[0])
    target = _require_commit(repo, command.args[1])

    path = shortest_path(repo.commits, source, target)
    if path is None:
        return "No path"
    return "Path: " + " -> ".join(path)


def handle_search(repo: Repository, command: Command) -> str:
    """SEARCH <keyword> | SEARCH --author=<name> — 커밋을 찾는다.

    둘 중 정확히 하나여야 한다. 둘 다 주면 무엇을 원하는지 모호하고, 조용히
    한쪽만 쓰면 사용자가 나머지가 무시된 것을 눈치채지 못한다.

    찾은 커밋은 위상 순서로 출력한다 — LOG 와 같은 규칙이라 부모가 자식보다
    먼저 나온다. 검색 결과에도 이 순서가 유지되는 편이 읽기에 낫다.

    후보를 가져오는 것은 역색인이다(과제 §4 "모든 커밋을 순회하지 않고").
    순회 버전은 `search.py` 에 그대로 남아 있고, 테스트가 둘의 결과를 맞춰 본다.
    """
    repo.require_initialized()

    unknown = [name for name in command.options if name != "author"]
    if unknown:
        raise InvalidArgs(f"SEARCH has no such option: --{unknown[0]}")

    author = command.options.get("author")
    if author is not None and command.args:
        raise InvalidArgs("SEARCH takes either a keyword or --author, not both")

    if author is not None:
        found = repo.index.find_by_author(author)
        subject = f"--author={author}"
    else:
        if len(command.args) != 1:
            raise InvalidArgs(
                "SEARCH takes exactly one keyword (or --author=<name>); "
                "quote it if it contains spaces"
            )
        found = repo.index.find_by_keyword(command.args[0])
        subject = command.args[0]

    if not found:
        return f"No commits found for {subject}."

    noun = "commit" if len(found) == 1 else "commits"
    body = _format_many(repo, {h: repo.commits[h] for h in found})
    return f"Found {len(found)} {noun}:\n{body}"


HANDLERS: dict[str, Handler] = {
    "init": handle_init,
    "branch": handle_branch,
    "switch": handle_switch,
    "commit": handle_commit,
    "log": handle_log,
    "ancestors": handle_ancestors,
    "path": handle_path,
    "search": handle_search,
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
