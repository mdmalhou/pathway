# Copyright © 2023 Pathway

from __future__ import annotations

import functools
import os
import pathlib
import re
from typing import Any, List, Optional, Tuple
from unittest import mock

import numpy as np
import pandas as pd
import pytest

import pathway as pw
import pathway.internals.shadows.operator as operator
from pathway.debug import table_from_pandas, table_to_pandas
from pathway.internals import api
from pathway.internals.expression import NumbaApplyExpression
from pathway.tests.utils import (
    T,
    assert_table_equality,
    assert_table_equality_wo_index,
    assert_table_equality_wo_index_types,
    assert_table_equality_wo_types,
    run_all,
    run_graph_and_validate_result,
    xfail_no_numba,
)


@pytest.mark.parametrize(
    "asserter",
    [
        assert_table_equality,
        assert_table_equality_wo_index,
        assert_table_equality_wo_types,
        assert_table_equality_wo_index_types,
    ],
)
@pytest.mark.parametrize(
    "unexpected",
    [
        """
            | foo
        1   | 1
        """,
        """
            | foo   | bar
        1   | 42    | 42
        """,
        """
            | bar   | foo
        1   | 1     | 1
        """,
    ],
)
def test_assert_table_unexpected_columns(asserter, unexpected):
    input = T(
        """
            | foo   | bar
        1   | 1     | 1
        """
    )

    with pytest.raises((RuntimeError, AssertionError)):
        asserter(input, T(unexpected))


def test_input_operator():
    input = T(
        """
            | foo
        1   | 1
        2   | 2
        """
    )

    assert_table_equality(
        input,
        T(
            """
                | foo
            1   | 1
            2   | 2
            """
        ),
    )


def test_select_column_ref():
    t_latin = T(
        """
            | lower | upper
        1   | a     | A
        2   | b     | B
        26  | z     | Z
        """
    )
    t_num = T(
        """
            | num
        1   | 1
        2   | 2
        26  | 26
        """
    ).with_universe_of(t_latin)

    res = t_latin.select(num=t_num.num, upper=t_latin["upper"])

    assert_table_equality(
        res,
        T(
            """
                | num | upper
            1   | 1   | A
            2   | 2   | B
            26  | 26  | Z
            """
        ),
    )


def test_select_arithmetic_with_const():
    table = T(
        """
        a
        42
        """
    )

    res = table.select(
        table.a,
        add=table.a + 1,
        radd=1 + table.a,
        sub=table.a - 1,
        rsub=1 - table.a,
        mul=table.a * 2,
        rmul=2 * table.a,
        truediv=table.a / 4,
        rtruediv=63 / table.a,
        floordiv=table.a // 4,
        rfloordiv=63 // table.a,
        mod=table.a % 4,
        rmod=63 % table.a,
        pow=table.a**2,
        rpow=2**table.a,
    )

    assert_table_equality(
        res,
        T(
            """
            a  | add | radd | sub | rsub | mul | rmul | truediv | rtruediv | floordiv | rfloordiv | mod | rmod | pow  | rpow
            42 | 43  | 43   | 41  | -41  | 84  | 84   | 10.5    | 1.5      | 10       | 1         | 2   | 21   | 1764 | 4398046511104
            """  # noqa: E501
        ),
    )


def test_select_values():
    t1 = T(
        """
    | lower | upper
    1  | a     | A
    2  | b     | B
    """
    )

    res = t1.select(foo="alpha", bar="beta")
    assert_table_equality(
        res,
        T(
            """
    | foo   | bar
    1  | alpha | beta
    2  | alpha | beta
        """
        ),
    )


def test_select_column_different_universe():
    foo = T(
        """
        | col
    1  | a
    2  | b
    """
    )
    bar = T(
        """
            | col
        3  | a
        4  | b
        5  | c
        """
    )
    with pytest.raises(ValueError):
        foo.select(ret=bar.col)


def test_select_const_expression():
    input = T(
        """
            | foo | bar
        1   | 1   | 3
        2   | 2   | 4
        """
    )

    result = input.select(a=42)

    assert_table_equality(
        result,
        T(
            """
            | a
        1   | 42
        2   | 42
        """
        ),
    )


def test_select_simple_expression():
    input = T(
        """
            | foo | bar
        1   | 1   | 3
        2   | 2   | 4
        """
    )

    result = input.select(a=input.bar + input.foo)

    assert_table_equality(
        result,
        T(
            """
                | a
            1   | 4
            2   | 6
            """
        ),
    )


def test_select_int_unary():
    input = T(
        """
        a
        1
        """
    )

    result = input.select(
        input.a,
        minus=-input.a,
    )

    assert_table_equality(
        result,
        T(
            """
            a | minus
            1 | -1
            """
        ),
    )


def test_select_int_binary():
    input = T(
        """
        a | b
        1 | 2
        """
    )

    result = input.select(
        input.a,
        input.b,
        add=input.a + input.b,
        sub=input.a - input.b,
        truediv=input.a / input.b,
        floordiv=input.a // input.b,
        mul=input.a * input.b,
    )

    assert_table_equality(
        result,
        T(
            """
            a | b | add | sub | truediv | floordiv | mul
            1 | 2 | 3   | -1  | 0.5     | 0        | 2
            """
        ),
    )


def test_select_int_comparison():
    input = T(
        """
        a | b
        1 | 2
        2 | 2
        3 | 2
        """
    )

    result = input.select(
        input.a,
        input.b,
        eq=input.a == input.b,
        ne=input.a != input.b,
        lt=input.a < input.b,
        le=input.a <= input.b,
        gt=input.a > input.b,
        ge=input.a >= input.b,
    )

    assert_table_equality(
        result,
        T(
            """
            a | b | eq    | ne    | lt    | le    | gt    | ge
            1 | 2 | false | true  | true  | true  | false | false
            2 | 2 | true  | false | false | true  | false | true
            3 | 2 | false | true  | false | false | true  | true
            """
        ),
    )


def test_select_float_comparison():
    input = T(
        """
        a   | b
        1.5 | 2.5
        2.5 | 2.5
        3.5 | 2.5
        """
    )

    result = input.select(
        input.a,
        input.b,
        eq=input.a == input.b,
        ne=input.a != input.b,
        lt=input.a < input.b,
        le=input.a <= input.b,
        gt=input.a > input.b,
        ge=input.a >= input.b,
    )

    assert_table_equality(
        result,
        T(
            """
            a   | b   | eq    | ne    | lt    | le    | gt    | ge
            1.5 | 2.5 | false | true  | true  | true  | false | false
            2.5 | 2.5 | true  | false | false | true  | false | true
            3.5 | 2.5 | false | true  | false | false | true  | true
            """
        ),
    )


def test_select_mixed_comparison():
    input = T(
        """
        a   | b
        1.5 | 2
        2.0 | 2
        3.5 | 2
        """
    )
    result = input.select(
        input.a,
        input.b,
        eq=input.a == input.b,
        ne=input.a != input.b,
        lt=input.a < input.b,
        le=input.a <= input.b,
        gt=input.a > input.b,
        ge=input.a >= input.b,
    )

    assert_table_equality(
        result,
        T(
            """
            a   | b | eq    | ne    | lt    | le    | gt    | ge
            1.5 | 2 | false | true  | true  | true  | false | false
            2.0 | 2 | true  | false | false | true  | false | true
            3.5 | 2 | false | true  | false | false | true  | true
            """
        ),
    )


def test_select_float_unary():
    input = T(
        """
        a
        1.25
        """
    )

    result = input.select(
        input.a,
        minus=-input.a,
    )

    assert_table_equality(
        result,
        T(
            """
            a    | minus
            1.25 | -1.25
            """
        ),
    )


def test_select_float_binary():
    input = T(
        """
        a    | b
        1.25 | 2.5
        """
    )

    result = input.select(
        input.a,
        input.b,
        add=input.a + input.b,
        sub=input.a - input.b,
        truediv=input.a / input.b,
        floordiv=input.a // input.b,
        mul=input.a * input.b,
    )

    assert_table_equality(
        result,
        T(
            """
            a    | b   | add  | sub   | truediv | floordiv | mul
            1.25 | 2.5 | 3.75 | -1.25 | 0.5     | 0.0        | 3.125
            """
        ).update_types(floordiv=float),
    )


def test_select_bool_unary():
    input = T(
        """
        a
        true
        false
        """
    )

    result = input.select(
        input.a,
        not_=~input.a,
    )

    assert_table_equality(
        result,
        T(
            """
            a     | not_
            true  | false
            false | true
            """
        ),
    )


def test_select_bool_binary():
    input = T(
        """
        a     | b
        false | false
        false | true
        true  | false
        true  | true
        """
    )

    result = input.select(
        input.a,
        input.b,
        and_=input.a & input.b,
        or_=input.a | input.b,
        xor=input.a ^ input.b,
    )

    assert_table_equality(
        result,
        T(
            """
            a     |  b    | and_  | or_   | xor
            false | false | false | false | false
            false | true  | false | true  | true
            true  | false | false | true  | true
            true  | true  | true  | true  | false
            """
        ),
    )


def test_broadcasting_singlerow():
    table = T(
        """
    | pet  |  owner  | age
    1 |  1   | Alice   | 10
    2 |  1   | Bob     | 9
    3 |  2   | Alice   | 8
    4 |  1   | Bob     | 7
    5 |  0   | Eve     | 10
        """
    )

    row = table.reduce(val=1)
    returned = table.select(newval=row.ix_ref().val)

    expected = T(
        """
    | newval
    1 | 1
    2 | 1
    3 | 1
    4 | 1
    5 | 1
        """
    )
    assert_table_equality(returned, expected)


def test_indexing_single_value_groupby():
    indexed_table = T(
        """
    colA   | colB
    10     | A
    20     | A
    30     | B
    40     | B
    """
    )
    grouped_table = indexed_table.groupby(pw.this.colB).reduce(
        pw.this.colB, sum=pw.reducers.sum(pw.this.colA)
    )
    returned = indexed_table.select(
        *pw.this, sum=grouped_table.ix_ref(pw.this.colB).sum
    )
    expected = T(
        """
    colA   | colB | sum
    10     | A    | 30
    20     | A    | 30
    30     | B    | 70
    40     | B    | 70
    """
    )
    assert_table_equality_wo_index(returned, expected)


def test_indexing_single_value_groupby_hardcoded_value():
    indexed_table = T(
        """
    colA   | colB
    10     | A
    20     | A
    30     | B
    40     | B
    """
    )
    grouped_table = indexed_table.groupby(pw.this.colB).reduce(
        pw.this.colB, sum=pw.reducers.sum(pw.this.colA)
    )
    returned = indexed_table.select(*pw.this, sum_A=grouped_table.ix_ref("A").sum)
    expected = T(
        """
    colA   | colB | sum_A
    10     | A    | 30
    20     | A    | 30
    30     | B    | 30
    40     | B    | 30
    """
    )
    assert_table_equality_wo_index(returned, expected)


def test_indexing_two_values_groupby():
    indexed_table = T(
        """
    colA  | colB | colC
    1     | A    | D
    2     | A    | D
    10    | A    | E
    20    | A    | E
    100   | B    | F
    200   | B    | F
    1000  | B    | G
    2000  | B    | G
    """
    )
    grouped_table = indexed_table.groupby(pw.this.colB, pw.this.colC).reduce(
        pw.this.colB, pw.this.colC, sum=pw.reducers.sum(pw.this.colA)
    )
    returned = indexed_table.select(
        *pw.this, sum=grouped_table.ix_ref(pw.this.colB, pw.this.colC).sum
    )
    expected = T(
        """
    colA  | colB | colC | sum
    1     | A    | D    | 3
    2     | A    | D    | 3
    10    | A    | E    | 30
    20    | A    | E    | 30
    100   | B    | F    | 300
    200   | B    | F    | 300
    1000  | B    | G    | 3000
    2000  | B    | G    | 3000
    """
    )
    assert_table_equality_wo_index(returned, expected)


def test_ixref_optional():
    indexed_table = T(
        """
    colA  | colB | colC
    1     | A    | D
    2     | A    | D
    10    | A    | E
    20    | A    | E
    100   | B    | F
    200   | B    | F
    1000  | B    | G
    2000  | B    | G
    """
    )
    grouped_table = indexed_table.groupby(pw.this.colB, pw.this.colC).reduce(
        pw.this.colB, pw.this.colC, sum=pw.reducers.sum(pw.this.colA)
    )
    indexer = T(
        """
        refB | refC
        A    | D
        A    | E
        B    | F
        B    | G
             | D
        A    |
             |
        """
    )
    returned = indexer.select(
        *pw.this,
        sum=grouped_table.ix_ref(pw.this.refB, pw.this.refC, optional=True).sum,
    )
    expected = T(
        """
    refB  | refC | sum
     A    | D    | 3
     A    | E    | 30
     B    | F    | 300
     B    | G    | 3000
          | D    |
     A    |      |
          |      |
    """
    )
    assert_table_equality_wo_index(returned, expected)


