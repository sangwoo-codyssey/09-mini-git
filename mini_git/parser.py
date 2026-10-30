"""입력 한 줄을 실행 가능한 형태로 쪼갠다.

CLI 문법 표준(과제 §4):
  - 명령어는 대소문자를 구분하지 않는다        INIT / init 모두 허용
  - 문자열 인자는 공백을 포함할 수 있고,        COMMIT "Add login feature"
    그럴 때 따옴표로 감싼다
  - 옵션은 --key=value 형식으로 통일한다        LOG --sort-by=date

파싱은 저장소 상태를 전혀 모른다. "이 브랜치가 존재하는가" 같은 판단은 명령을
실행하는 쪽의 몫이고, 여기서는 문자열을 구조로 바꾸는 일만 한다.
"""

from dataclasses import dataclass

from mini_git.errors import ParseError

DQUOTE = '"'
SQUOTE = "'"
QUOTES = frozenset({DQUOTE, SQUOTE})


@dataclass(frozen=True)
class Command:
    """파싱이 끝난 명령 하나.

    Attributes:
        name: 소문자로 정규화된 명령 이름. 예) "commit"
        args: 위치 인자 목록. 따옴표는 제거된 상태다.
        options: --key=value 로 들어온 것들. 예) {"sort-by": "date"}
    """

    name: str
    args: tuple[str, ...]
    options: dict[str, str]


def tokenize(line: str) -> list[str]:
    """한 줄을 토큰 목록으로 쪼갠다.

    공백으로 나누되, 따옴표로 감싼 구간은 공백을 포함해 토큰 하나로 유지한다.
    따옴표 자체는 결과에 남기지 않는다. 홑따옴표와 겹따옴표를 모두 허용하되,
    구간을 닫는 것은 그 구간을 연 문자뿐이다. 그래서 "it's fine" 안의 홑따옴표는
    닫는 따옴표가 아니라 그냥 글자로 남는다.

    닫히지 않은 채 줄이 끝나면 ParseError 를 던진다. 남은 부분을 토큰으로
    받아주면 사용자가 오타를 눈치채지 못한 채 엉뚱한 커밋 메시지가 저장되므로,
    조용히 넘어가는 대신 알린다.

    예)
        'branch feature'                  -> ['branch', 'feature']
        'commit "Add login feature"'      -> ['commit', 'Add login feature']
        "init 'Alice Kim'"                -> ['init', 'Alice Kim']
        'commit "it\\'s fine"'             -> ['commit', "it's fine"]
        'log --sort-by=date'              -> ['log', '--sort-by=date']
        '  init   "Alice"  '              -> ['init', 'Alice']
        ''                                -> []
        'commit "unclosed'                -> ParseError

    Args:
        line: 사용자가 입력한 한 줄.

    Returns:
        토큰 목록. 빈 줄이거나 공백뿐이면 빈 목록.

    Raises:
        ParseError: 따옴표가 닫히지 않은 채 줄이 끝났을 때.
    """
    tokens: list[str] = []
    current = ""
    quote_char: str | None = None   # None = 따옴표 밖. 아니면 구간을 연 문자
    has_token = False               # '아직 토큰 없음' 과 '빈 토큰("")' 구분

    for char in line:
        if quote_char is not None:
            # 따옴표 구간 안. 열 때 쓴 문자를 만나야 닫힌다.
            if char == quote_char:
                quote_char = None
            else:
                current += char
            has_token = True
        elif char in QUOTES:
            quote_char = char
            has_token = True
        elif char.isspace():
            # 토큰 경계. 만들던 토큰이 있을 때만 끊는다(연속 공백 무시).
            if has_token:
                tokens.append(current)
                current, has_token = "", False
        else:
            current += char
            has_token = True

    if quote_char is not None:
        raise ParseError(quote_char)
    if has_token:
        tokens.append(current)
    return tokens


def parse(line: str) -> Command | None:
    """한 줄을 Command 로 바꾼다.

    빈 줄에는 아무 일도 일어나지 않아야 하므로 None 을 돌려준다.
    (오류가 아니라 "실행할 것이 없음" 이다.)
    """
    tokens = tokenize(line)
    if not tokens:
        return None

    name = tokens[0].lower()
    args: list[str] = []
    options: dict[str, str] = {}

    for token in tokens[1:]:
        if token.startswith("--") and "=" in token:
            key, value = token[2:].split("=", 1)
            options[key] = value
        else:
            args.append(token)

    return Command(name=name, args=tuple(args), options=options)
