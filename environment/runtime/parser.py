"""Expression parser for the bytecode compiler.

Parses simple arithmetic programs into an AST representation.
Programs consist of variable assignments and expression statements
using standard arithmetic operators (+, -, *, /).
"""

import re


class ASTNode:
    """Base class for AST nodes."""
    pass


class NumberLiteral(ASTNode):
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"NumberLiteral({self.value})"


class VariableRef(ASTNode):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"VariableRef({self.name})"


class BinaryOp(ASTNode):
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right

    def __repr__(self):
        return f"BinaryOp({self.op}, {self.left}, {self.right})"


class Assignment(ASTNode):
    def __init__(self, target, expr):
        self.target = target
        self.expr = expr

    def __repr__(self):
        return f"Assignment({self.target}, {self.expr})"


class PrintStmt(ASTNode):
    def __init__(self, expr):
        self.expr = expr

    def __repr__(self):
        return f"PrintStmt({self.expr})"


class Parser:
    """Recursive descent parser for arithmetic expression programs.

    Supports:
        - Variable assignments: var = expr
        - Print statements: print(expr)
        - Arithmetic: +, -, *, / with standard precedence
        - Parenthesized expressions
        - Integer and float literals
    """

    def __init__(self):
        self._tokens = []
        self._pos = 0
        self._symbols = {}

    @property
    def symbol_table(self):
        return dict(self._symbols)

    def parse(self, source_code):
        """Parse source code into a list of AST statements."""
        self._tokens = self._tokenize(source_code)
        self._pos = 0
        self._symbols = {}
        statements = []

        while self._pos < len(self._tokens):
            stmt = self._parse_statement()
            if stmt is not None:
                statements.append(stmt)

        return statements

    def _tokenize(self, source):
        """Tokenize source into a flat list of tokens."""
        tokens = []
        lines = source.strip().split("\n")
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Split preserving operators and parens
            parts = re.findall(
                r'[a-zA-Z_]\w*|[0-9]+(?:\.[0-9]+)?|[+\-*/()=]', line
            )
            tokens.extend(parts)
            tokens.append("NEWLINE")
        return tokens

    def _current(self):
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return None

    def _advance(self):
        token = self._current()
        self._pos += 1
        return token

    def _parse_statement(self):
        """Parse a single statement (assignment, print, or expression)."""
        token = self._current()

        if token == "NEWLINE":
            self._advance()
            return None

        if token == "print":
            return self._parse_print()

        # Check for assignment
        if (token and token.isidentifier() and
                self._pos + 1 < len(self._tokens) and
                self._tokens[self._pos + 1] == "="):
            return self._parse_assignment()

        # Expression statement
        expr = self._parse_expr()
        if self._current() == "NEWLINE":
            self._advance()
        return PrintStmt(expr)

    def _parse_assignment(self):
        """Parse variable assignment: name = expr"""
        name = self._advance()
        self._advance()  # consume '='
        expr = self._parse_expr()
        if self._current() == "NEWLINE":
            self._advance()

        # Register variable in symbol table with normalized name
        normalized = name.lower()
        self._symbols[normalized] = {"type": "variable", "defined": True}
        return Assignment(normalized, expr)

    def _parse_print(self):
        """Parse print statement: print(expr)"""
        self._advance()  # consume 'print'
        self._advance()  # consume '('
        expr = self._parse_expr()
        self._advance()  # consume ')'
        if self._current() == "NEWLINE":
            self._advance()
        return PrintStmt(expr)

    def _parse_expr(self):
        """Parse addition/subtraction level."""
        left = self._parse_term()
        while self._current() in ("+", "-"):
            op = self._advance()
            right = self._parse_term()
            left = BinaryOp(op, left, right)
        return left

    def _parse_term(self):
        """Parse multiplication/division level."""
        left = self._parse_factor()
        while self._current() in ("*", "/"):
            op = self._advance()
            right = self._parse_factor()
            left = BinaryOp(op, left, right)
        return left

    def _parse_factor(self):
        """Parse atomic expressions (numbers, variables, parens)."""
        token = self._current()

        if token == "(":
            self._advance()
            expr = self._parse_expr()
            self._advance()  # consume ')'
            return expr

        if token and re.match(r'^[0-9]+(\.[0-9]+)?$', token):
            self._advance()
            if "." in token:
                return NumberLiteral(float(token))
            return NumberLiteral(int(token))

        if token and token.isidentifier() and token != "NEWLINE":
            self._advance()
            return VariableRef(token)

        self._advance()
        return NumberLiteral(0)