def test_indexing_two_values_groupby_hardcoded_values():
    indexed_table = T(
        """
    colA   | colB
    10     | A
    20     | B
    """
    )
    indexed_table = indexed_table.groupby(pw.this.colA, pw.this.colB).reduce(*pw.this)
    tested_table = T(
        """
    colC
    10
    20
    """
    )
    returned = tested_table.select(
        *pw.this, new_value=indexed_table.ix_ref(10, "A").colA
    )
    expected = T(
        """
    colC   | new_value
    10     | 10
    20     | 10
    """
    )
    assert_table_equality(returned, expected)


def test_ix_ref_with_primary_keys():
    indexed_table = T(
        """
    colA   | colB
    10     | A
    20     | B
    """
    )
    indexed_table = indexed_table.with_id_from(pw.this.colB)
    tested_table = T(
        """
    colC
    10
    20
    """
    )
    returned = tested_table.select(*pw.this, new_value=indexed_table.ix_ref("A").colA)
    expected = T(
        """
    colC   | new_value
    10     | 10
    20     | 10
    """
    )
    assert_table_equality(returned, expected)


def test_select_universes():
    t1 = T(
        """
        | col
    1  | a
    2  | b
    3  | c
    """
    )

    t2 = T(
        """
        | col
    2  | 1
    3  | 1
    """
    ).promise_universe_is_subset_of(t1)

    assert_table_equality(
        t2.select(t1.col),
        T(
            """
        | col
    2  | b
    3  | c
    """
        ),
    )

    with pytest.raises(ValueError):
        t1.select(t2.col)


def test_select_op_universes():
    t1 = T(
        """
        | col
    1  | 11
    2  | 12
    3  | 13
    """
    )

    t2 = T(
        """
        | col
    2  | 1
    3  | 1
    """
    ).promise_universe_is_subset_of(t1)

    assert_table_equality(
        t2.select(col=t1.col + t2.col),
        T(
            """
        | col
    2  | 13
    3  | 14
    """
        ),
    )

    with pytest.raises(ValueError):
        t1.select(col=t1.col + t2.col)


def test_select_column_ix_args():
    t1 = T(
        """
      | a | b
    0 | 3 | 1
    1 | 4 | 2
    2 | 7 | 0
    """
    )
    expected = T(
        """
      | a | prev_a
    0 | 4 |   3
    1 | 7 |   4
    2 | 3 |   7
    """
    )
    t2 = t1.select(t1.ix(t1.pointer_from(t1.b)).a, prev_a=t1.a)
    assert_table_equality(t2, expected)


def test_concat():
    t1 = T(
        """
        | lower | upper
    1  | a     | A
    2  | b     | B
    """
    )
    t2 = T(
        """
        | lower | upper
    1  | c     | C
    """
    )

    res = pw.Table.concat_reindex(t1, t2)

    expected = T(
        """
    lower | upper
    a     | A
    b     | B
    c     | C
        """,
    )

    assert_table_equality_wo_index(res, expected)


def test_concat_unsafe():
    t1 = T(
        """
        | lower | upper
    1  | a     | A
    2  | b     | B
    """
    )
    t2 = T(
        """
       | lower | upper
    3  | c     | C
    """
    )

    pw.universes.promise_are_pairwise_disjoint(t1, t2)
    res = pw.Table.concat(t1, t2)

    expected = T(
        """
       | lower | upper
    1  | a     | A
    2  | b     | B
    3  | c     | C
        """,
    )
    assert_table_equality(res, expected)


def test_concat_unsafe_collision():
    t1 = T(
        """
        | lower | upper
    1  | a     | A
    2  | b     | B
    """
    )
    t2 = T(
        """
       | lower | upper
    1  | c     | C
    """
    )

    with pytest.raises(ValueError):
        pw.Table.concat(t1, t2)


@pytest.mark.parametrize("dtype", [np.int64, np.float64])
def test_flatten(dtype: Any):
    df = pd.DataFrame(
        {
            "array": [
                np.array([1, 2], dtype=dtype),
                np.array([], dtype=dtype),
                np.array([3, 4], dtype=dtype),
                np.array([10, 11, 12], dtype=dtype),
                np.array([4, 5, 6, 1, 2], dtype=dtype),
            ],
            "other": [-1, -2, -3, -4, -5],
        }
    )
    expected_df = pd.DataFrame(
        {
            "array": np.array([1, 2, 3, 4, 10, 11, 12, 4, 5, 6, 1, 2], dtype=dtype),
            "other": [-1, -1, -3, -3, -4, -4, -4, -5, -5, -5, -5, -5],
        }
    )
    new_dtype = List[int] if dtype == np.int64 else List[float]
    t1 = table_from_pandas(df).with_columns(
        array=pw.declare_type(new_dtype, pw.this.array)
    )
    t1 = t1.flatten(t1.array, t1.other)
    expected = table_from_pandas(expected_df)
    assert_table_equality_wo_index(t1, expected)


@pytest.mark.parametrize("dtype", [np.int64, np.float64])
def test_flatten_multidimensional(dtype: Any):
    df = pd.DataFrame(
        {
            "array": [
                np.array([[1, 2], [3, 4]], dtype=dtype),
                np.array([[1, 2, 5, 6]], dtype=dtype),
            ]
        }
    )
    expected_rows = [
        np.array([1, 2], dtype=dtype),
        np.array([3, 4], dtype=dtype),
        np.array([1, 2, 5, 6], dtype=dtype),
    ]
    t = table_from_pandas(df)
    t = t.flatten(t.array)
    t_pandas = table_to_pandas(t)
    assert len(expected_rows) == len(t_pandas)
    for expected_row in expected_rows:
        found_equal = False
        for t_row in t_pandas.itertuples():
            if t_row.array.shape != expected_row.shape:
                continue
            if (t_row.array == expected_row).all():
                found_equal = True
                break
        assert found_equal


def test_flatten_string():
    df = pd.DataFrame({"string": ["abc", "defoimkm", "xyz"], "other": [0, 1, 2]})
    t1 = pw.debug.table_from_pandas(df)
    t1 = t1.update_types(string=str)
    t1 = t1.flatten(t1.string)
    df_expected = pd.DataFrame({"string": list("abcdefoimkmxyz")})
    expected = table_from_pandas(df_expected)
    assert_table_equality_wo_index(t1, expected)


@pytest.mark.parametrize("mul", [1, -2])
@pytest.mark.parametrize("dtype", [np.int64, np.float64])
def test_flatten_explode(mul: int, dtype: Any):
    mul = dtype(mul)
    df = pd.DataFrame(
        {
            "array": [
                np.array([1, 2], dtype=dtype),
                np.array([], dtype=dtype),
                np.array([3, 4], dtype=dtype),
                np.array([10, 11, 12], dtype=dtype),
                np.array([4, 5, 6, 1, 2], dtype=dtype),
            ],
            "other": [-1, -2, -3, -4, -5],
        }
    )
    expected_df = pd.DataFrame(
        {
            "array": [1, 2, 3, 4, 10, 11, 12, 4, 5, 6, 1, 2],
            "other": np.array([-1, -1, -3, -3, -4, -4, -4, -5, -5, -5, -5, -5]) * mul,
        },
        dtype=dtype,
    )
    t1 = table_from_pandas(df).with_columns(
        array=pw.declare_type(
            {np.int64: List[int], np.float64: List[float]}[dtype], pw.this.array
        )
    )
    t1 = t1.flatten(
        t1.array,
        other=mul * pw.cast({np.int64: int, np.float64: float}[dtype], t1.other),
    )
    expected = table_from_pandas(expected_df)
    assert_table_equality_wo_index(t1, expected)


def test_flatten_incorrect_type():
    t = T(
        """
         | a | other
      0  | 1 | -1
      1  | 2 | -2
      2  | 3 | -3
    """
    )
    with pytest.raises(
        TypeError,
        match=re.escape("Cannot flatten column <table1>.a of type <class 'int'>."),
    ):
        t = t.flatten(t.a)


def test_from_columns():
    first = T(
        """
    | pet | owner | age
    1 |  1  | Alice | 10
    2 |  1  | Bob   | 9
    3 |  2  | Alice | 8
    """
    )
    second = T(
        """
    | foo | aux | baz
    1 | a   | 70  | a
    2 | b   | 80  | c
    3 | c   | 90  | b
    """
    ).with_universe_of(first)
    expected = T(
        """
    | pet | foo
    1 | 1   | a
    2 | 1   | b
    3 | 2   | c
        """
    )
    assert_table_equality(pw.Table.from_columns(first.pet, second.foo), expected)


def test_from_columns_collision():
    first = T(
        """
    | pet | owner | age
    1 |  1  | Alice | 10
    2 |  1  | Bob   | 9
    3 |  2  | Alice | 8
    """
    )
    with pytest.raises(ValueError):
        pw.Table.from_columns(first.pet, first.pet)


def test_from_columns_mismatched_keys():
    first = T(
        """
    | pet | owner | age
    1 |  1  | Alice | 10
    2 |  1  | Bob   | 9
    3 |  2  | Alice | 8
    """
    )
    second = T(
        """
    | foo | aux | baz
    1 | a   | 70  | a
    2 | b   | 80  | c
    4 | c   | 90  | b
    """
    )
    with pytest.raises(ValueError):
        pw.Table.from_columns(first.pet, second.foo)


def test_rename_columns_1():
    old = T(
        """
      | pet  |  owner  | age
    1 |  1   | Alice   | 10
    2 |  1   | Bob     | 9
    """
    )

    expected = T(
        """
       |  owner  | animal | winters
    1  | Alice   |  1     | 10
    2  | Bob     |  1     | 9
    """
    )
    new = old.rename_columns(animal=old.pet, winters=old.age)
    assert_table_equality(new, expected)


def test_rename_columns_2():
    old = T(
        """
      | pet | age
    1 |  1  | 10
    2 |  1  | 9
    """
    )
    expected = T(
        """
      | age | pet
    1 |  1  | 10
    2 |  1  | 9
    """
    )
    new = old.rename_columns(age="pet", pet="age")
    assert_table_equality(new, expected)


def test_rename_by_dict():
    old = T(
        """
        | t0  |  t1  | t2
    1 |  1   | Alice   | 10
    2 |  1   | Bob     | 9
    """
    )

    expected = T(
        """
        |  col_0  | col_1 | col_2
    1 |  1   | Alice   | 10
    2 |  1   | Bob     | 9
    """
    )
    new = old.rename_by_dict({f"t{i}": f"col_{i}" for i in range(3)})
    assert_table_equality(new, expected)


def test_rename_with_dict():
    old = T(
        """
        | t0  |  t1  | t2
    1 |  1   | Alice   | 10
    2 |  1   | Bob     | 9
    """
    )
    mapping = {f"t{i}": f"col_{i}" for i in range(3)}
    new = old.rename(mapping)
    expected = old.rename_by_dict(mapping)
    assert_table_equality(new, expected)


def test_rename_with_kwargs():
    old = T(
        """
        | pet  |  owner  | age
    1 |  1   | Alice   | 10
    2 |  1   | Bob     | 9
    """
    )

    new = old.rename(animal=old.pet, winters=old.age)
    expected = old.rename_columns(animal=old.pet, winters=old.age)
    assert_table_equality(new, expected)


def test_rename_columns_unknown_column_name():
    old = T(
        """
    | pet |  owner  | age
    1 |  1  | Alice   | 10
    2 |  1  | Bob     | 9
    """
    )
    with pytest.raises(Exception):
        old.rename_columns(pet="animal", habitat="location")


def test_drop_columns():
    old = T(
        """
    | pet | owner | age | weight
    1 | 1   | Bob   | 11  | 7
    2 | 1   | Eve   | 10  | 11
    3 | 2   | Eve   | 15  | 13
    """
    )
    new = old.without(old.pet, old.age, pw.this.owner)
    expected = T(
        """
    | weight
    1 | 7
    2 | 11
    3 | 13
    """
    )
    assert_table_equality(new, expected)


def test_filter():
    t_latin = T(
        """
            | lower | upper
        1  | a     | A
        2  | b     | B
        26 | z     | Z
        """
    )
    t_tmp = T(
        """
            | bool
        1   | True
        2   | True
        26  | False
        """
    ).with_universe_of(t_latin)

    res = t_latin.filter(t_tmp["bool"])

    assert_table_equality(
        res,
        T(
            """
                | lower | upper
            1  | a     | A
            2  | b     | B
            """
        ),
    )


def test_filter_no_columns():
    input = T(
        """
            |
        1   |
        2   |
        3   |
        """
    ).select()

    output = input.filter(input.id == input.id)

    assert_table_equality(
        output,
        T(
            """
                |
            1   |
            2   |
            3   |
            """
        ).select(),
    )


def test_filter_different_universe():
    t_latin = T(
        """
            | lower | upper
        1  | a     | A
        2  | b     | B
        26 | z     | Z
        """
    )
    t_wrong = T(
        """
            | bool
        1   | True
        7   | False
        """
    )

    with pytest.raises(ValueError):
        t_latin.filter(t_wrong.bool)


