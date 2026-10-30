"""파서 회귀 테스트.

여기 적힌 것이 곧 tokenize / parse 의 스펙이다.
"""

import unittest

from mini_git.parser import Command, parse, tokenize


class TokenizeTest(unittest.TestCase):
    """공백으로 쪼개되, 따옴표 구간은 하나로 유지한다."""

    def test_공백으로_쪼갠다(self):
        self.assertEqual(tokenize("branch feature"), ["branch", "feature"])

    def test_겹따옴표_안의_공백은_유지된다(self):
        self.assertEqual(
            tokenize('commit "Add login feature"'),
            ["commit", "Add login feature"],
        )

    def test_홑따옴표도_같게_동작한다(self):
        self.assertEqual(tokenize("init 'Alice Kim'"), ["init", "Alice Kim"])

    def test_따옴표는_결과에_남지_않는다(self):
        self.assertEqual(tokenize('init "Alice"'), ["init", "Alice"])

    def test_앞뒤와_사이의_잉여_공백은_무시된다(self):
        self.assertEqual(tokenize('   init    "Alice"   '), ["init", "Alice"])

    def test_빈_줄은_빈_목록(self):
        self.assertEqual(tokenize(""), [])
        self.assertEqual(tokenize("     "), [])

    def test_옵션은_한_토큰으로_남는다(self):
        self.assertEqual(tokenize("log --sort-by=date"), ["log", "--sort-by=date"])

    def test_옵션값에_공백이_있으면_따옴표로_감싼다(self):
        self.assertEqual(
            tokenize('search --author="Alice Kim"'),
            ["search", "--author=Alice Kim"],
        )

    def test_인자가_여러_개일_수_있다(self):
        self.assertEqual(
            tokenize("path a1b2c3 g7h8i9"),
            ["path", "a1b2c3", "g7h8i9"],
        )


class ParseTest(unittest.TestCase):
    """토큰을 Command 로 조립한다."""

    def test_명령어는_소문자로_정규화된다(self):
        self.assertEqual(parse("INIT Alice").name, "init")
        self.assertEqual(parse("Init Alice").name, "init")

    def test_위치_인자가_순서대로_담긴다(self):
        command = parse("path a1b2c3 g7h8i9")
        self.assertEqual(command.args, ("a1b2c3", "g7h8i9"))
        self.assertEqual(command.options, {})

    def test_옵션은_키와_값으로_분리된다(self):
        command = parse("log --sort-by=date")
        self.assertEqual(command.args, ())
        self.assertEqual(command.options, {"sort-by": "date"})

    def test_인자와_옵션이_섞여도_된다(self):
        command = parse('search "login" --author=Alice')
        self.assertEqual(command.args, ("login",))
        self.assertEqual(command.options, {"author": "Alice"})

    def test_값에_등호가_있으면_첫_등호에서만_자른다(self):
        command = parse("search --author=a=b")
        self.assertEqual(command.options, {"author": "a=b"})

    def test_빈_줄은_None(self):
        self.assertIsNone(parse(""))
        self.assertIsNone(parse("   "))

    def test_Command_는_불변이다(self):
        command = parse("init Alice")
        self.assertIsInstance(command, Command)
        with self.assertRaises(Exception):
            command.name = "commit"


if __name__ == "__main__":
    unittest.main()
