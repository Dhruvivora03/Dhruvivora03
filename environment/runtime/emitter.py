"""Bytecode emitter for the compiler.

Walks the AST and emits stack-based bytecode instructions.
The virtual machine uses a simple operand stack where:
  - PUSH_CONST pushes a value onto the stack
  - LOAD_VAR pushes a variable's value onto the stack
  - STORE_VAR pops the top value and stores it
  - ADD/SUB/MUL/DIV pop two operands and push the result
  - PRINT pops and outputs the top value

For binary operations, the left operand is pushed first,
then the right operand, so the right operand is on top of stack.
"""


class Instruction:
    """Single bytecode instruction with opcode and optional operand."""

    def __init__(self, opcode, operand=None):
        self.opcode = opcode
        self.operand = operand

    def __repr__(self):
        if self.operand is not None:
            return f"{self.opcode} {self.operand}"
        return self.opcode

    def to_dict(self):
        result = {"opcode": self.opcode}
        if self.operand is not None:
            result["operand"] = self.operand
        return result


class BytecodeEmitter:
    """Emits bytecode from AST nodes.

    Maintains a symbol table reference for variable resolution.
    Variables not found in the symbol table are treated as
    having a default value of 0.
    """

    def __init__(self, symbol_table):
        self._symbols = symbol_table
        self._instructions = []

    @property
    def instructions(self):
        return list(self._instructions)

    def emit_program(self, statements):
        """Emit bytecode for a complete program (list of statements)."""
        self._instructions = []
        for stmt in statements:
            self._emit_statement(stmt)
        return self._instructions

    def _emit_statement(self, node):
        """Emit bytecode for a statement node."""
        from runtime.parser import Assignment, PrintStmt
        if isinstance(node, Assignment):
            self._emit_expr(node.expr)
            self._instructions.append(
                Instruction("STORE_VAR", node.target)
            )
        elif isinstance(node, PrintStmt):
            self._emit_expr(node.expr)
            self._instructions.append(Instruction("PRINT"))

    def _emit_expr(self, node):
        """Emit bytecode for an expression node."""
        from runtime.parser import NumberLiteral, VariableRef, BinaryOp

        if isinstance(node, NumberLiteral):
            self._instructions.append(
                Instruction("PUSH_CONST", node.value)
            )
        elif isinstance(node, VariableRef):
            # Look up variable in symbol table
            if node.name in self._symbols:
                self._instructions.append(
                    Instruction("LOAD_VAR", node.name)
                )
            else:
                # Variable not in symbol table, use default
                self._instructions.append(
                    Instruction("PUSH_CONST", 0)
                )
        elif isinstance(node, BinaryOp):
            # Left operand pushed first, right operand on top
            self._emit_expr(node.left)
            self._emit_expr(node.right)
            op_map = {"+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV"}
            self._instructions.append(
                Instruction(op_map[node.op])
            )