def test_reindex():
    t1 = T(
        """
            | col
        1   | 11
        2   | 12
        3   | 13
        """
    )
    t2 = T(
        """
        | new_id
    1  | 2
    2  | 3
    3  | 4
    """
    ).select(new_id=t1.pointer_from(pw.this.new_id))
    pw.universes.promise_is_subset_of(t1, t2)
    assert_table_equality(
        t1.with_id(t2.new_id),
        T(
            """
                | col
            2   | 11
            3   | 12
            4   | 13
            """
        ),
    )
    with pytest.raises(TypeError):
        # must be column val
        t1.with_id(t1.id + 1),
    with pytest.raises(ValueError):
        # old style is not supported
        t1.select(id=t2.new_id),


def test_reindex_no_columns():
    t1 = T(
        """
            |
        1   |
        2   |
        3   |
        """
    ).select()
    t2 = T(
        """
            | new_id
        1   | 2
        2   | 3
        3   | 4
        """
    ).select(new_id=t1.pointer_from(pw.this.new_id))
    pw.universes.promise_is_subset_of(t1, t2)

    assert_table_equality(
        t1.with_id(t2.new_id),
        T(
            """
                |
            2   |
            3   |
            4   |
            """
        ).select(),
    )


def test_column_fixpoint():
    def collatz_transformer(iterated):
        def collatz_step(x: float) -> float:
            if x == 1:
                return 1
            elif x % 2 == 0:
                return x / 2
            else:
                return 3 * x + 1

        new_iterated = iterated.select(val=pw.apply(collatz_step, iterated.val))
        return dict(iterated=new_iterated)

    ret = pw.iterate(
        collatz_transformer,
        iterated=table_from_pandas(
            pd.DataFrame(index=range(1, 101), data={"val": np.arange(1.0, 101.0)})
        ),
    ).iterated
    expected_ret = table_from_pandas(
        pd.DataFrame(index=range(1, 101), data={"val": 1.0})
    )

    assert_table_equality(ret, expected_ret)


# FIXME: uses pointer != float due to annotated return type of min_int
def test_rows_fixpoint():
    def min_id_remove(iterated: pw.Table):
        min_id_table = iterated.reduce(min_id=pw.reducers.min_int(iterated.id))
        iterated = iterated.filter(
            iterated.id != min_id_table.ix(min_id_table.pointer_from()).min_id
        )
        return dict(iterated=iterated)

    ret = pw.iterate(
        min_id_remove,
        iterated=pw.iterate_universe(
            T(
                """
                | foo
            1   | 1
            2   | 2
            3   | 3
            4   | 4
            5   | 5
            """
            )
        ),
    ).iterated

    expected_ret = T(
        """
            | foo
        """
    ).update_types(foo=int)

    assert_table_equality_wo_index(ret, expected_ret)


# FIXME: uses pointer != float due to annotated return type of min_int
def test_rows_fixpoint_needs_iterate_universe():
    def min_id_remove(iterated: pw.Table):
        min_id_table = iterated.reduce(min_id=pw.reducers.min_int(iterated.id))
        iterated = iterated.filter(
            iterated.id != min_id_table.ix(min_id_table.pointer_from()).min_id
        )
        return dict(iterated=iterated)

    with pytest.raises(ValueError):
        pw.iterate(
            min_id_remove,
            iterated=T(
                """
                    | foo
                1   | 1
                2   | 2
                3   | 3
                4   | 4
                5   | 5
                """
            ),
        ).iterated


def test_iteration_column_order():
    def iteration_step(iterated):
        iterated = iterated.select(bar=iterated.bar, foo=iterated.foo - iterated.foo)
        return dict(iterated=iterated)

    ret = pw.iterate(
        iteration_step,
        iterated=T(
            """
                | foo   | bar
            1   | 1     | None
            2   | 2     | None
            3   | 3     | None
            """
        ),
    ).iterated

    expected_ret = T(
        """
            | foo   | bar
        1   | 0     | None
        2   | 0     | None
        3   | 0     | None
        """
    )

    assert_table_equality_wo_index(ret, expected_ret)


@pytest.mark.parametrize("limit", [-1, 0])
def test_iterate_with_wrong_limit(limit):
    def iteration_step(iterated):
        iterated = iterated.select(foo=iterated.foo + 1)
        return dict(iterated=iterated)

    with pytest.raises(ValueError):
        pw.iterate(
            iteration_step,
            iteration_limit=limit,
            iterated=T(
                """
                    | foo
                1   | 0
                """
            ),
        ).iterated


@pytest.mark.parametrize("limit", [1, 2, 10])
def test_iterate_with_limit(limit):
    def iteration_step(iterated):
        iterated = iterated.select(foo=iterated.foo + 1)
        return dict(iterated=iterated)

    ret = pw.iterate(
        iteration_step,
        iteration_limit=limit,
        iterated=T(
            """
                | foo
            1   | 0
            """
        ),
    ).iterated

    expected_ret = T(
        f"""
            | foo
        1   | {limit}
        """
    )

    assert_table_equality(ret, expected_ret)


def test_apply():
    a = T(
        """
            | foo
        1   | 1
        2   | 2
        3   | 3
        """
    )

    def inc(x: int) -> int:
        return x + 1

    result = a.select(ret=pw.apply(inc, a.foo))

    assert_table_equality(
        result,
        T(
            """
                | ret
            1   | 2
            2   | 3
            3   | 4
            """
        ),
    )


def test_apply_inspect_wrapped_signature():
    a = T(
        """
            | foo
        1   | 1
        2   | 2
        3   | 3
        """
    )

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    @decorator
    def inc(x: int) -> int:
        return x + 1

    result = a.select(ret=pw.apply(inc, a.foo))

    assert_table_equality(
        result,
        T(
            """
                | ret
            1   | 2
            2   | 3
            3   | 4
            """
        ),
    )


def test_apply_consts():
    a = T(
        """
            | foo
        1   | 1
        2   | 2
        3   | 3
        """
    )

    def inc(x: int) -> int:
        return x + 1

    result = a.select(ret=pw.apply(inc, 1))

    assert_table_equality(
        result,
        T(
            """
                | ret
            1 | 2
            2 | 2
            3 | 2
            """
        ),
    )


def test_apply_more_args():
    a = T(
        """
            | foo
        1 | 1
        2 | 2
        3 | 3
        """
    )
    b = T(
        """
            | bar
        1 | 2
        2 | -1
        3 | 4
        """
    ).with_universe_of(a)

    def add(x: int, y: int) -> int:
        return x + y

    result = a.select(ret=pw.apply(add, x=a.foo, y=b.bar))

    assert_table_equality(
        result,
        T(
            """
                | ret
            1 | 3
            2 | 1
            3 | 7
            """
        ),
    )


@xfail_no_numba
def test_numba_apply():
    a = T(
        """
            | foo
        1 | 1
        2 | 2
        3 | 3
        """,
    )
    b = T(
        """
            | bar
        1 | 2
        2 | -1
        3 | 4
        """,
    ).with_universe_of(a)

    def add(x, y):
        return x + y

    expression = pw.numba_apply(add, "int64(int64,int64)", a.foo, b.bar)
    assert isinstance(expression, NumbaApplyExpression)

    result = a.select(ret=expression)

    assert_table_equality(
        result,
        T(
            """
                | ret
            1 | 3
            2 | 1
            3 | 7
            """,
        ),
    )


@xfail_no_numba
def test_numba_apply_lambda():
    a = T(
        """
            | foo
        1 | 1
        2 | 2
        3 | 3
        """,
    )
    b = T(
        """
            | bar
        1 | 2
        2 | -1
        3 | 4
        """,
    ).with_universe_of(a)

    expression = pw.numba_apply(lambda x, y: x + y, "int64(int64,int64)", a.foo, b.bar)

    assert isinstance(expression, NumbaApplyExpression)
    result = a.select(ret=expression)

    assert_table_equality(
        result,
        T(
            """
                | ret
            1 | 3
            2 | 1
            3 | 7
            """,
        ),
    )


@xfail_no_numba
def test_numba_composite():
    a = T(
        """
            | foo
        1 | 1
        2 | 2
        3 | 3
        """,
    )
    b = T(
        """
            | bar
        1 | 2
        2 | -1
        3 | 4
        """,
    ).with_universe_of(a)

    result = a.select(
        ret=pw.numba_apply(lambda x, y: x + y, "int64(int64,int64)", a.foo - 1, 1)
        + b.bar
    )

    assert_table_equality(
        result,
        T(
            """
              | ret
            1 | 3
            2 | 1
            3 | 7
            """,
        ),
    )


@xfail_no_numba
def test_numba_more_signatures():
    a = T(
        """
            | foo
        1 | 1
        2 | 2
        3 | 3
        """,
    )

    result = a.select(ret=pw.numba_apply(lambda x: x + 0.5, "float64(int64,)", a.foo))

    assert_table_equality(
        result,
        T(
            """
                | ret
            1 | 1.5
            2 | 2.5
            3 | 3.5
            """,
        ),
    )


def test_apply_incompatible_keys():
    a = T(
        """
            | foo
        1   | 1
        2   | 2
        3   | 3
        """
    )
    b = T(
        """
            | bar
        1   | 2
        """
    )

    def add(x: float, y: float) -> float:
        return x + y

    with pytest.raises(ValueError):
        a.select(ret=pw.apply(add, x=a.foo, y=b.bar))


def test_apply_wrong_number_of_args():
    a = T(
        """
            | foo
        1 | 1
        2 | 2
        """
    )

    def add(x: float, y: float) -> float:
        return x + y

    with pytest.raises(AssertionError):
        a.select(ret=pw.apply(add))


def test_apply_async():
    import asyncio

    async def inc(a: int) -> int:
        await asyncio.sleep(0.1)
        return a + 1

    input = pw.debug.table_from_markdown(
        """
            | a
        1   | 1
        2   | 2
        3   | 3
        """
    )

    result = input.select(ret=pw.apply_async(inc, pw.this.a))

    assert_table_equality(
        result,
        T(
            """
              | ret
            1 | 2
            2 | 3
            3 | 4
            """,
        ),
    )


def test_apply_async_more_args():
    import asyncio

    async def add(a: int, b: int, *, c: int) -> int:
        await asyncio.sleep(0.1)
        return a + b + c

    input = pw.debug.table_from_markdown(
        """
            | a | b  | c
        1   | 1 | 10 | 100
        2   | 2 | 20 | 200
        3   | 3 | 30 | 300
        """
    )

    result = input.select(ret=pw.apply_async(add, pw.this.a, pw.this.b, c=pw.this.c))

    assert_table_equality(
        result,
        T(
            """
              | ret
            1 | 111
            2 | 222
            3 | 333
            """,
        ),
    )


def test_apply_async_wrong_args():
    import asyncio

    async def add(a: int, b: int, *, c: int) -> int:
        await asyncio.sleep(0.1)
        return a + b + c

    input = pw.debug.table_from_markdown(
        """
            | a | b  | c
        1   | 1 | 10 | 100
        2   | 2 | 20 | 200
        3   | 3 | 30 | 300
        """
    )

    with pytest.raises(TypeError):
        result = input.select(ret=pw.apply_async(add, pw.this.a, pw.this.b, pw.this.c))

        assert_table_equality(
            result,
            T(
                """
                | ret
                1 | 111
                2 | 222
                3 | 333
                """,
            ),
        )


def test_apply_async_coerce_async():
    a = T(
        """
            | foo
        1   | 1
        2   | 2
        3   | 3
        """
    )

    def inc(x: int) -> int:
        return x + 1

    result = a.select(ret=pw.apply_async(inc, a.foo))

    assert_table_equality(
        result,
        T(
            """
                | ret
            1   | 2
            2   | 3
            3   | 4
            """
        ),
    )


def test_apply_async_disk_cache(tmp_path: pathlib.Path):
    cache_dir = tmp_path / "test_cache"
    os.environ["PATHWAY_PERSISTENT_STORAGE"] = str(cache_dir)

    counter = mock.Mock()

    @pw.asynchronous.async_options(cache_strategy=pw.asynchronous.DiskCache())
    def inc(x: int) -> int:
        counter()
        return x + 1

    input = T(
        """
            | foo
        1   | 1
        2   | 2
        3   | 3
        """
    )
    result = input.select(ret=pw.apply_async(inc, pw.this.foo))
    expected = T(
        """
            | ret
        1   | 2
        2   | 3
        3   | 4
        """
    )

    # run twice to check if cache is used
    assert_table_equality(result, expected)
    assert_table_equality(result, expected)
    assert os.path.exists(cache_dir)
    assert counter.call_count == 3


def test_udf_async():
    import asyncio

    @pw.udf_async
    async def inc(a: int) -> int:
        await asyncio.sleep(0.1)
        return a + 1

    input = pw.debug.table_from_markdown(
        """
            | a
        1   | 1
        2   | 2
        3   | 3
        """
    )

    result = input.select(ret=inc(pw.this.a))

    assert_table_equality(
        result,
        T(
            """
              | ret
            1 | 2
            2 | 3
            3 | 4
            """,
        ),
    )


def test_udf_async_options(tmp_path: pathlib.Path):
    cache_dir = tmp_path / "test_cache"
    os.environ["PATHWAY_PERSISTENT_STORAGE"] = str(cache_dir)

    counter = mock.Mock()

    @pw.udf_async(cache_strategy=pw.asynchronous.DiskCache())
    async def inc(x: int) -> int:
        counter()
        return x + 1

    input = T(
        """
            | foo
        1   | 1
        2   | 2
        3   | 3
        """
    )
    result = input.select(ret=inc(pw.this.foo))
    expected = T(
        """
            | ret
        1   | 2
        2   | 3
        3   | 4
        """
    )

    # run twice to check if cache is used
    assert_table_equality(result, expected)
    assert_table_equality(result, expected)
    assert os.path.exists(cache_dir)
    assert counter.call_count == 3


