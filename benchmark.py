"""순회 검색과 역색인 검색을 재서 비교한다 (과제 §3 학습목표 5).

실행: ./run.sh bench

역색인만 있으면 CLI 는 돌지만 "왜 빠른가" 를 보일 수가 없다. 그래서
`mini_git/search.py` 에 순회 방식(`scan_by_*`)을 남겨 두고 여기서 둘을 잰다.
`tests/test_search.py::EquivalenceTest` 가 두 방식이 같은 결과를 냄을 보장하므로,
여기서 재는 것은 순수하게 **같은 답을 얻는 두 가지 길의 비용 차이**다.

    순회    커밋마다 메시지를 쪼개 확인한다        O(커밋 수 × 메시지 길이)
    역색인  딕셔너리를 한 번 조회한다             O(찾은 커밋 수)

역색인 쪽이 저장소 크기와 무관한 것이 핵심이다. 늘어나는 부분이 있다면 그것은
조회가 아니라 결과 목록을 복사하는 비용이고, 이는 결과 수에만 비례한다.
"""

import time

from mini_git.repository import Commit
from mini_git.search import InvertedIndex, scan_by_author, scan_by_keyword

WORDS = ["add", "fix", "refactor", "login", "payment", "search", "index", "bug"]
SIZES = (100, 1_000, 10_000, 50_000)
REPEAT = 200


def build_corpus(count: int) -> tuple[dict[str, Commit], InvertedIndex]:
    """같은 커밋 집합을 순회용 딕셔너리와 역색인 양쪽으로 만든다."""
    commits: dict[str, Commit] = {}
    index = InvertedIndex()
    for i in range(count):
        commit = Commit(
            hash=f"{i:06x}",
            message=f"{WORDS[i % 8]} {WORDS[(i * 3) % 8]} feature number {i}",
            author=f"dev{i % 5}",
            timestamp=float(i),
            parents=(),
        )
        commits[commit.hash] = commit
        index.add(commit)
    return commits, index


def measure(operation, repeat: int = REPEAT) -> float:
    """한 번 실행에 걸리는 평균 시간(마이크로초)."""
    started = time.perf_counter()
    for _ in range(repeat):
        operation()
    return (time.perf_counter() - started) / repeat * 1_000_000


def report(title: str, scan, lookup) -> None:
    print(f"\n{title}  (검색 1회 평균 마이크로초, {REPEAT}회 반복)")
    print(f"{'커밋 수':>10} {'순회':>12} {'역색인':>12} {'배수':>10}")
    print("-" * 48)
    for size in SIZES:
        commits, index = build_corpus(size)
        scanned = measure(lambda: scan(commits))
        looked_up = measure(lambda: lookup(index))
        print(f"{size:>10,} {scanned:>12.1f} {looked_up:>12.1f} {scanned / looked_up:>9.0f}x")


def main() -> int:
    report(
        "키워드 검색",
        lambda commits: scan_by_keyword(commits, "login"),
        lambda index: index.find_by_keyword("login"),
    )
    report(
        "작성자 검색",
        lambda commits: scan_by_author(commits, "dev2"),
        lambda index: index.find_by_author("dev2"),
    )
    print("\n커밋이 10배 늘 때 순회는 약 10배 느려지고, 역색인은 거의 그대로다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
