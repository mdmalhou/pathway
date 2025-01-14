# Copyright © 2023 Pathway

from __future__ import annotations

import itertools
from collections import defaultdict
from typing import TYPE_CHECKING, Dict, Iterable

if TYPE_CHECKING:
    import pathway.internals.expression as expr
    from pathway.internals.table import Table
    from pathway.internals.trace import Trace

from pathway.internals.expression_visitor import ExpressionVisitor


class ExpressionFormatter(ExpressionVisitor):
    table_numbers: Dict[Table, int]

    def __init__(self):
        self.table_counter = itertools.count(start=1)
        self.table_numbers = defaultdict(lambda: next(self.table_counter))

    def table_infos(self):
        for tab, cnt in self.table_numbers.items():
            trace: Trace = tab._source.operator.trace
            yield f"<table{cnt}>", trace.user_frame

    def print_table_infos(self):
        return "\n".join(
            f"{name} created in {frame.filename}:{frame.line_number}"
            for name, frame in self.table_infos()
        )

    def eval_column_val(self, expression: expr.ColumnReference):
        return f"<table{self.table_numbers[expression._table]}>.{expression._name}"

    def eval_unary_op(self, expression: expr.ColumnUnaryOpExpression):
        symbol = getattr(expression._operator, "_symbol", expression._operator.__name__)
        uexpr = self.eval_expression(expression._expr)
        return f"({symbol}{uexpr})"

    def eval_binary_op(self, expression: expr.ColumnBinaryOpExpression):
        symbol = getattr(expression._operator, "_symbol", expression._operator.__name__)
        lexpr = self.eval_expression(expression._left)
        rexpr = self.eval_expression(expression._right)
        return f"({lexpr} {symbol} {rexpr})"

    def eval_const(self, expression: expr.ColumnConstExpression):
        return repr(expression._val)

    def eval_reducer(self, expression: expr.ReducerExpression):
        args = self._eval_args_kwargs(expression._args)
        name = expression._reducer.__name__.lstrip("_")
        return f"pathway.reducers.{name}({args})"

    def eval_reducer_ix(self, expression: expr.ReducerIxExpression):
        return self.eval_reducer(expression)

    def eval_apply(self, expression: expr.ApplyExpression):
        args = self._eval_args_kwargs(expression._args, expression._kwargs)
        return f"pathway.apply({expression._fun.__name__}, {args})"

    def eval_async_apply(self, expression: expr.ApplyExpression):
        args = self._eval_args_kwargs(expression._args, expression._kwargs)
        return f"pathway.apply_async({expression._fun.__name__}, {args})"

    def eval_numbaapply(self, expression: expr.NumbaApplyExpression):
        args = self._eval_args_kwargs(expression._args, expression._kwargs)
        return f"pathway.numba_apply({expression._fun.__name__}, {args})"

    def eval_pointer(self, expression: expr.PointerExpression):
        kwargs: Dict[str, expr.ColumnExpression] = {}
        if expression._optional:
            import pathway.internals.expression as expr

            kwargs["optional"] = expr.ColumnConstExpression(True)
        args = self._eval_args_kwargs(expression._args, kwargs)
        return f"<table{self.table_numbers[expression._table]}>.pointer_from({args})"

    def eval_ix(self, expression: expr.ColumnIxExpression):
        args = [self.eval_expression(expression._keys_expression)]
        if expression._optional:
            args.append("optional=True")
        args_joined = ", ".join(args)
        name = expression._column_expression._name
        return f"<table{self.table_numbers[expression._column_expression._table]}>.ix({args_joined}).{name}"

    def eval_call(self, expression: expr.ColumnCallExpression):
        args = self._eval_args_kwargs(expression._args)
        return self.eval_expression(expression._col_expr) + f"({args})"

    def eval_cast(self, expression: expr.CastExpression):
        uexpr = self.eval_expression(expression._expr)
        return f"pathway.cast({_type_name(expression._return_type)}, {uexpr})"

    def eval_declare(self, expression: expr.DeclareTypeExpression):
        uexpr = self.eval_expression(expression._expr)
        return f"pathway.declare_type({_type_name(expression._return_type)}, {uexpr})"

    def eval_coalesce(self, expression: expr.CoalesceExpression):
        args = self._eval_args_kwargs(expression._args)
        return f"pathway.coalesce({args})"

    def eval_require(self, expression: expr.RequireExpression):
        args = self._eval_args_kwargs((expression._val, *expression._args))
        return f"pathway.require({args})"

    def eval_ifelse(self, expression: expr.IfElseExpression):
        args = self._eval_args_kwargs(
            (expression._if, expression._then, expression._else)
        )
        return f"pathway.if_else({args})"

    def eval_method_call(self, expression: expr.MethodCallExpression):
        object_ = self.eval_expression(expression._args[0])
        args = self._eval_args_kwargs(expression._args[1:])
        return f"({object_}).{expression._name}({args})"

    def _eval_args_kwargs(
        self,
        args: Iterable[expr.ColumnExpression] = (),
        kwargs: Dict[str, expr.ColumnExpression] = {},
    ):
        return ", ".join(
            itertools.chain(
                (self.eval_expression(arg) for arg in args),
                (
                    key + "=" + self.eval_expression(value)
                    for key, value in kwargs.items()
                ),
            )
        )

    def eval_make_tuple(self, expression: expr.MakeTupleExpression):
        args = self._eval_args_kwargs(expression._args)
        return f"pathway.make_tuple({args})"

    def eval_sequence_get(self, expression: expr.SequenceGetExpression):
        object = self.eval_expression(expression._object)
        args = [expression._index]
        if expression._check_if_exists:
            args += [expression._default]
        args_formatted = self._eval_args_kwargs(args)
        if expression._check_if_exists:
            return f"({object}).get({args_formatted})"
        else:
            return f"({object})[{args_formatted}]"


def get_expression_info(expression: expr.ColumnExpression) -> str:
    printer = ExpressionFormatter()
    expression_str = f"{printer.eval_expression(expression)},\n"
    expression_info = ""

    frame = expression._trace.user_frame
    if frame is not None:
        expression_info = f"called in {frame.filename}:{frame.line_number}\n"

    tabnames = printer.print_table_infos()
    if tabnames != "":
        tabnames = "with tables:\n" + tabnames + "\n"

    return expression_str + expression_info + tabnames


def _type_name(return_type):
    if isinstance(return_type, str):
        return repr(return_type)
    else:
        return return_type.__name__