def test_empty_join():
    left = T(
        """
                col | on
            1 | a   | 11
            2 | b   | 12
            3 | c   | 13
        """
    )
    right = T(
        """
                col | on
            1 | d   | 12
            2 | e   | 13
            3 | f   | 14
        """,
    )
    joined = left.join(right, left.on == right.on).select()
    assert_table_equality_wo_index(
        joined,
        T(
            """
                |
            2   |
            3   |
            """
        ).select(),
    )


def test_join_left_assign_id():
    left = T(
        """
                col | on
            1 | a   | 11
            2 | b   | 12
            3 | c   | 13
            4 | d   | 13
        """
    )
    right = T(
        """
                col | on
            1 | d   | 12
            2 | e   | 13
            3 | f   | 14
        """,
    )
    joined = left.join(right, left.on == right.on, id=left.id).select(
        lcol=left.col, rcol=right.col
    )

    assert_table_equality(
        joined,
        T(
            """
        | lcol | rcol
        2 |  b |    d
        3 |  c |    e
        4 |  d |    e
    """
        ),
    )

    with pytest.raises(AssertionError):
        left.join(right, left.on == right.on, id=left.on)

    left.join(right, left.on == right.on, id=right.id).select(
        lcol=left.col, rcol=right.col
    )
    with pytest.raises(KeyError):
        run_all()


def test_join_right_assign_id():
    left = T(
        """
                col | on
            1 | a   | 11
            2 | b   | 12
            3 | c   | 13
        """
    )
    right = T(
        """
                col | on
            0 | c   | 12
            1 | d   | 12
            2 | e   | 13
            3 | f   | 14
        """,
    )
    joined = left.join(right, left.on == right.on, id=right.id).select(
        lcol=left.col, rcol=right.col
    )
    assert_table_equality(
        joined,
        T(
            """
          | lcol | rcol
        0 |    b |    c
        1 |    b |    d
        2 |    c |    e
    """
        ),
    )

    with pytest.raises(AssertionError):
        left.join(right, left.on == right.on, id=right.on)

    left.join(right, left.on == right.on, id=left.id).select(
        lcol=left.col, rcol=right.col
    )
    with pytest.raises(KeyError):
        run_all()


def test_join():
    t1 = T(
        """
            | pet | owner | age
        1   |   1 | Alice |  10
        2   |   1 |   Bob |   9
        3   |   2 | Alice |   8
        """
    )
    t2 = T(
        """
            | pet | owner | age | size
        11  |   3 | Alice |  10 |    M
        12  |   1 |   Bob |   9 |    L
        13  |   1 |   Tom |   8 |   XL
        """
    )
    expected = T(
        """
            owner_name | L | R  | age
            Bob        | 2 | 12 |   9
            """,
    ).with_columns(
        L=t1.pointer_from(pw.this.L),
        R=t2.pointer_from(pw.this.R),
    )
    res = t1.join(t2, t1.pet == t2.pet, t1.owner == t2.owner).select(
        owner_name=t2.owner, L=t1.id, R=t2.id, age=t1.age
    )
    assert_table_equality_wo_index(
        res,
        expected,
    )


def test_join_swapped_condition():
    t1 = T(
        """
            | pet | owner | age
        1   |   1 | Alice |  10
        2   |   1 |   Bob |   9
        3   |   2 | Alice |   8
        """
    )
    t2 = T(
        """
            | pet | owner | age | size
        1   |   3 | Alice |  10 |    M
        2   |   1 |   Bob |   9 |    L
        3   |   1 |   Tom |   8 |   XL
        """
    )
    # ensure we are not testing case with completely messed up universes
    t1.with_universe_of(t2)
    with pytest.raises(ValueError):
        t1.join(t2, t2.pet == t1.pet).select(
            owner_name=t2.owner, L=t1.id, R=t2.id, age=t1.age
        )


@pytest.mark.parametrize(
    "op",
    [
        operator.ne,
        operator.lt,
        operator.gt,
        operator.le,
        operator.ge,
    ],
)
def test_join_illegal_operator_in_condition(op):
    t1 = T(
        """
            | pet | owner | age
        1   |   1 | Alice |  10
        2   |   1 |   Bob |   9
        3   |   2 | Alice |   8
        """
    )
    t2 = T(
        """
            | pet | owner | age | size
        11  |   3 | Alice |  10 |    M
        12  |   1 |   Bob |   9 |    L
        13  |   1 |   Tom |   8 |   XL
        """
    )
    with pytest.raises(ValueError):
        t1.join(t2, op(t1.pet, t2.pet))


def test_join_default():
    t1 = T(
        """
            | pet | owner | age
        1   |   1 | Alice |  10
        2   |   1 |   Bob |   9
        3   |   2 | Alice |   8
        """
    )
    t2 = T(
        """
            | pet | owner | age | size
        11  |   3 | Alice |  10 |    M
        12  |   1 |   Bob |   9 |    L
        13  |   1 |   Tom |   8 |   XL
        """
    )
    res = t1.join(t2, t1.pet == t2.pet).select(
        owner_name=t2.owner, L=t1.id, R=t2.id, age=t1.age
    )
    expected = T(
        """
            owner_name  | L | R  | age
            Bob         | 1 | 12 | 10
            Tom         | 1 | 13 | 10
            Bob         | 2 | 12 |  9
            Tom         | 2 | 13 |  9
        """,
    ).with_columns(
        L=t1.pointer_from(pw.this.L),
        R=t2.pointer_from(pw.this.R),
    )

    assert_table_equality_wo_index(res, expected)


def test_join_self():
    input = T(
        """
            | foo   | bar
        1   | 1     | 1
        2   | 1     | 2
        3   | 1     | 3
        """
    )
    with pytest.raises(Exception):
        input.join(input, input.foo == input.bar)


def test_join_select_no_columns():
    left = T(
        """
            | a
        1  | 1
        2  | 2
        """
    )
    right = T(
        """
            | b
        1  | foo
        2  | bar
        """
    )

    ret = left.join(right, left.id == right.id).select().select(col=42)
    assert_table_equality_wo_index(
        ret,
        T(
            """
                | col
            1   | 42
            2   | 42
            """
        ),
    )


def test_cross_join():
    t1 = T(
        """
            | pet | owner | age
        1   |   1 | Alice |  10
        2   |   1 |   Bob |   9
        3   |   2 | Alice |   8
        """
    )
    t2 = T(
        """
            | pet | owner | age | size
        11  |   3 | Alice |  10 |    M
        12  |   1 |   Bob |  9  |    L
        13  |   1 |   Tom |  8  |   XL
        """
    )
    res = t1.join(t2).select(owner_name=t2.owner, L=t1.id, R=t2.id, age=t1.age)
    expected = T(
        """
            owner_name  | L | R | age
            Alice       | 1 | 11 |  10
            Bob         | 1 | 12 |  10
            Tom         | 1 | 13 |  10
            Alice       | 2 | 11 |   9
            Bob         | 2 | 12 |   9
            Tom         | 2 | 13 |   9
            Alice       | 3 | 11 |   8
            Bob         | 3 | 12 |   8
            Tom         | 3 | 13 |   8
        """,
    ).with_columns(
        L=t1.pointer_from(pw.this.L),
        R=t2.pointer_from(pw.this.R),
    )
    assert_table_equality_wo_index(res, expected)


def test_empty_join_2():
    t1 = T(
        """
        v1
        1
        2
        """,
    )
    t2 = T(
        """
        v2
        10
        20
        """,
    )
    t = t1.join(t2).select(t1.v1, t2.v2)
    expected_t = T(
        """
        v1  | v2
        1   | 10
        1   | 20
        2   | 10
        2   | 20
        """,
    )
    assert_table_equality_wo_index(t, expected_t)


def test_ix():
    t_animals = T(
        """
            | genus      | epithet
        1   | upupa      | epops
        2   | acherontia | atropos
        3   | bubo       | scandiacus
        4   | dynastes   | hercules
        """
    )
    t_birds = T(
        """
            | desc   | ptr
        1   | hoopoe | 2
        2   | owl    | 4
        """
    ).with_columns(ptr=t_animals.pointer_from(pw.this.ptr))

    res = t_birds.select(latin=t_animals.ix(t_birds.ptr).genus)
    expected = T(
        """
            | latin
        1   | acherontia
        2   | dynastes
        """
    )
    assert_table_equality(res, expected)


def test_ix_none():
    t_animals = T(
        """
            | genus      | epithet
        1   | upupa      | epops
        2   | acherontia | atropos
        3   | bubo       | scandiacus
        4   | dynastes   | hercules
        """
    )
    t_birds = T(
        """
            | desc   | ptr
        1   | hoopoe | 2
        2   | owl    | 4
        3   | brbrb  |
        """
    ).with_columns(ptr=t_animals.pointer_from(pw.this.ptr, optional=True))

    res = t_birds.select(latin=t_animals.ix(t_birds.ptr, optional=True).genus)
    expected = T(
        """
            | latin
        1   | acherontia
        2   | dynastes
        3   |
        """
    )
    assert_table_equality(res, expected)


def test_ix_missing_key():
    t_animals = T(
        """
            | genus      | epithet
        1   | upupa      | epops
        2   | acherontia | atropos
        """
    )
    t_birds = T(
        """
            | desc   | ptr
        1   | hoopoe | 1
        2   | owl    | 3
        """
    ).with_columns(ptr=t_animals.pointer_from(pw.this.ptr))
    t_birds.select(latin=t_animals.ix(t_birds.ptr).genus)
    with pytest.raises(KeyError):
        run_all()


def test_ix_none_in_source():
    t_animals = T(
        """
            | genus      | epithet
        1   | upupa      | epops
        2   | acherontia | atropos
        3   | bubo       | scandiacus
        4   |            | hercules
        """
    )
    t_birds = T(
        """
            | desc   | ptr
        1   | hoopoe | 2
        2   | owl    | 4
        """
    ).with_columns(ptr=t_animals.pointer_from(pw.this.ptr))

    res = t_birds.select(latin=t_animals.ix(t_birds.ptr).genus)
    expected = T(
        """
            | latin
        1   | acherontia
        2   |
        """
    )
    assert_table_equality(res, expected)


def test_ix_self_select():
    input = T(
        """
            | foo   | bar
        1   | 1     | 4
        2   | 1     | 5
        3   | 2     | 6
        """
    ).with_columns(foo=pw.this.pointer_from(pw.this.foo))

    result = input.select(result=input.ix(input.foo).bar)

    assert_table_equality(
        result,
        T(
            """
                | result
            1   | 4
            2   | 4
            3   | 5
            """
        ),
    )


def test_groupby_simplest():
    left = T(
        """
        | pet  |  owner  | age
    1 | dog  | Alice   | 10
    2 | dog  | Bob     | 9
    3 | cat  | Alice   | 8
    4 | dog  | Bob     | 7
    """
    )

    left_res = left.groupby(left.pet).reduce(left.pet)

    assert_table_equality_wo_index(
        left_res,
        T(
            """
          | pet
        1 | dog
        2 | cat
    """
        ),
    )


def test_groupby_singlecol():
    left = T(
        """
        | pet  |  owner  | age
    1 | dog  | Alice   | 10
    2 | dog  | Bob     | 9
    3 | cat  | Alice   | 8
    4 | dog  | Bob     | 7
    """
    )

    left_res = left.groupby(left.pet).reduce(left.pet, ageagg=pw.reducers.sum(left.age))

    assert_table_equality_wo_index(
        left_res,
        T(
            """
          | pet  | ageagg
        1 | dog  | 26
        2 | cat  | 8
    """
        ),
    )


def test_groupby_int_sum():
    left = T(
        """
      | owner   | val
    1 | Alice   | 1
    2 | Alice   | -1
    3 | Bob     | 0
    4 | Bob     | 0
    5 | Charlie | 1
    6 | Charlie | 0
    7 | Dee     | 5
    8 | Dee     | 5
    """
    )

    left_res = left.groupby(left.owner).reduce(
        left.owner, val=pw.reducers.int_sum(left.val)
    )

    assert_table_equality_wo_index(
        left_res,
        T(
            """
          | owner   | val
        1 | Alice   | 0
        2 | Bob     | 0
        3 | Charlie | 1
        4 | Dee     | 10
    """
        ),
    )


def test_groupby_filter_singlecol():
    left = T(
        """
        | pet  |  owner  | age
      1 | dog  | Alice   | 10
      2 | dog  | Bob     | 9
      3 | cat  | Alice   | 8
      4 | dog  | Bob     | 7
      5 | cat  | Alice   | 6
      6 | dog  | Bob     | 5
    """
    )

    left_res = (
        left.filter(left.age > 6)
        .groupby(left.pet)
        .reduce(left.pet, ageagg=pw.reducers.sum(left.age))
    )

    assert_table_equality_wo_index(
        left_res,
        T(
            """
          | pet  | ageagg
        1 | dog  | 26
        2 | cat  | 8
    """
        ),
    )


