#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${PYTHON:-python3}"

# 표준 라이브러리만 쓰므로 로컬 실행이 전부다. Docker 는 쓰지 않는다.

check_python() {
  if ! command -v "$PYTHON" &>/dev/null; then
    echo "오류: '$PYTHON' 을 찾을 수 없습니다. PYTHON 환경변수로 지정하세요." >&2
    exit 1
  fi
  "$PYTHON" - <<'PY'
import sys
if sys.version_info < (3, 10):
    sys.exit("오류: Python 3.10 이상이 필요합니다 (현재 %d.%d)" % sys.version_info[:2])
PY
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
  *)
    echo "사용법: $0 {run|test}"
    echo ""
    echo "  $0 run                # mini-git REPL 실행 (기본값)"
    echo "  $0 test               # unittest 회귀 테스트"
    echo "  $0 test -k tokenize   # 추가 인자는 unittest 로 그대로 전달"
    echo ""
    echo "환경변수:"
    echo "  PYTHON   사용할 파이썬 실행 파일 (기본: python3)"
    exit 1
    ;;
esac
