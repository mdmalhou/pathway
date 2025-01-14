# Copyright © 2023 Pathway

"""Variant of API with immediate evaluation in Python."""

from __future__ import annotations

import asyncio
import dataclasses
from enum import Enum
from typing import Any, Callable, Iterable, List, Optional, Tuple, Union

from pathway.internals.api import CapturedTable, Value
from pathway.internals.dtype import DType
from pathway.internals.monitoring import StatsMonitor

class BasePointer:
    pass

def ref_scalar(*args, optional=False) -> BasePointer: ...

class PathwayType(Enum):
    ANY = 1
    STRING = 2
    INT = 3
    BOOL = 4
    FLOAT = 5

class Universe:
    @property
    def id_column(self) -> Column: ...

@dataclasses.dataclass(frozen=True)
class PyTrace:
    file_name: str
    line_number: int
    line: str

@dataclasses.dataclass(frozen=True)
class EvalProperties:
    trace: Optional[PyTrace] = None
    dtype: Optional[DType] = None

class Column:
    """A Column holds data and conceptually is a Dict[Universe elems, dt]

    Columns should not be constructed directly, but using methods of the scope.
    All fields are private.
    """

    @property
    def universe(self) -> Universe: ...

class Table:
    """A `Table` is a thin wrapper over a list of Columns.

    universe and columns are public fields - tables can be constructed
    """

    def __init__(self, universe: Universe, columns: List[Column]): ...
    @property
    def universe(self) -> Universe: ...
    @property
    def columns(self) -> List[Column]: ...

class MissingValueError(BaseException):
    "Marker class to indicate missing attributes"

class EngineError(Exception):
    "Marker class to indicate engine error"

class Reducer:
    ARG_MIN: Reducer
    MIN: Reducer
    ARG_MAX: Reducer
    MAX: Reducer
    SUM: Reducer
    INT_SUM: Reducer
    SORTED_TUPLE: Reducer
    COUNT: Reducer
    UNIQUE: Reducer
    ANY: Reducer