def test_groupby_universes():
    left = T(
        """
        | pet  |  owner
    1 | dog  | Alice
    2 | dog  | Bob
    3 | cat  | Alice
    4 | dog  | Bob
    """
    )

    left_prim = T(
        """
        | age
    1 | 10
    2 | 9
    3 | 8
    4 | 7
    5 | 6
    """
    )

    left_bis = T(
        """
        | age
    1 | 10
    2 | 9
    3 | 8
    """
    )
    pw.universes.promise_is_subset_of(left, left_prim)

    left_res = left.groupby(left.pet).reduce(
        left.pet, ageagg=pw.reducers.sum(left_prim.age)
    )

    assert_table_equality_wo_index(
        left_res,
        T(
            """
        | pet  | ageagg
    1 | dog  | 26
    2 | cat  | 8
    """
        ),
    )

    with pytest.raises(AssertionError):
        left.groupby(left.pet).reduce(ageagg=pw.reducers.sum(left_bis.age))


def test_groupby_reducer_on_expression():
    left = T(
        """
        | pet  |  owner  | age
    1 | dog  | Alice   | 10
    2 | dog  | Bob     | 9
    3 | cat  | Alice   | 8
    4 | dog  | Bob     | 7
    """
    )

    left_res = left.groupby(left.pet).reduce(
        left.pet, ageagg=pw.reducers.min(left.age + left.age)
    )

    assert_table_equality_wo_index(
        left_res,
        T(
            """
        | pet  | ageagg
    1 | dog  | 14
    2 | cat  | 16
    """
        ),
    )


def test_groupby_expression_on_reducers():
    left = T(
        """
        | pet  |  owner  | age
    1 | dog  | Alice   | 10
    2 | dog  | Bob     | 9
    3 | cat  | Alice   | 8
    4 | dog  | Bob     | 7
    """
    )

    left_res = left.groupby(left.pet).reduce(
        left.pet,
        ageagg=pw.reducers.min(left.age) + pw.reducers.sum(left.age),
    )
    assert_table_equality_wo_index(
        left_res,
        T(
            """
        | pet  | ageagg
    1 | dog  | 33
    2 | cat  | 16
    """
        ),
    )


def test_groupby_reduce_no_columns():
    input = T(
        """
            | a
        1  | 1
        2  | 2
        """
    )

    ret = input.reduce().select(col=42)

    assert_table_equality_wo_index(
        ret,
        T(
            """
                | col
            1   | 42
            """
        ),
    )


def test_groupby_mutlicol():
    left = T(
        """
        | pet  |  owner  | age
    1 | dog  | Alice   | 10
    2 | dog  | Bob     | 9
    3 | cat  | Alice   | 8
    4 | dog  | Bob     | 7
    """
    )

    left_res = left.groupby(left.pet, left.owner).reduce(
        left.pet, left.owner, ageagg=pw.reducers.sum(left.age)
    )

    assert_table_equality_wo_index(
        left_res,
        T(
            """
        | pet  |  owner  | ageagg
    1 | dog  | Alice   | 10
    2 | dog  | Bob     | 16
    3 | cat  | Alice   | 8
    """
        ),
    )


def test_groupby_mix_key_val():
    left = T(
        """
        | pet  |  owner  | age
    1 |  1   | Alice   | 10
    2 |  1   | Bob     | 9
    3 |  2   | Alice   | 8
    4 |  1   | Bob     | 7
    """
    )

    left_res = left.groupby(left.pet).reduce(
        left.pet, ageagg=pw.reducers.min(left.age + left.pet)
    )

    right = T(
        """
            | pet | ageagg
        1 | 1   |      8
        2 | 2   |     10
        """
    )
    # right_res = right.with_id_from(right.pet)

    # assert_table_equality(left_res, right_res)

    assert_table_equality_wo_index(left_res, right)


def test_groupby_mix_key_val2():
    left = T(
        """
        | pet  |  owner  | age
    1 |  1   | Alice   | 10
    2 |  1   | Bob     | 9
    3 |  2   | Alice   | 8
    4 |  1   | Bob     | 7
    """
    )

    right = T(
        """
            | pet | ageagg
        1 | 1   |      8
        2 | 2   |     10
        """
    )
    res = right.with_id_from(right.pet)

    assert_table_equality(
        res,
        left.groupby(left.pet).reduce(
            left.pet, ageagg=pw.reducers.min(left.age) + left.pet
        ),
    )

    assert_table_equality(
        res,
        left.groupby(left.pet).reduce(
            left.pet, ageagg=pw.reducers.min(left.age + left.pet)
        ),
    )


def test_groupby_key_expressions():
    left = T(
        """
        | pet  |  owner  | age
    1 |  1   | Alice   | 10
    2 |  1   | Bob     | 9
    3 |  2   | Alice   | 8
    4 |  1   | Bob     | 7
    """
    )

    right = T(
        """
            | pet  | pet2
        1 | 1    | 1
        2 | 2    | 2
        """
    )
    res = right.with_id_from(right.pet)

    assert_table_equality(res, left.groupby(left.pet).reduce(left.pet, pet2=left.pet))

    with pytest.raises(Exception):
        left.groupby(left.pet).reduce(age2=left.age)


def test_groupby_setid():
    left = T(
        """
        | pet  |  owner  | age
    1 |  1   | Alice   | 10
    2 |  1   | Bob     | 9
    3 |  2   | Alice   | 8
    4 |  1   | Bob     | 7
    """
    ).with_columns(pet=pw.this.pointer_from(pw.this.pet))

    res = left.groupby(id=left.pet).reduce(
        left.pet,
        agesum=pw.reducers.sum(left.age),
    )

    expected = T(
        """
            | pet | agesum
        1 | 1   | 26
        2 | 2   | 8
        """
    ).with_columns(pet=left.pointer_from(pw.this.pet))

    assert_table_equality(res, expected)

    with pytest.raises(Exception):
        left.groupby(id=left.pet + 1).reduce(age2=left.age)


def test_groupby_similar_tables():
    a = T(
        """
            | pet  |  owner  | age
        1   | dog  | Alice   | 10
        2   | dog  | Bob     | 9
        3   | cat  | Alice   | 8
        4   | dog  | Bob     | 7
        """
    )
    b = a.select(*pw.this)

    r1 = a.groupby(b.pet).reduce(
        a.pet, agemin=pw.reducers.min(a.age), agemax=pw.reducers.max(b.age)
    )
    r2 = b.groupby(a.pet).reduce(
        b.pet, agemin=pw.reducers.min(b.age), agemax=pw.reducers.max(a.age)
    )

    expected = T(
        """
            | pet | agemin | agemax
        1   | cat | 8      | 8
        2   | dog | 7      | 10
        """,
        id_from=["pet"],
    )

    assert_table_equality(r1, expected)
    assert_table_equality(r2, expected)


def test_argmin_argmax_tie():
    table = T(
        """
        |  name   | age
      2 | Alice   |  18
      1 | Charlie |  18
      3 | Bob     |  18
      4 | David   |  19
      5 | Erin    |  19
      6 | Frank   |  20
    """,
        unsafe_trusted_ids=True,
    )

    res = table.groupby(table.age).reduce(
        table.age,
        min=table.ix(pw.reducers.argmin(table.age)).name,
        max=table.ix(pw.reducers.argmax(table.age)).name,
    )

    expected = T(
        """
          | age |     min |     max
        1 |  18 | Charlie | Charlie
        2 |  19 | David   | David
        3 |  20 | Frank   | Frank
        """
    )

    assert_table_equality_wo_index(res, expected)


def test_avg_reducer():
    t1 = T(
        """
      |  owner  | age
    1 | Alice   | 10
    2 | Bob     | 5
    3 | Alice   | 20
    4 | Bob     | 10
    """
    )
    res = t1.groupby(pw.this.owner).reduce(
        pw.this.owner, avg=pw.reducers.avg(pw.this.age)
    )

    expected = T(
        """
        | owner | avg
    1 |  Alice  | 15
    2 |  Bob    | 7.5
    """
    )
    assert_table_equality_wo_index(res, expected)


def test_difference():
    t1 = T(
        """
            | col
        1   | 11
        2   | 12
        3   | 13
        """
    )
    t2 = T(
        """
            | col
        2   | 11
        3   | 11
        4   | 11
        """
    )

    assert_table_equality(
        t1.difference(t2),
        T(
            """
                | col
            1   | 11
            """
        ),
    )


def test_intersect():
    t1 = T(
        """
            | col
        1   | 11
        2   | 12
        3   | 13
        """
    )
    t2 = T(
        """
            | col
        2   | 11
        3   | 11
        4   | 11
        """
    )

    assert_table_equality(
        t1.intersect(t2),
        T(
            """
                | col
            2   | 12
            3   | 13
            """
        ),
    )


def test_intersect_many_tables():
    t1 = T(
        """
            | col
        1   | 11
        2   | 12
        3   | 13
        4   | 14
        """
    )
    t2 = T(
        """
            | col
        2   | 11
        3   | 11
        4   | 11
        5   | 11
        """
    )
    t3 = T(
        """
            | col
        1   | 11
        3   | 11
        4   | 11
        5   | 11
        """
    )

    assert_table_equality(
        t1.intersect(t2, t3),
        T(
            """
                | col
            3   | 13
            4   | 14
            """
        ),
    )


def test_intersect_no_columns():
    t1 = T(
        """
            |
        1   |
        2   |
        3   |
        """
    ).select()
    t2 = T(
        """
            |
        2   |
        3   |
        4   |
        """
    ).select()

    assert_table_equality(
        t1.intersect(t2),
        T(
            """
                |
            2   |
            3   |
            """
        ).select(),
    )


def test_update_cells():
    old = T(
        """
            | pet  |  owner  | age
        1   |  1   | Alice   | 10
        2   |  1   | Bob     | 9
        3   |  2   | Alice   | 8
        4   |  1   | Bob     | 7
        """
    )
    update = T(
        """
            | owner  | age
        1   | Eve    | 10
        4   | Eve    | 3
        """
    )
    expected = T(
        """
            | pet  |  owner  | age
        1   |  1   | Eve     | 10
        2   |  1   | Bob     | 9
        3   |  2   | Alice   | 8
        4   |  1   | Eve     | 3
        """
    ).with_universe_of(old)
    pw.universes.promise_is_subset_of(update, old)

    new = old.update_cells(update)
    assert_table_equality(new, expected)
    assert_table_equality(old << update, expected)


def test_update_cells_0_rows():
    old = T(
        """
            | pet  |  owner  | age
        """
    )
    update = T(
        """
            | owner  | age
        """
    )
    pw.universes.promise_is_subset_of(update, old)
    expected = T(
        """
            | pet  |  owner  | age
        """
    ).with_universe_of(old)

    assert_table_equality(old.update_cells(update), expected)
    assert_table_equality(old << update, expected)


def test_update_cells_ids_dont_match():
    old = T(
        """
            | pet  |  owner  | age
        1   |  1   | Alice   | 10
        2   |  1   | Bob     | 9
        3   |  2   | Alice   | 8
        4   |  1   | Bob     | 7
        """
    )
    update = T(
        """
            | pet  |  owner  | age
        5   |  0   | Eve     | 10
        """
    )
    with pytest.raises(Exception):
        old.update_cells(update)


def test_update_rows():
    old = T(
        """
            | pet  |  owner  | age
        1   |  1   | Alice   | 10
        2   |  1   | Bob     | 9
        3   |  2   | Alice   | 8
        4   |  1   | Bob     | 7
        """
    )
    update = T(
        """
            | pet |  owner  | age
        1   | 7   | Bob     | 11
        5   | 0   | Eve     | 10
        """
    )
    expected = T(
        """
            | pet  |  owner  | age
        1   |  7   | Bob     | 11
        2   |  1   | Bob     | 9
        3   |  2   | Alice   | 8
        4   |  1   | Bob     | 7
        5   |  0   | Eve     | 10
        """
    )

    new = old.update_rows(update)
    assert_table_equality(new, expected)


def test_update_rows_no_columns():
    old = T(
        """
            |
        1   |
        2   |
        3   |
        4   |
        """
    ).select()
    update = T(
        """
            |
        1   |
        5   |
        """
    ).select()
    expected = T(
        """
            |
        1   |
        2   |
        3   |
        4   |
        5   |
        """
    ).select()
    new = old.update_rows(update)
    assert_table_equality(new, expected)


def test_update_rows_0_rows():
    old = T(
        """
            | pet  |  owner  | age
        """
    )
    update = T(
        """
            | pet |  owner  | age
        """
    )

    expected = T(
        """
            | pet  |  owner  | age
        """
    )
    assert_table_equality(old.update_rows(update), expected)


def test_update_rows_columns_dont_match():
    old = T(
        """
            | pet  |  owner  | age
        1   |  1   | Alice   | 10
        2   |  1   | Bob     | 9
        3   |  2   | Alice   | 8
        4   |  1   | Bob     | 7
        """
    )
    update = T(
        """
            | pet  |  owner  | age | weight
        5   |  0   | Eve     | 10  | 42
        """
    )
    with pytest.raises(Exception):
        old.update_rows(update)


