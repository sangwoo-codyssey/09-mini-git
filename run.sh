#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 표준 라이브러리만 쓰므로 로컬 실행이 전부다. Docker 는 쓰지 않는다.
#
# 이 미션은 Python 3.10 이상을 요구하는데 macOS 기본 python3 는 3.9 다.
# PYTHON 환경변수가 있으면 그걸 존중하고, 없으면 3.10+ 인터프리터를 직접 찾는다.

version_ok() {
  command -v "$1" &>/dev/null && \
    "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' &>/dev/null
}

resolve_python() {
  if [ -n "$PYTHON" ]; then
    return  # 사용자가 지정했으면 그대로 쓴다 (검사는 check_python 이 한다)
  fi
  for candidate in python3 python3.14 python3.13 python3.12 python3.11 python3.10; do
    if version_ok "$candidate"; then
      PYTHON="$candidate"
      return
    fi
  done
  PYTHON=python3  # 못 찾으면 check_python 이 이유를 설명하고 죽는다
}

check_python() {
  resolve_python
  if ! command -v "$PYTHON" &>/dev/null; then
    echo "오류: '$PYTHON' 을 찾을 수 없습니다. PYTHON 환경변수로 지정하세요." >&2
    exit 1
  fi
  if ! version_ok "$PYTHON"; then
    echo "오류: Python 3.10 이상이 필요합니다 (현재 $("$PYTHON" -V 2>&1))." >&2
    echo "      3.10+ 인터프리터를 PYTHON 환경변수로 지정하세요. 예: PYTHON=python3.14 ./run.sh" >&2
    exit 1
  fi
}

case "${1:-run}" in
  run)
    check_python
    cd "$SCRIPT_DIR"
    exec "$PYTHON" main.py
    ;;
  test)
    check_python
    cd "$SCRIPT_DIR"
    shift
    exec "$PYTHON" -m unittest discover "$@"
    ;;
  bench)
    check_python
    cd "$SCRIPT_DIR"
    exec "$PYTHON" benchmark.py
    ;;
  *)
    echo "사용법: $0 {run|test|bench}"
    echo ""
    echo "  $0 run                # mini-git REPL 실행 (기본값)"
    echo "  $0 test               # unittest 회귀 테스트"
    echo "  $0 test -k tokenize   # 추가 인자는 unittest 로 그대로 전달"
    echo "  $0 bench              # 순회 검색 vs 역색인 성능 비교"
    echo ""
    echo "환경변수:"
    echo "  PYTHON   사용할 파이썬 실행 파일 (기본: python3)"
    exit 1
    ;;
esac