class Expression:
    @staticmethod
    def const(value: Value) -> Expression: ...
    @staticmethod
    def argument(index: int) -> Expression: ...
    @staticmethod
    def apply(fun: Callable, /, *args: Expression) -> Expression: ...
    @staticmethod
    def is_none(expr: Expression) -> Expression: ...
    @staticmethod
    def not_(expr: Expression) -> Expression: ...
    @staticmethod
    def and_(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def or_(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def xor(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def int_eq(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def int_ne(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def int_lt(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def int_le(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def int_gt(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def int_ge(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def int_neg(expr: Expression) -> Expression: ...
    @staticmethod
    def int_add(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def int_sub(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def int_mul(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def int_floor_div(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def int_true_div(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def int_mod(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def int_pow(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def int_lshift(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def int_rshift(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def int_and(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def int_or(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def int_xor(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def float_eq(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def float_ne(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def float_lt(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def float_le(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def float_gt(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def float_ge(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def float_neg(expr: Expression) -> Expression: ...
    @staticmethod
    def float_add(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def float_sub(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def float_mul(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def float_floor_div(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def float_true_div(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def float_mod(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def float_pow(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def str_eq(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def str_ne(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def str_lt(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def str_le(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def str_gt(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def str_ge(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def str_add(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def str_rmul(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def str_lmul(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def ptr_eq(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def ptr_ne(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def eq(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def ne(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def if_else(if_: Expression, then: Expression, else_: Expression) -> Expression: ...
    @staticmethod
    def int_to_float(expr: Expression) -> Expression: ...
    @staticmethod
    def int_to_bool(expr: Expression) -> Expression: ...
    @staticmethod
    def int_to_str(expr: Expression) -> Expression: ...
    @staticmethod
    def float_to_int(expr: Expression) -> Expression: ...
    @staticmethod
    def float_to_bool(expr: Expression) -> Expression: ...
    @staticmethod
    def float_to_str(expr: Expression) -> Expression: ...
    @staticmethod
    def bool_to_int(expr: Expression) -> Expression: ...
    @staticmethod
    def bool_to_float(expr: Expression) -> Expression: ...
    @staticmethod
    def bool_to_str(expr: Expression) -> Expression: ...
    @staticmethod
    def str_to_int(expr: Expression) -> Expression: ...
    @staticmethod
    def str_to_float(expr: Expression) -> Expression: ...
    @staticmethod
    def str_to_bool(expr: Expression) -> Expression: ...
    @staticmethod
    def date_time_naive_eq(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def date_time_naive_ne(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def date_time_naive_lt(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def date_time_naive_le(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def date_time_naive_gt(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def date_time_naive_ge(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def date_time_naive_nanosecond(expr: Expression) -> Expression: ...
    @staticmethod
    def date_time_naive_microsecond(expr: Expression) -> Expression: ...
    @staticmethod
    def date_time_naive_millisecond(expr: Expression) -> Expression: ...
    @staticmethod
    def date_time_naive_second(expr: Expression) -> Expression: ...
    @staticmethod
    def date_time_naive_minute(expr: Expression) -> Expression: ...
    @staticmethod
    def date_time_naive_hour(expr: Expression) -> Expression: ...
    @staticmethod
    def date_time_naive_day(expr: Expression) -> Expression: ...
    @staticmethod
    def date_time_naive_month(expr: Expression) -> Expression: ...
    @staticmethod
    def date_time_naive_year(expr: Expression) -> Expression: ...
    @staticmethod
    def date_time_naive_timestamp(expr: Expression) -> Expression: ...
    @staticmethod
    def date_time_naive_sub(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def date_time_naive_add_duration(
        lhs: Expression, rhs: Expression
    ) -> Expression: ...
    @staticmethod
    def date_time_naive_sub_duration(
        lhs: Expression, rhs: Expression
    ) -> Expression: ...
    @staticmethod
    def date_time_naive_strptime(expr: Expression, fmt: Expression) -> Expression: ...
    @staticmethod
    def date_time_naive_strftime(expr: Expression, fmt: Expression) -> Expression: ...
    @staticmethod
    def date_time_naive_from_timestamp(
        expr: Expression, unit: Expression
    ) -> Expression: ...
    @staticmethod
    def date_time_naive_to_utc(
        expr: Expression, from_timezone: Expression
    ) -> Expression: ...
    @staticmethod
    def date_time_naive_round(expr: Expression, duration: Expression) -> Expression: ...
    @staticmethod
    def date_time_naive_floor(expr: Expression, duration: Expression) -> Expression: ...
    @staticmethod
    def date_time_utc_eq(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def date_time_utc_ne(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def date_time_utc_lt(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def date_time_utc_le(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def date_time_utc_gt(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def date_time_utc_ge(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def date_time_utc_nanosecond(expr: Expression) -> Expression: ...
    @staticmethod
    def date_time_utc_microsecond(expr: Expression) -> Expression: ...
    @staticmethod
    def date_time_utc_millisecond(expr: Expression) -> Expression: ...
    @staticmethod
    def date_time_utc_second(expr: Expression) -> Expression: ...
    @staticmethod
    def date_time_utc_minute(expr: Expression) -> Expression: ...
    @staticmethod
    def date_time_utc_hour(expr: Expression) -> Expression: ...
    @staticmethod
    def date_time_utc_day(expr: Expression) -> Expression: ...
    @staticmethod
    def date_time_utc_month(expr: Expression) -> Expression: ...
    @staticmethod
    def date_time_utc_year(expr: Expression) -> Expression: ...
    @staticmethod
    def date_time_utc_timestamp(expr: Expression) -> Expression: ...
    @staticmethod
    def date_time_utc_sub(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def date_time_utc_add_duration(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def date_time_utc_sub_duration(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def date_time_utc_strptime(expr: Expression, fmt: Expression) -> Expression: ...
    @staticmethod
    def date_time_utc_strftime(expr: Expression, fmt: Expression) -> Expression: ...
    @staticmethod
    def date_time_utc_to_naive(
        expr: Expression, to_timezone: Expression
    ) -> Expression: ...
    @staticmethod
    def date_time_utc_round(expr: Expression, duration: Expression) -> Expression: ...
    @staticmethod
    def date_time_utc_floor(expr: Expression, duration: Expression) -> Expression: ...
    @staticmethod
    def duration_eq(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def duration_ne(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def duration_lt(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def duration_le(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def duration_gt(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def duration_ge(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def _duration_get_in_unit(
        expr: Expression, values: Any, num_nanoseconds: int
    ) -> int: ...
    @staticmethod
    def duration_nanoseconds(expr: Expression) -> Expression: ...
    @staticmethod
    def duration_microseconds(expr: Expression) -> Expression: ...
    @staticmethod
    def duration_milliseconds(expr: Expression) -> Expression: ...
    @staticmethod
    def duration_seconds(expr: Expression) -> Expression: ...
    @staticmethod
    def duration_minutes(expr: Expression) -> Expression: ...
    @staticmethod
    def duration_hours(expr: Expression) -> Expression: ...
    @staticmethod
    def duration_days(expr: Expression) -> Expression: ...
    @staticmethod
    def duration_weeks(expr: Expression) -> Expression: ...
    @staticmethod
    def duration_neg(expr: Expression) -> Expression: ...
    @staticmethod
    def duration_add(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def duration_add_date_time_naive(
        lhs: Expression, rhs: Expression
    ) -> Expression: ...
    @staticmethod
    def duration_add_date_time_utc(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def duration_sub(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def duration_mul_by_int(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def int_mul_by_duration(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def duration_div_by_int(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def duration_floor_div(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def duration_true_div(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def duration_mod(lhs: Expression, rhs: Expression) -> Expression: ...
    @staticmethod
    def pointer_from(*args: Expression, optional: bool) -> Expression: ...
    @staticmethod
    def make_tuple(*args: Expression) -> Expression: ...
    @staticmethod
    def sequence_get_item_checked(
        expr: Expression, index: Expression, default: Expression
    ) -> Expression: ...
    @staticmethod
    def sequence_get_item_unchecked(
        expr: Expression, index: Expression
    ) -> Expression: ...

class MonitoringLevel(Enum):
    NONE = 0
    IN_OUT = 1
    ALL = 2

class Context:
    # "Location" of the current attribute in the transformer computation
    this_row: BasePointer
    data: Tuple[Value, BasePointer]

    def raising_get(self, column: int, row: BasePointer, *args: Value) -> Value: ...

class Computer:
    @classmethod
    def from_raising_fun(
        cls,
        fun: Callable[[Context], Value],
        *,
        dtype: DType,
        is_output: bool,
        is_method: bool,
        universe: Universe,
        data: Value = None,
        data_column: Optional[Column] = None,
    ) -> Computer: ...

ComplexColumn = Union[Column, Computer]

class VennUniverses:
    def only_left(self) -> Universe: ...
    def only_right(self) -> Universe: ...
    def both(self) -> Universe: ...

class Scope:
    @property
    def parent(self) -> Optional[Scope]: ...
    def empty_table(self, dtypes: Iterable[DType]) -> Table: ...
    def iterate(
        self,
        iterated: List[Table],
        iterated_with_universe: List[Table],
        extra: List[Table],
        logic: Callable[
            [Scope, List[Table], List[Table], List[Table]],
            Tuple[List[Table], List[Table]],
        ],
        *,
        limit: Optional[int] = None,
    ) -> Tuple[List[Table], List[Table]]:
        """Fixed-point iteration

        logic is called with a new scope, clones of tables from iterated,
        clones of tables from extra.
        logic should not use any other outside tables.
        logic must return a list of tables corresponding to iterated:
        result[i] is the result of single iteration on iterated[i]
        """
        ...
    # Evaluators for expressions

    def static_universe(self, keys: Iterable[BasePointer]) -> Universe: ...
    def static_column(
        self, universe: Universe, rows: Iterable[Tuple[BasePointer, Any]], dt: DType
    ) -> Column: ...
    def map_column(
        self,
        table: Table,
        function: Callable[[Tuple[Value, ...]], Value],
        properties: EvalProperties,
    ) -> Column: ...
    def expression_column(
        self, table: Table, expression: Expression, properties: EvalProperties
    ) -> Column: ...
    def async_map_column(
        self, table: Table, function: Callable[..., Value], properties: EvalProperties
    ): ...
    def unsafe_map_column_numba(
        self, table: Table, function: Any, properties: EvalProperties
    ) -> Column: ...
    def filter_universe(self, universe: Universe, column: Column) -> Universe: ...
    def intersect_universe(
        self, universe: Universe, *universes: Universe
    ) -> Universe: ...
    def union_universe(self, universe: Universe, *universes: Universe) -> Universe: ...
    def venn_universes(
        self, left_universe: Universe, right_universe: Universe
    ) -> VennUniverses: ...
    def reindex_universe(self, column: Column) -> Universe: ...
    def restrict_column(
        self,
        universe: Universe,
        column: Column,
    ) -> Column: ...
    def override_column_universe(
        self, universe: Universe, column: Column
    ) -> Column: ...
    def reindex_column(
        self,
        column_to_reindex: Column,
        reindexing_column: Column,
        reindexing_universe: Universe,
    ) -> Column: ...
    def connector_table(
        self,
        data_source: DataStorage,
        data_format: DataFormat,
        commit_duration_ms: Optional[int],
    ) -> Table: ...
    @staticmethod
    def table(universe: Universe, columns: List[Column]) -> Table: ...

    # Grouping and joins

    def group_by(
        self, table: Table, requested_columns: List[Column], set_id: bool = False
    ) -> Grouper:
        """
        Args:
            table: a list of columns to group by.
        """
        ...
    def ix(
        self,
        keys_column: Column,
        input_universe: Universe,
        strict: bool,
        optional: bool,
    ) -> Ixer: ...
    def join(
        self,
        left_table: Table,
        right_table: Table,
        assign_id: bool = False,
        left_ear: bool = False,
        right_ear: bool = False,
    ) -> Joiner: ...

    # Transformers

    def complex_columns(self, inputs: List[ComplexColumn]) -> List[Column]: ...

    # Updates

    def update_rows(
        self, universe: Universe, column: Column, updates: Column
    ) -> Column:
        """Updates rows of `column`, breaking ties in favor of `updates`"""
        ...
    def debug_universe(self, name: str, universe: Universe): ...
    def debug_column(self, name: str, column: Column): ...
    def concat(self, universes: Iterable[Universe]) -> Concat: ...
    def flatten(self, flatten_column: Column) -> Flatten: ...
    def sort(
        self, key_column: Column, instance_column: Column
    ) -> Tuple[Column, Column]: ...
    def probe_universe(self, universe: Universe, operator_id: int): ...
    def probe_column(self, column: Column, operator_id: int): ...
    def subscribe_table(self, table: Table, on_change: Callable, on_end: Callable): ...
    def output_table(
        self, table: Table, data_sink: DataStorage, data_format: DataFormat
    ): ...

class Joiner:
    @property
    def universe(self) -> Universe: ...
    def select_left_column(self, column: Column) -> Column: ...
    def select_right_column(self, column: Column) -> Column: ...

class Ixer:
    @property
    def universe(self) -> Universe: ...
    def ix_column(self, column: Column) -> Column: ...

class Grouper:
    @property
    def universe(self) -> Universe: ...
    def input_column(self, column: Column) -> Column: ...
    def count_column(self) -> Column: ...
    def reducer_column(self, reducer: Reducer, column: Column) -> Column: ...
    def reducer_ix_column(
        self, reducer: Reducer, ixer: Ixer, input_column: Column
    ) -> Column: ...

class Concat:
    @property
    def universe(self) -> Universe: ...
    def concat_column(self, columns: List[Column]) -> Column: ...

class Flatten:
    @property
    def universe(self) -> Universe: ...
    def get_flattened_column(self) -> Column: ...
    def explode_column(self, column: Column) -> Column: ...

def run_with_new_graph(
    logic: Callable[[Scope], Iterable[Table]],
    event_loop: asyncio.AbstractEventLoop,
    stats_monitor: Optional[StatsMonitor] = None,
    *,
    ignore_asserts: bool = False,
    monitoring_level: MonitoringLevel = MonitoringLevel.NONE,
    with_http_server: bool = False,
) -> List[CapturedTable]: ...
def unsafe_make_pointer(arg) -> BasePointer: ...

class DataFormat:
    value_fields: Any

    def __init__(self, *args, **kwargs): ...

class DataStorage:
    def __init__(self, *args, **kwargs): ...

class CsvParserSettings:
    def __init__(self, *args, **kwargs): ...

class AwsS3Settings:
    def __init__(self, *args, **kwargs): ...

class ValueField:
    def __init__(self, *args, **kwargs): ...
    def set_default(self, *args, **kwargs): ...

class PythonSubject:
    def __init__(self, *args, **kwargs): ...

class ElasticSearchAuth:
    def __init__(self, *args, **kwargs): ...

class ElasticSearchParams:
    def __init__(self, *args, **kwargs): ...