def test_with_columns():
    old = T(
        """
            | pet | owner | age
        1   |  1  | Alice | 10
        2   |  1  | Bob   | 9
        3   |  2  | Alice | 8
        """
    )
    update = T(
        """
            | owner | age | weight
        1   | Bob   | 11  | 7
        2   | Eve   | 10  | 11
        3   | Eve   | 15  | 13
        """
    ).with_universe_of(old)
    expected = T(
        """
            | pet | owner | age | weight
        1   | 1   | Bob   | 11  | 7
        2   | 1   | Eve   | 10  | 11
        3   | 2   | Eve   | 15  | 13
        """
    ).with_universe_of(old)

    new = old.with_columns(*update)
    assert_table_equality(new, expected)


def test_with_columns_0_rows():
    old = T(
        """
            | pet | owner | age
        """
    )
    update = T(
        """
            | owner | age | weight
        """
    ).with_universe_of(old)
    expected = T(
        """
            | pet | owner | age | weight
        """
    ).with_universe_of(old)

    assert_table_equality(old.with_columns(**update), expected)


def test_with_columns_ix_args():
    t1 = T(
        """
      | a | b
    0 | 3 | 1
    1 | 4 | 2
    2 | 7 | 0
    """
    )
    t2 = T(
        """
      |  c
    0 | 10
    1 | 20
    2 | 30
    """
    )
    expected = T(
        """
      | a | b |  c
    0 | 3 | 1 | 20
    1 | 4 | 2 | 30
    2 | 7 | 0 | 10
    """
    )
    t3 = t1.with_columns(t2.ix(t2.pointer_from(t1.b)).c)
    assert_table_equality(t3, expected)


def test_with_columns_ids_dont_match():
    old = T(
        """
            | pet  |  owner  | age
        1   |  1   | Alice   | 10
        2   |  1   | Bob     | 9
        """
    )
    update = T(
        """
            | pet  |  owner  | age
        5   |  0   | Eve     | 10
        """
    )
    with pytest.raises(Exception):
        old.with_columns(update)


def test_groupby_ix():
    tab = T(
        """
          | grouper | val | output
        0 |       0 |   1 |    abc
        1 |       0 |   2 |    def
        2 |       1 |   1 |    ghi
        3 |       1 |   2 |    jkl
        4 |       2 |   1 |    mno
        5 |       2 |   2 |    pqr
        """,
    ).with_columns(grouper=pw.this.pointer_from(pw.this.grouper))
    res = tab.groupby(id=tab.grouper).reduce(
        col=pw.reducers.argmax(tab.val),
        output=tab.ix(pw.reducers.argmax(tab.val)).output,
    )
    expected = T(
        """
        col | output
          1 | def
          3 | jkl
          5 | pqr
        """,
    ).with_columns(col=tab.pointer_from(pw.this.col))
    assert_table_equality_wo_types(res, expected)


def test_groupby_foreign_column():
    tab = T(
        """
        grouper | col
              0 |   1
              0 |   2
              1 |   3
              1 |   4
              2 |   5
              2 |   6
        """,
    ).with_columns(grouper=pw.this.pointer_from(pw.this.grouper))
    tab2 = tab.select(tab.col)
    grouped = tab.groupby(id=tab.grouper)
    reduced1 = grouped.reduce(
        col=pw.reducers.sum(tab.col),
    )
    reduced2 = grouped.reduce(col=reduced1.col + pw.reducers.sum(tab2.col))
    assert_table_equality_wo_index(
        reduced2,
        T(
            """
            col
            6
            14
            22
            """,
        ),
    )


def test_join_ix():
    left = T(
        """
           | a
        1  | 3
        2  | 2
        3  | 1
        """
    ).with_columns(a=pw.this.pointer_from(pw.this.a))
    right = T(
        """
           | b
        0  | baz
        1  | foo
        2  | bar
        """
    )

    ret = left.join(right, left.a == right.id, id=left.id).select(
        col=right.ix(left.a).b
    )

    ret3 = right.having(left.a).select(col=right.ix(left.a).b)

    # below is the desugared version of above computation
    # it works, and it's magic
    keys_table = left.join(right, left.a == right.id, id=left.id).select(
        join_column=left.a
    )
    desugared_ix = keys_table.join(
        right,
        keys_table.join_column == right.id,
        id=keys_table.id,
    ).select(right.b)
    ret2 = (
        left.join(right, left.a == right.id, id=left.id)
        .promise_universe_is_subset_of(desugared_ix)
        .select(col=desugared_ix.b)
    )
    assert_table_equality(
        ret,
        T(
            """
                | col
            3   | foo
            2   | bar
            """
        ),
    )
    assert_table_equality(ret2, ret)
    assert_table_equality(ret3, ret)


def test_join_foreign_col():
    left = T(
        """
           | a
        1  | 1
        2  | 2
        3  | 3
        """
    )
    right = T(
        """
           | b
        0  | baz
        1  | foo
        2  | bar
        """
    )

    joiner = left.join(right, left.id == right.id)
    t1 = joiner.select(col=left.a * 2)
    t2 = joiner.select(col=left.a + t1.col)
    assert_table_equality_wo_index(
        t2,
        T(
            """
                | col
            1   | 3
            2   | 6
            """
        ),
    )


def test_wildcard_basic_usage():
    tab1 = T(
        """
           | a | b
        1  | 1 | 2
        """
    )

    tab2 = T(
        """
           | c | d
        1  | 3 | 4
        """
    ).with_universe_of(tab1)

    left = tab1.select(*tab1, *tab2)

    right = tab1.select(tab1.a, tab1.b, tab2.c, tab2.d)

    assert_table_equality(left, right)


def test_wildcard_shadowing():
    tab = T(
        """
           | a | b | c | d
        1  | 1 | 2 | 3 | 4
        """
    )

    left = tab.select(*tab.without(tab.a, "b"), e=pw.this.a)

    right = tab.select(tab.c, tab.d, e=tab.a)

    assert_table_equality(left, right)


def test_this_magic_1():
    tab = T(
        """
           | a | b | c | d
        1  | 1 | 2 | 3 | 4
        """
    )

    left = tab.select(pw.this.without("a").b)

    right = tab.select(tab.b)

    assert_table_equality(left, right)


def test_this_magic_2():
    tab = T(
        """
           | a | b | c | d
        1  | 1 | 2 | 3 | 4
        """
    )

    with pytest.raises(KeyError):
        tab.select(pw.this.without(pw.this.a).a)


def test_this_magic_3():
    tab = T(
        """
           | a | b | c | d
        1  | 1 | 2 | 3 | 4
        """
    )

    left = tab.select(*pw.this.without(pw.this.a))

    right = tab.select(tab.b, tab.c, tab.d)

    assert_table_equality(left, right)


def test_this_magic_4():
    tab = T(
        """
           | a | b | c | d
        1  | 1 | 2 | 3 | 4
        """
    )

    left = tab.select(*pw.this[["a", "b", pw.this.c]].without(pw.this.a))

    right = tab.select(tab.b, tab.c)

    assert_table_equality(left, right)


def test_join_this():
    t1 = T(
        """
     age  | owner  | pet
      10  | Alice  | 1
       9  | Bob    | 1
       8  | Alice  | 2
     """
    )
    t2 = T(
        """
     age  | owner  | pet | size
      10  | Alice  | 3   | M
      9   | Bob    | 1   | L
      8   | Tom    | 1   | XL
     """
    )
    t3 = t1.join(
        t2, pw.left.pet == pw.right.pet, pw.left.owner == pw.right.owner
    ).select(age=pw.left.age, owner_name=pw.right.owner, size=pw.this.size)

    expected = T(
        """
    age | owner_name | size
    9   | Bob        | L
    """
    )
    assert_table_equality_wo_index(t3, expected)


def test_join_chain_1():
    edges1 = T(
        """
        u | v
        a | b
        b | c
        c | d
        d | e
        e | f
        f | g
        g | a
    """
    )
    edges2 = edges1.copy()
    edges3 = edges1.copy()
    path3 = (
        edges1.join(edges2, edges1.v == edges2.u)
        .join(edges3, edges2.v == edges3.u)
        .select(edges1.u, edges3.v)
    )
    assert_table_equality_wo_index(
        path3,
        T(
            """
        u | v
        a | d
        b | e
        c | f
        d | g
        e | a
        f | b
        g | c
        """
        ),
    )


def test_join_chain_2():
    edges1 = T(
        """
        u | v
        a | b
        b | c
        c | d
        d | e
        e | f
        f | g
        g | a
    """
    )
    edges2 = edges1.copy()
    edges3 = edges1.copy()
    path3 = edges1.join(
        edges2.join(edges3, edges2.v == edges3.u), edges1.v == edges2.u
    ).select(edges1.u, edges3.v)
    assert_table_equality_wo_index(
        path3,
        T(
            """
        u | v
        a | d
        b | e
        c | f
        d | g
        e | a
        f | b
        g | c
        """
        ),
    )


def test_join_leftrightthis():
    left_table = T(
        """
           | a | b | c
        1  | 1 | 2 | 3
        """
    )

    right_table = T(
        """
           | b | c | d
        1  | 2 | 3 | 4
        """
    )

    assert_table_equality_wo_index(
        left_table.join(right_table, pw.left.b == pw.right.b).select(
            pw.left.a, pw.this.b, pw.right.c, pw.right.d
        ),
        T(
            """
        a | b | c | d
        1 | 2 | 3 | 4
        """
        ),
    )

    with pytest.raises(KeyError):
        left_table.join(right_table, pw.left.b == pw.right.b).select(pw.this.c)


def test_chained_join_leftrightthis():
    left_table = T(
        """
           | a | b
        1  | 1 | 2
        """
    )

    middle_table = T(
        """
           | b | c
        1  | 2 | 3
        """
    )

    right_table = T(
        """
           | b | d
        1  | 2 | 4
        """
    )

    assert_table_equality_wo_index(
        left_table.join(middle_table, pw.left.b == pw.right.b)
        .join(right_table, pw.left.b == pw.right.b)
        .select(*pw.this),
        T(
            """
        a | b | c | d
        1 | 2 | 3 | 4
        """
        ),
    )


def test_chained_join_ids():
    left_table = T(
        """
           | a | b
        1  | 1 | 2
        """
    )

    middle_table = T(
        """
           | b | c
        1  | 2 | 3
        """
    )

    right_table = T(
        """
           | b | d
        1  | 2 | 4
        """
    )

    manually = (
        left_table.join(middle_table, pw.left.b == pw.right.b)
        .select(pw.left.b)
        .with_columns(left_id=pw.this.id)
        .join(right_table, pw.left.b == pw.right.b)
        .select(pw.left.left_id, right_id=pw.right.id)
        .with_columns(this_id=pw.this.id)
    )

    assert_table_equality(
        left_table.join(middle_table, pw.left.b == pw.right.b)
        .join(right_table, pw.left.b == pw.right.b)
        .select(left_id=pw.left.id, right_id=pw.right.id, this_id=pw.this.id),
        manually,
    )


def test_multiple_having():
    indexed_table = T(
        """
           | col
        2  | a
        3  | b
        4  | c
        5  | d
        """
    )

    indexer1 = T(
        """
          | key
        1 | 4
        2 | 3
        3 | 2
        4 | 1
    """
    ).with_columns(key=indexed_table.pointer_from(pw.this.key))

    indexer2 = T(
        """
          | key
        1 | 6
        2 | 5
        3 | 4
        4 | 3
    """
    ).with_columns(key=indexed_table.pointer_from(pw.this.key))

    assert_table_equality_wo_index(
        indexed_table.having(indexer1.key, indexer2.key).select(
            col1=indexed_table.ix(indexer1.key).col,
            col2=indexed_table.ix(indexer2.key).col,
        ),
        T(
            """
        col1 | col2
           a |    c
           b |    d
        """
        ),
    )


def test_having_empty():
    indexed_table = T(
        """
           | col
        2  | a
        3  | b
        4  | c
        5  | d
        """
    )
    assert indexed_table == indexed_table.having()


def test_join_desugaring_assign_id():
    left = T(
        """
                col | on
            1 | a   | 11
            2 | b   | 12
            3 | c   | 13
        """
    )
    right = T(
        """
                col | on
            1 | d   | 12
            2 | e   | 13
            3 | f   | 14
        """,
    )
    joined_lr = left.join(right, left.on == right.on, id=left.id).select(
        lcol=pw.left.col, rcol=pw.right.col
    )
    assert_table_equality_wo_index(
        joined_lr,
        T(
            """
        | lcol | rcol
        1 |    b |    d
        2 |    c |    e
    """
        ),
    )

    joined_rl = right.join(left, right.on == left.on, id=left.id).select(
        lcol=pw.right.col, rcol=pw.left.col
    )
    assert_table_equality_wo_index(joined_lr, joined_rl)


def test_join_chain_assign_id():
    left_table = T(
        """
           | a  | b
        1  | a1 | b1
        2  | a2 | b2
        3  | a3 | b3
        4  | a4 | b4
        """
    )

    middle_table = T(
        """
            | b  | c
        11  | b2 | c2
        12  | b3 | c3
        13  | b4 | c4
        14  | b5 | c5
        """
    )

    right_table = T(
        """
           | c  | d
        21 | c3 | d3
        22 | c4 | d4
        23 | c5 | d5
        24 | c6 | d6
        """
    )

    assert_table_equality(
        left_table.join(middle_table, pw.left.b == pw.right.b, id=pw.left.id)
        .join(right_table, pw.left.c == pw.right.c, id=pw.left.id)
        .select(*pw.this),
        T(
            """
          | a  | b  | c  | d
        3 | a3 | b3 | c3 | d3
        4 | a4 | b4 | c4 | d4
        """
        ),
    )


def test_desugaring_this_star_groupby_01():
    ret = (
        T(
            """
           | A | B
        31 | x | y
        33 | x | y
    """
        )
        .groupby(*pw.this)
        .reduce(*pw.this)
    )

    expected = T(
        """
           | A | B
        31 | x | y

    """
    )
    # expected is not build inline,
    # so that we do have to use any desugaring
    expected = expected.with_id_from(expected.A, expected.B)
    assert_table_equality(ret, expected)


@pytest.mark.parametrize(
    "from_,to_",
    [
        (
            [10, 0, -1, -2, 2**32 + 1, 2**45 + 1],
            [10.0, 0, -1.0, -2, float(2**32 + 1), float(2**45 + 1)],
        ),
        (
            [10, 0, -1, -2, 2**32 + 1, 2**45 + 1],
            [True, False, True, True, True, True],
        ),
        (
            [10, 0, -1, -2, 2**32 + 1, 2**45 + 1],
            ["10", "0", "-1", "-2", "4294967297", "35184372088833"],
        ),
        (
            [
                10.345,
                10.999,
                -1.012,
                -1.99,
                -2.01,
                float(2**32 + 1),
                float(2**45 + 1),
                float(2**60 + 1),
            ],
            [10, 10, -1, -1, -2, 2**32 + 1, 2**45 + 1, 2**60],
        ),
        ([10.345, 10.999, -1.012, -1.99, 0.0], [True, True, True, True, False]),
        (
            [
                10.345,
                10.999,
                -1.012,
                -1.99,
                -2.01,
                2**32 + 0.2,
                2**45 + 0.1,
            ],
            [
                "10.345",
                "10.999",
                "-1.012",
                "-1.99",
                "-2.01",
                "4294967296.2",
                "35184372088832.1",
            ],
        ),
        ([False, True], [0, 1]),
        ([False, True], [0.0, 1.0]),
        ([False, True], ["False", "True"]),
        (
            ["10", "0", "-1", "-2", "4294967297", "35184372088833"],
            [10, 0, -1, -2, 2**32 + 1, 2**45 + 1],
        ),
        (
            [
                "10.345",
                "10.999",
                "-1.012",
                "-1.99",
                "-2.01",
                "4294967297",
                "35184372088833",
            ],
            [
                10.345,
                10.999,
                -1.012,
                -1.99,
                -2.01,
                float(2**32 + 1),
                float(2**45 + 1),
            ],
        ),
        (["", "False", "True", "12", "abc"], [False, True, True, True, True]),
    ],
)
def test_cast(from_: List, to_: List):
    from_dtype = type(from_[0])
    to_dtype = type(to_[0])

    def move_to_pathway_with_the_right_type(list: List, dtype: Any):
        df = pd.DataFrame({"a": list}, dtype=dtype)
        table = table_from_pandas(df)
        if dtype == str:
            table = table.update_types(a=str)
        return table

    table = move_to_pathway_with_the_right_type(from_, from_dtype)
    expected = move_to_pathway_with_the_right_type(to_, to_dtype)
    table = table.select(a=pw.cast(to_dtype, pw.this.a))
    assert_table_equality(table, expected)


def test_lazy_coalesce():
    tab = T(
        """
    col
    1
    2
    3
    """
    )
    ret = tab.select(col=pw.declare_type(int, pw.coalesce(tab.col, tab.col / 0)))
    assert_table_equality(ret, tab)


def test_require_01():
    tab = T(
        """
    col1 | col2
    2   | 2
    1   |
    3   | 3
    """
    )

    expected = T(
        """
    sum | dummy
    4   | 1
        | 1
    6   | 1
    """
    ).select(pw.this.sum)

    def f(a, b):
        return a + b

    app_expr = pw.apply(f, tab.col1, tab.col2)
    req_expr = pw.require(app_expr, tab.col2)

    res = tab.select(sum=req_expr)

    assert_table_equality_wo_index_types(res, expected)

    assert req_expr._dependencies() == app_expr._dependencies()


def test_if_else():
    tab = T(
        """
    a | b
    1 | 0
    2 | 2
    3 | 3
    4 | 2
        """
    )

    ret = tab.select(res=pw.if_else(tab.b != 0, tab.a // tab.b, 0))

    assert_table_equality(
        ret,
        T(
            """
        res
        0
        1
        1
        2
        """
        ),
    )


def test_join_filter_1():
    left = T(
        """
                val
            1 | 10
            2 | 11
            3 | 12
        """
    )
    right = T(
        """
                val
            1 | 10
            2 | 11
            3 | 12
        """,
    )
    joined = (
        left.join(right)
        .filter(pw.left.val < pw.right.val)
        .select(left_val=pw.left.val, right_val=pw.right.val)
    )
    assert_table_equality_wo_index(
        joined,
        T(
            """
            left_val | right_val
                  10 |        11
                  10 |        12
                  11 |        12
            """
        ),
    )


def test_join_filter_2():
    tA = T(
        """
                 A
            1 | 10
            2 | 11
            3 | 12
        """
    )
    tB = T(
        """
                 B
            1 | 10
            2 | 11
            3 | 12
        """
    )
    tC = T(
        """
                 C
            1 | 10
            2 | 11
            3 | 12
        """
    )
    tD = T(
        """
                 D
            1 | 10
            2 | 11
            3 | 12
        """
    )

    result = (
        tA.join(tB)
        .filter(pw.this.A <= pw.this.B)
        .join(tC)
        .join(tD)
        .filter(pw.this.C <= pw.this.D)
        .filter(pw.this.A + pw.this.B == pw.this.C + pw.this.D)
        .select(*pw.this)
    )
    expected = T(
        """
 A  | B  | C  | D
 10 | 10 | 10 | 10
 10 | 11 | 10 | 11
 10 | 12 | 10 | 12
 10 | 12 | 11 | 11
 11 | 11 | 10 | 12
 11 | 11 | 11 | 11
 11 | 12 | 11 | 12
 12 | 12 | 12 | 12
        """
    )

    assert_table_equality_wo_index(result, expected)


def test_outerjoin_filter_1():
    left = T(
        """
                val
            1 | 10
            2 | 11
            3 | 12
        """
    )
    right = T(
        """
                val
            1 | 11
            2 | 12
            3 | 13
        """,
    )
    joined = (
        left.join_outer(right, left.val == right.val)
        .filter(pw.left.val.is_not_none())
        .filter(pw.right.val.is_not_none())
        .select(left_val=pw.left.val, right_val=pw.right.val)
    )
    assert_table_equality_wo_index(
        joined,
        T(
            """
            left_val | right_val
                  11 |        11
                  12 |        12
            """
        ).update_types(
            left_val=Optional[int],
            right_val=Optional[int],
        ),
    )


def test_outerjoin_filter_2():
    left = T(
        """
                val
            1 | 10
            2 | 11
            3 | 12
        """
    )
    right = T(
        """
                val
            1 | 11
            2 | 12
            3 | 13
        """,
    )
    joined = (
        left.join_outer(right, left.val == right.val)
        .filter(pw.left.val.is_not_none())
        .filter(pw.right.val.is_not_none())
        .select(val=pw.left.val + pw.right.val)
    )
    assert_table_equality_wo_index(
        joined,
        T(
            """
            val
             22
             24
            """
        ).update_types(val=Optional[int]),
    )


def test_join_reduce_1():
    left = T(
        """
                a
            1 | 10
            2 | 11
            3 | 12
        """
    )
    right = T(
        """
                b
            1 | 11
            2 | 12
            3 | 13
        """,
    )
    result = left.join(right).reduce(col=pw.reducers.count())
    expected = T(
        """
        col
        9
    """
    )
    assert_table_equality_wo_index(result, expected)


def test_join_reduce_2():
    left = T(
        """
                a
            1 | 10
            2 | 11
            3 | 12
        """
    )
    right = T(
        """
                b
            1 | 11
            2 | 12
            3 | 13
        """,
    )
    result = left.join(right).reduce(col=pw.reducers.sum(pw.left.a * pw.right.b))
    result2 = left.join(right).reduce(col=pw.reducers.sum(pw.this.a * pw.this.b))
    expected = T(
        f"""
        col
        {(10+11+12)*(11+12+13)}
    """
    )
    assert_table_equality_wo_index(result, expected)
    assert_table_equality_wo_index(result2, expected)


def test_join_groupby_1():
    left = T(
        """
              | a  | lcol
            1 | 10 |    1
            2 | 11 |    1
            3 | 12 |    2
            4 | 13 |    2
        """
    )
    right = T(
        """
              | b  | rcol
            1 | 11 |    1
            2 | 12 |    1
            3 | 13 |    2
            4 | 14 |    2
        """,
    )
    result = (
        left.join(right)
        .groupby(pw.this.lcol, pw.this.rcol)
        .reduce(pw.this.lcol, pw.this.rcol, res=pw.reducers.sum(pw.this.a * pw.this.b))
    )
    expected = T(
        f"""
    lcol | rcol | res
       1 |    1 | {(10+11)*(11+12)}
       1 |    2 | {(10+11)*(13+14)}
       2 |    1 | {(12+13)*(11+12)}
       2 |    2 | {(12+13)*(13+14)}
    """
    )
    assert_table_equality_wo_index(result, expected)


def test_join_groupby_2():
    left = T(
        """
                a  |  col
            1 | 10 |    1
            2 | 11 |    1
            3 | 12 |    2
            4 | 13 |    2
        """
    )
    right = T(
        """
                b  |  col
            1 | 11 |    1
            2 | 12 |    1
            3 | 13 |    2
            4 | 14 |    2
        """,
    )
    result = (
        left.join(right, left.col == right.col)
        .groupby(pw.this.col)
        .reduce(pw.this.col, res=pw.reducers.sum(pw.this.a * pw.this.b))
    )
    expected = T(
        f"""
    col | res
      1 | {(10+11)*(11+12)}
      2 | {(12+13)*(13+14)}
    """
    )
    assert_table_equality_wo_index(result, expected)


def test_join_filter_reduce():
    left = T(
        """
                a
            1 | 10
            2 | 11
            3 | 12
        """
    )
    right = T(
        """
                b
            1 | 11
            2 | 12
            3 | 13
        """,
    )
    result = (
        left.join(right).filter(pw.this.a >= pw.this.b).reduce(col=pw.reducers.count())
    )
    expected = T(
        """
        col
        3
    """
    )
    assert_table_equality_wo_index(result, expected)


def test_make_tuple():
    t = T(
        """
        A | B  | C
        1 | 10 | a
        2 | 20 |
        3 | 30 | c
        """
    )
    result = t.select(zip_column=pw.make_tuple(t.A * 2, pw.this.B, pw.this.C))

    def three_args_tuple(x, y, z) -> tuple:
        return (x, y, z)

    expected = t.select(
        zip_column=pw.apply_with_type(
            three_args_tuple,
            Tuple[int, int, Optional[str]],  # type: ignore[arg-type]
            pw.this.A * 2,
            pw.this.B,
            pw.this.C,
        )
    )
    assert_table_equality_wo_index(result, expected)


def test_sequence_get_unchecked_fixed_length():
    t1 = T(
        """
      | i | s
    1 | 4 | xyz
    2 | 3 | abc
    3 | 7 | d
    """
    )

    t2 = t1.select(tup=pw.make_tuple(pw.this.i, pw.this.s))
    t3 = t2.select(i=pw.this.tup[0], s=pw.this.tup[1])

    assert_table_equality(t3, t1)


def test_sequence_get_unchecked_fixed_length_dynamic_index_1():
    t1 = T(
        """
      | i | s   | a
    1 | 4 | xyz | 0
    2 | 3 | abc | 1
    3 | 7 | d   | 0
    """
    )

    t2 = t1.select(tup=pw.make_tuple(pw.this.i, pw.this.s), a=pw.this.a)
    t3 = t2.select(r=pw.this.tup[pw.this.a])
    assert t3.schema.as_dict()["r"] == Any


def test_sequence_get_unchecked_fixed_length_dynamic_index_2():
    t1 = T(
        """
      | a | b | c
    1 | 4 | 1 | 0
    2 | 3 | 2 | 1
    3 | 7 | 3 | 1
    """
    )
    expected = T(
        """
      | r
    1 | 4
    2 | 2
    3 | 3
    """
    )

    t2 = t1.select(tup=pw.make_tuple(pw.this.a, pw.this.b), c=pw.this.c)
    t3 = t2.select(r=pw.this.tup[pw.this.c])

    assert_table_equality(t3, expected)


def test_sequence_get_checked_fixed_length_dynamic_index():
    t1 = T(
        """
      | a | b | c
    1 | 4 | 1 | 0
    2 | 3 | 2 | 1
    3 | 7 | 3 | 1
    """
    )
    expected = T(
        """
      | r
    1 | 4
    2 | 2
    3 | 3
    """
    )

    t2 = t1.select(tup=pw.make_tuple(pw.this.a, pw.this.b), c=pw.this.c)
    t3 = t2.select(r=pw.this.tup.get(pw.this.c))

    assert t3.schema.as_dict()["r"] == Optional[int]
    assert_table_equality_wo_types(t3, expected)


def _create_tuple(n: int) -> Tuple[int, ...]:
    return tuple(range(n, 0, -1))


def test_sequence_get_unchecked_variable_length():
    t1 = T(
        """
      | a
    1 | 3
    2 | 4
    3 | 5
    """
    )
    expected = T(
        """
      | x | y
    1 | 1 | 3
    2 | 2 | 3
    3 | 3 | 3
    """
    )

    t2 = t1.select(tup=pw.apply(_create_tuple, pw.this.a))
    t3 = t2.select(x=pw.this.tup[2], y=pw.this.tup[-3])

    assert_table_equality(t3, expected)


def test_sequence_get_unchecked_variable_length_untyped():
    t1 = T(
        """
      | a
    1 | 3
    2 | 4
    3 | 5
    """
    )
    expected = T(
        """
      | x | y
    1 | 1 | 3
    2 | 2 | 3
    3 | 3 | 3
    """
    )

    t2 = t1.select(tup=pw.declare_type(Any, pw.apply(_create_tuple, pw.this.a)))
    t3 = t2.select(x=pw.this.tup[2], y=pw.this.tup[-3])

    assert_table_equality_wo_types(t3, expected)


def test_sequence_get_checked_variable_length():
    t1 = T(
        """
      | a
    1 | 1
    2 | 2
    3 | 3
    """
    )
    expected = T(
        """
      | x | y
    1 |   | 1
    2 | 1 | 1
    3 | 2 | 1
    """
    )

    t2 = t1.select(tup=pw.apply(_create_tuple, pw.this.a))
    t3 = t2.select(x=pw.this.tup.get(1), y=pw.declare_type(int, pw.this.tup.get(-1)))

    assert_table_equality(t3, expected)


def test_sequence_get_unchecked_variable_length_errors():
    t1 = T(
        """
      | a
    1 | 1
    2 | 2
    3 | 5
    """
    )

    t2 = t1.select(tup=pw.apply(_create_tuple, pw.this.a))
    t2.select(x=pw.this.tup[1])
    with pytest.raises(IndexError):
        run_all()


def test_sequence_get_unchecked_fixed_length_errors():
    t1 = T(
        """
      | a | b
    1 | 4 | 10
    2 | 3 | 9
    3 | 7 | 8
    """
    )

    t2 = t1.select(tup=pw.make_tuple(pw.this.a, pw.this.b))
    with pytest.raises(
        IndexError,
        match=(
            re.escape(
                "Index 2 out of range for a tuple of type typing.Tuple[int, int]."
            )
            + r"[\s\S]*"
        ),
    ):
        t2.select(i=pw.this.tup[2])


def test_sequence_get_checked_fixed_length_errors():
    file_name = os.path.basename(__file__)
    t1 = T(
        """
      | a | b  |  c
    1 | 4 | 10 | abc
    2 | 3 | 9  | def
    3 | 7 | 8  | xx
    """
    )
    expected = T(
        """
      |  c
    1 | abc
    2 | def
    3 | xx
    """
    )

    t2 = t1.with_columns(tup=pw.make_tuple(pw.this.a, pw.this.b))
    with pytest.warns(
        UserWarning,
        match=(
            re.escape(
                "Index 2 out of range for a tuple of type typing.Tuple[int, int]."
            )
            + " It refers to the following expression:\n"
            + re.escape("(<table1>.tup).get(2, <table1>.c),\n")
            + rf"called in .*{file_name}.*\n"
            + "with tables:\n"
            + r"<table1> created in .*\n"
            + re.escape("Consider using just the default value without .get().")
        ),
    ):
        t3 = t2.select(c=pw.this.tup.get(2, default=pw.this.c))
    assert_table_equality(t3, expected)


@pytest.mark.parametrize("dtype", [int, float])
@pytest.mark.parametrize("index", [pw.this.index_pos, pw.this.index_neg])
@pytest.mark.parametrize("checked", [True, False])
def test_sequence_get_from_1d_ndarray(dtype, index, checked):
    t = pw.debug.table_from_pandas(
        pd.DataFrame(
            {
                "a": [
                    np.array([1, 2, 3], dtype=dtype),
                    np.array([4, 5], dtype=dtype),
                    np.array([0, 0], dtype=dtype),
                ],
                "index_pos": [1, 1, 1],
                "index_neg": [-2, -1, -1],
            }
        )
    ).update_columns(a=pw.declare_type(np.ndarray, pw.this.a))
    expected = T(
        """
        a
        2
        5
        0
    """
    )
    if checked:
        result = t.select(a=pw.this.a.get(index))
    else:
        result = t.select(a=pw.this.a[index])
    assert_table_equality_wo_index_types(result, expected)


@pytest.mark.parametrize("dtype", [int, float])
@pytest.mark.parametrize("index", [1, -1])
@pytest.mark.parametrize("checked", [True, False])
def test_sequence_get_from_2d_ndarray(dtype, index, checked):
    t = pw.debug.table_from_pandas(
        pd.DataFrame(
            {
                "a": [
                    np.array([[1, 2, 3], [4, 5, 6]], dtype=dtype),
                    np.array([[4, 5], [6, 7]], dtype=dtype),
                    np.array([[0, 0], [1, 1]], dtype=dtype),
                ]
            }
        )
    ).select(a=pw.declare_type(np.ndarray, pw.this.a))
    expected = pw.debug.table_from_pandas(
        pd.DataFrame(
            {
                "a": [
                    np.array([4, 5, 6], dtype=dtype),
                    np.array([6, 7], dtype=dtype),
                    np.array([1, 1], dtype=dtype),
                ]
            }
        )
    ).select(a=pw.declare_type(np.ndarray, pw.this.a))

    if checked:
        result = t.select(a=pw.this.a.get(index))
    else:
        result = t.select(a=pw.this.a[index])

    result = result.select(a=pw.declare_type(np.ndarray, pw.this.a))

    def check_all_rows_equal(t0: api.CapturedTable, t1: api.CapturedTable) -> None:
        assert all([(r0[0] == r1[0]).all() for r0, r1 in zip(t0.values(), t1.values())])  # type: ignore[attr-defined]

    run_graph_and_validate_result(check_all_rows_equal)(result, expected)


@pytest.mark.parametrize("dtype", [int, float])
@pytest.mark.parametrize(
    "index,expected", [([2, 2, 2], [3, -1, -1]), ([-3, -2, -3], [1, 4, -1])]
)
def test_sequence_get_from_1d_ndarray_default(dtype, index, expected):
    t = pw.debug.table_from_pandas(
        pd.DataFrame(
            {
                "a": [
                    np.array([1, 2, 3], dtype=dtype),
                    np.array([4, 5], dtype=dtype),
                    np.array([0, 0], dtype=dtype),
                ],
                "index": index,
            }
        )
    ).update_columns(a=pw.declare_type(np.ndarray, pw.this.a))
    expected = pw.debug.table_from_pandas(pd.DataFrame({"a": expected}))
    result = t.select(a=pw.this.a.get(pw.this.index, default=-1))
    assert_table_equality_wo_index_types(result, expected)


@pytest.mark.parametrize("dtype", [int, float])
@pytest.mark.parametrize("index", [[2, 2, 2], [-3, -2, -3]])
def test_sequence_get_from_1d_ndarray_out_of_bounds(dtype, index):
    t = pw.debug.table_from_pandas(
        pd.DataFrame(
            {
                "a": [
                    np.array([1, 2, 3], dtype=dtype),
                    np.array([4, 5], dtype=dtype),
                    np.array([0, 0], dtype=dtype),
                ],
                "index": index,
            }
        )
    ).update_columns(a=pw.declare_type(np.ndarray, pw.this.a))
    t.select(a=pw.this.a[pw.this.index])
    with pytest.raises(IndexError):
        run_all()


def test_unique():
    left = T(
        """
      | pet  |  owner  | age
    1 | dog  | Bob     | 10
    2 | cat  | Alice   | 9
    3 | cat  | Alice   | 8
    4 | dog  | Bob     | 7
    5 | foo  | Charlie | 6
    """
    )

    left_res = left.groupby(left.pet).reduce(left.pet, pw.reducers.unique(left.owner))

    assert_table_equality_wo_index(
        left_res,
        T(
            """
        pet | owner
        dog | Bob
        cat | Alice
        foo | Charlie
    """
        ),
    )
    left.groupby(left.pet).reduce(pw.reducers.unique(left.age))
    with pytest.raises(Exception):
        run_all()


def test_any():
    left = T(
        """
      | pet  |  owner  | age
    1 | dog  | Bob     | 10
    2 | cat  | Alice   | 9
    3 | cat  | Alice   | 8
    4 | dog  | Bob     | 7
    5 | foo  | Charlie | 6
    """
    )

    left_res = left.reduce(
        pw.reducers.any(left.pet),
        pw.reducers.any(left.owner),
        pw.reducers.any(left.age),
    )

    joined = left.join(
        left_res,
        left.pet == left_res.pet,
        left.owner == left_res.owner,
        left.age == left_res.age,
    ).reduce(cnt=pw.reducers.count())

    assert_table_equality_wo_index(
        joined,
        T(
            """
    cnt
    1
    """
        ),
    )


def test_slices_1():
    left = T(
        """
                col | on
            1 | a   | 11
            2 | b   | 12
            3 | c   | 13
        """
    )
    right = T(
        """
                col | on
            1 | d   | 12
            2 | e   | 13
            3 | f   | 14
        """,
    )
    res = left.join(right, left.on == right.on).select(
        **left.slice.with_suffix("_l").with_prefix("t"),
        **right.slice.with_suffix("_r").with_prefix("t"),
    )
    expected = T(
        """
tcol_l | ton_l | tcol_r | ton_r
b      | 12    | d      | 12
c      | 13    | e      | 13
    """
    )
    assert_table_equality_wo_index(res, expected)


def test_slices_2():
    left = T(
        """
                col | on
            1 | a   | 11
            2 | b   | 12
            3 | c   | 13
        """
    )
    right = T(
        """
                col | on
            1 | d   | 12
            2 | e   | 13
            3 | f   | 14
        """,
    )
    res = left.join(right, left.on == right.on).select(
        **pw.left.with_suffix("_l").with_prefix("t"),
        **pw.right.with_suffix("_r").with_prefix("t"),
    )
    expected = T(
        """
tcol_l | ton_l | tcol_r | ton_r
b      | 12    | d      | 12
c      | 13    | e      | 13
    """
    )
    assert_table_equality_wo_index(res, expected)


def test_slices_3():
    left = T(
        """
                col | on
            1 | a   | 11
            2 | b   | 12
            3 | c   | 13
        """
    )
    right = T(
        """
                col | on
            1 | d   | 12
            2 | e   | 13
            3 | f   | 14
        """,
    )
    res = left.join(right, left.on == right.on).select(
        **pw.left.without("col"),
        **pw.right.rename({"col": "col2"}),
    )
    expected = T(
        """
on | col2
12 | d
13 | e
    """
    )
    assert_table_equality_wo_index(res, expected)


def test_slices_4():
    left = T(
        """
                col | on
            1 | a   | 11
            2 | b   | 12
            3 | c   | 13
        """
    )
    right = T(
        """
                col | on
            1 | d   | 12
            2 | e   | 13
            3 | f   | 14
        """,
    )
    res = left.join(right, left.on == right.on).select(
        **pw.left.without(pw.this.col),
        **pw.right.rename({pw.this.col: pw.this.col2}),
    )
    expected = T(
        """
on | col2
12 | d
13 | e
    """
    )
    assert_table_equality_wo_index(res, expected)


def test_slices_5():
    left = T(
        """
                col | on
            1 | a   | 11
            2 | b   | 12
            3 | c   | 13
        """
    )
    right = T(
        """
                col | on
            1 | d   | 12
            2 | e   | 13
            3 | f   | 14
        """,
    )
    res = left.join(right, left.on == right.on).select(
        **pw.left.without(left.col),
        **pw.right.rename({right.col: pw.this.col2})[["col2"]],
    )
    expected = T(
        """
on | col2
12 | d
13 | e
    """
    )
    assert_table_equality_wo_index(res, expected)


def test_slices_6():
    left = T(
        """
                col | on
            1 | a   | 11
            2 | b   | 12
            3 | c   | 13
        """
    )
    right = T(
        """
                col | on
            1 | d   | 12
            2 | e   | 13
            3 | f   | 14
        """,
    )
    res = left.join(right, left.on == right.on).select(
        left.slice.on,
    )
    expected = T(
        """
on
12
13
    """
    )
    assert_table_equality_wo_index(res, expected)
    assert_table_equality_wo_index(res, expected)
