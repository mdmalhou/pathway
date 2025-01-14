# Copyright © 2023 Pathway

import contextlib
import os
import re
from typing import Type

import pandas as pd
import pytest

import pathway as pw
from pathway.internals.runtime_type_check import runtime_type_check
from pathway.tests.utils import (
    T,
    assert_table_equality,
    remove_ansi_escape_codes,
    run_all,
)


def test_select_args():
    tab = T(
        """a
            1
            2"""
    )

    with pytest.raises(
        ValueError,
        match=re.escape(
            "Expected a ColumnReference, found a string. Did you mean this.a instead of 'a'?"
        ),
    ):
        tab.select("a")


def test_reduce_args():
    tab = T(
        """a
            1
            2"""
    )

    with pytest.raises(
        ValueError,
        match=re.escape(
            "Expected a ColumnReference, found a string. Did you mean this.a instead of 'a'?"
        ),
    ):
        tab.reduce("a")

    with pytest.raises(
        ValueError,
        match=re.escape(
            "In reduce() all positional arguments have to be a ColumnReference."
        ),
    ):
        tab.reduce(1)

    with pytest.raises(
        ValueError,
        match=re.escape(
            "Expected a ColumnReference, found a string. Did you mean this.a instead of 'a'?"
        ),
    ):
        tab.groupby().reduce("a")

    with pytest.raises(
        ValueError,
        match=re.escape(
            "In reduce() all positional arguments have to be a ColumnReference."
        ),
    ):
        tab.groupby().reduce(1)


def test_groupby_extrakwargs():
    tab = T(
        """a
            1
            2"""
    )

    with pytest.raises(
        ValueError,
        match=re.escape(
            "Table.groupby() received extra kwargs.\n"
            + "You probably want to use Table.groupby(...).reduce(**kwargs) to compute output columns."
        ),
    ):
        tab.groupby(pw.this.a, output=pw.this.a)


def test_groupby_extraargs():
    t = T(
        """
            | shard |  t | tt |  v
        1   | 0     |  1 |  1 |  10
        2   | 0     |  2 |  2 |  1
        3   | 0     |  4 |  4 |  3
        4   | 0     |  8 |  8 |  2
        5   | 0     |  9 |  9 |  4
        6   | 0     |  10|  10|  8
        7   | 1     |  1 |  1 |  9
        8   | 1     |  2 |  2 |  16
    """
    )

    with pytest.raises(
        ValueError,
        match=re.escape(
            "Table.windowby() received extra args.\nIt handles grouping only by a single column."
        ),
    ):
        t.windowby(
            t.t,
            t.tt,
            window=pw.temporal.session(predicate=lambda a, b: abs(a - b) <= 1),
            shard=t.shard,
        )


def test_join_args():
    left = T(
        """a
            1
            2"""
    )
    right = left.copy()

    with pytest.raises(
        ValueError,
        match=re.escape(
            "Received `how` argument but was not expecting any.\n"
            + "Consider using a generic join method that handles `how` to decide on a type of a join to be used."
        ),
    ):
        left.join_left(right, how=pw.JoinMode.LEFT)

    with pytest.raises(
        ValueError,
        match=re.escape(
            "Received `how` argument of join that is a string.\n"
            + "You probably want to use one of JoinMode.INNER, JoinMode.LEFT,"
            + " JoinMode.RIGHT or JoinMode.OUTER values."
        ),
    ):
        left.join(right, how="left")

    with pytest.raises(
        ValueError,
        match=re.escape(
            "How argument of join should be one of JoinMode.INNER, JoinMode.LEFT,"
            + " JoinMode.RIGHT or JoinMode.OUTER values."
        ),
    ):
        left.join(right, how=1)

    with pytest.raises(
        ValueError,
        match=re.escape("The id argument of a join has to be a ColumnReference."),
    ):
        left.join(right, id=1)

    with pytest.raises(
        ValueError,
        match=re.escape(
            "Join received extra kwargs.\n"
            + "You probably want to use TableLike.join(...).select(**kwargs) to compute output columns."
        ),
    ):
        left.join(right, a=left.a)


def test_session_simple():
    t = T(
        """
            | shard |  t |  v
        1   | 0     |  1 |  10
        2   | 0     |  2 |  1
        3   | 0     |  4 |  3
        4   | 0     |  8 |  2
        5   | 0     |  9 |  4
        6   | 0     |  10|  8
        7   | 1     |  1 |  9
        8   | 1     |  2 |  16
    """
    )

    with pytest.raises(
        ValueError,
        match=re.escape(
            "Table.windowby() received extra kwargs.\n"
            + "You probably want to use Table.windowby(...).reduce(**kwargs) to compute output columns."
        ),
    ):
        t.windowby(
            t.t,
            window=pw.temporal.session(predicate=lambda a, b: abs(a - b) <= 1),
            shard=t.shard,
            min_t=pw.reducers.min(pw.this.t),
            max_v=pw.reducers.max(pw.this.v),
        )


def test_runtime_type_check_decorator():
    @runtime_type_check
    def foo(x: int):
        pass

    with pytest.raises(TypeError) as e:
        foo("123")
    assert (
        "parameter x='123' violates type hint <class 'int'>,"
        + " as str '123' not instance of int."
        in remove_ansi_escape_codes(str(e.value))
    )


@contextlib.contextmanager
def _assert_error_trace(error_type: Type):
    file_name = os.path.basename(__file__)
    with pytest.raises(
        error_type, match=rf"(?s).*Occurred here:.*# cause..*{file_name}.*"
    ):
        yield


def test_traceback_expression():
    input = T(
        """
            | v
        1   | 1
        2   | 2
        3   | 3
        """
    )

    input.select(ret=pw.this.v <= "foo")  # cause

    with _assert_error_trace(TypeError):
        run_all()


def test_traceback_rust_expression():
    input = T(
        """
            | foo | bar
        1   | 1   | a
        2   | 2   | b
        3   | 3   | c
        """
    )

    input = input.with_columns(bar=pw.declare_type(int, pw.this.bar))
    input.select(r=pw.this.foo + pw.this.bar)  # cause

    with _assert_error_trace(TypeError):
        run_all()


def test_traceback_async_apply():
    input = T(
        """
            | foo
        1   | 1
        2   | 2
        3   | 3
        """
    )

    async def inc(_):
        raise ValueError()

    input.select(ret=pw.apply_async(inc, pw.this.foo))  # cause

    with _assert_error_trace(ValueError):
        run_all()


def test_traceback_context_column():
    input = T(
        """
            | v
        1   | 1
        2   | 2
        3   | 3
        """
    )

    input.filter(pw.this.v <= "foo")  # cause

    with _assert_error_trace(TypeError):
        run_all()


def test_traceback_iterate():
    def iterate(iterated):
        def func(x: int) -> int:
            return x // 2

        result = iterated.select(val=pw.apply(func, iterated.val))  # cause

        return dict(iterated=result)

    input = T(
        """
            | val
        1   | foo
        2   | bar
        """
    ).with_columns(val=pw.declare_type(int, pw.this.val))

    pw.iterate(iterate, iterated=input)

    with _assert_error_trace(TypeError):
        run_all()


def test_traceback_transformers_1():
    t = T(
        """
        time
        1
        """
    )

    @pw.transformer
    class syntax_error_transformer:
        class my_table(pw.ClassArg):
            time = pw.input_attribute()

            @pw.output_attribute
            def output_col(self):
                return self.transfomer.my_table[self.id].time  # cause

    t = syntax_error_transformer(my_table=t).my_table

    with _assert_error_trace(AttributeError):
        run_all()


def test_traceback_transformers_2():
    t = T(
        """
        time
        1
        """
    )

    @pw.transformer
    class syntax_error_transformer:
        class my_table(pw.ClassArg):
            time = pw.input_attribute()

            @pw.output_attribute
            def output_col(self):
                return self.transformer.my_tablee[self.id].time  # cause

    t = syntax_error_transformer(my_table=t).my_table

    with _assert_error_trace(AttributeError):
        run_all()


def test_traceback_transformers_3():
    t = T(
        """
        time
        1
        """
    )

    @pw.transformer
    class syntax_error_transformer:
        class my_table(pw.ClassArg):
            time = pw.input_attribute()

            @pw.output_attribute
            def output_col(self):
                return self.transformer.my_table[self.id].foo  # cause

    t = syntax_error_transformer(my_table=t).my_table

    with _assert_error_trace(AttributeError):
        run_all()


def test_traceback_transformers_4():
    t = T(
        """
        time
        1
        """
    )

    @pw.transformer
    class syntax_error_transformer:
        class my_table(pw.ClassArg):
            time = pw.input_attribute()

            @pw.output_attribute
            def output_col(self):
                return self.transformer.my_table["asdf"].time  # cause

    t = syntax_error_transformer(my_table=t).my_table

    with _assert_error_trace(TypeError):
        run_all()


def test_traceback_connectors_1():
    df = pd.DataFrame({"data": [1, 2, 3]})
    pw.debug.table_from_pandas(df, id_from=["non-existing-column"])  # cause
    with _assert_error_trace(KeyError):
        run_all()


def test_traceback_connectors_2(tmp_path):
    pw.io.csv.write(  # cause
        pw.Table.empty(), str(tmp_path / "non_existing_directory" / "output.csv")
    )
    with _assert_error_trace(OSError):
        run_all()


def test_traceback_static():
    table1 = T(
        """
            | foo
        1   | 1
        """
    )
    table2 = T(
        """
            | bar
        2   | 2
        """
    )
    with _assert_error_trace(ValueError):
        table1.concat(table2)  # cause
    with _assert_error_trace(ValueError):
        table1 + table2  # cause
    with _assert_error_trace(AttributeError):
        table1.non_existing  # cause
    with _assert_error_trace(KeyError):
        table1.select(pw.this.non_existing)  # cause


@pytest.mark.parametrize(
    "func",
    [
        pw.io.csv.read,
        pw.io.fs.read,
        pw.io.http.read,
        pw.io.jsonlines.read,
        pw.io.kafka.read,
        pw.io.minio.read,
        pw.io.plaintext.read,
        pw.io.python.read,
        pw.io.redpanda.read,
        pw.io.s3_csv.read,
        pw.io.csv.write,
        pw.io.fs.write,
        pw.io.http.write,
        pw.io.jsonlines.write,
        pw.io.kafka.write,
        pw.io.logstash.write,
        pw.io.null.write,
        pw.io.postgres.write,
        pw.io.redpanda.write,
        pw.io.elasticsearch.write,
    ],
)
def test_traceback_early_connector_errors(func):
    with _assert_error_trace(TypeError):
        func()  # cause


def test_groupby_reduce_bad_column():
    with pytest.raises(
        ValueError,
        match=re.escape(
            "You cannot use <table1>.email in this reduce statement.\n"
            + "Make sure that <table1>.email is used in a groupby or wrap it with a reducer, "
            + "e.g. pw.reducers.count(<table1>.email)"
        ),
    ):
        purchases = T(
            """
        | purchase_id | user_id |  email            | amount
     1  | 1           | 1       | user1@example.com | 15
     2  | 2           | 2       | user2@example.com | 18
        """
        )

        purchases.groupby(purchases.user_id).reduce(
            user_id=pw.this.user_id,
            email=pw.this.email,
            total_amount=pw.reducers.sum(pw.this.amount),
        )


def test_filter_bad_expression():
    with pytest.raises(
        ValueError,
        match=re.escape("You cannot use <table1>.last_timestamp in this context."),
    ):
        t_input = T(
            """
            | request_uri | timestamp
         1  | /home       | 1633024800
         2  | /about      | 1633024860
            """
        )

        last_timestamp = t_input.reduce(
            last_timestamp=pw.reducers.max(t_input.timestamp)
        )
        t_input.filter(t_input.timestamp >= last_timestamp.last_timestamp - 3600)


def test_expressions_display_warning_when_evalution_in_python():
    file_name = os.path.basename(__file__)
    t1 = T(
        """
      | i | b
    1 | 4 | True
    2 | 3 | False
    3 | 0 | False
    """
    )

    with pytest.warns(
        UserWarning,
        match=(
            "Pathway does not natively support operator == "
            + re.escape("on types (<class 'int'>, <class 'bool'>). ")
            + "It refers to the following expression:\n"
            + re.escape("(<table1>.i == <table1>.b),\n")
            + rf"called in .*{file_name}.*\n"
            + "with tables:\n"
            + r"<table1> created in .*\n"
            + "The evaluation will be performed in Python, which may slow down your "
            + "computations. Try specifying the types or expressing the computation differently."
        ),
    ):
        t1.select(a=pw.this.i == pw.this.b)
        run_all()


def test_method_in_pathway_this():
    t1 = pw.debug.table_from_markdown(
        """
      | join
    1 |   2
    2 |  12
    """
    )
    with pytest.raises(
        ValueError,
        match=re.escape(
            "join is a method name. It is discouraged to use it as a column name. "
            + "If you really want to use it, use pw.this['join']."
        ),
    ):
        t1.select(pw.this.join)


def test_table_getitem():
    tab = T(
        """a
            1
            2"""
    )

    with pytest.raises(
        ValueError,
        match=re.escape(
            "Table.__getitem__ argument has to be a ColumnReference to the same table or pw.this, or a string "
            + "(or a list of those)."
        ),
    ):
        tab[tab.copy().a]


def test_from_columns():
    with pytest.raises(
        ValueError,
        match=re.escape("Table.from_columns() cannot have empty arguments list"),
    ):
        pw.Table.from_columns()


def test_groupby():
    left = T(
        """
      | pet  |  owner  | age
    1 |  1   | Alice   | 10
    2 |  1   | Bob     | 9
    3 |  2   | Alice   | 8
    4 |  1   | Bob     | 7
    """
    ).with_columns(pet=pw.this.pointer_from(pw.this.pet))

    res = left.groupby(left.pet, id=left.pet).reduce(
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

    with pytest.raises(
        ValueError,
        match=re.escape(
            "Table.groupby() received id argument and is grouped by a single column,"
            + " but the arguments are not equal.\n"
            + "Consider using <table>.groupby(id=...), skipping the positional argument."
        ),
    ):
        res = left.groupby(left.age, id=left.pet).reduce(
            left.pet,
        )

    with pytest.raises(
        ValueError,
        match=re.escape(
            "Table.groupby() cannot have id argument when grouping by multiple columns."
        ),
    ):
        res = left.groupby(left.age, left.pet, id=left.pet).reduce(
            left.pet,
        )


def test_update_cells():
    left = T(
        """
      | pet  |  owner
    1 |  1   | Alice
    2 |  1   | Bob
    3 |  2   | Alice
    4 |  1   | Bob
    """
    )

    right = T(
        """
      | pet  |  owner  | age
    1 |  1   | Alice   | 10
    2 |  1   | Bob     | 9
    """
    )

    with pytest.raises(
        ValueError,
        match=re.escape(
            "Columns of the argument in Table.update_cells() not present in the updated table: ['age']."
        ),
    ):
        left.update_cells(right)


def test_update_types():
    with pytest.raises(
        ValueError,
        match=re.escape(
            "Table.update_types() argument name has to be an existing table column name."
        ),
    ):
        T(
            """
            foor
            22
            24
            """
        ).update_types(bar=int)


def test_fatten():
    with pytest.raises(
        ValueError, match=re.escape("Table.flatten() cannot have empty arguments list.")
    ):
        T(
            """
            foor
            22
            24
            """
        ).flatten()


def test_slices_1():
    tab = T(
        """
                col | on
            1 | a   | 11
            2 | b   | 12
            3 | c   | 13
        """
    )

    with pytest.raises(
        ValueError,
        match=re.escape(
            "TableSlice method arguments should refer to table of which the slice was created."
        ),
    ):
        tab.slice[tab.copy().col]

    with pytest.raises(
        ValueError,
        match=re.escape(
            "TableSlice expects 'col' or this.col argument as column reference."
        ),
    ):
        tab.slice[pw.left.col]

    with pytest.raises(
        KeyError,
        match=re.escape(
            "Column name 'foo' not found in a TableSlice({'col': <table1>.col, 'on': <table1>.on})."
        ),
    ):
        tab.slice.without("foo")

    with pytest.raises(
        KeyError,
        match=re.escape(
            "Column name 'foo' not found in a TableSlice({'col': <table1>.col, 'on': <table1>.on})."
        ),
    ):
        tab.slice.rename({"foo": "bar"})

    with pytest.raises(
        ValueError,
        match=re.escape(
            "'select' is a method name. It is discouraged to use it as a column name."
            + " If you really want to use it, use ['select']."
        ),
    ):
        tab.slice.select


def test_this():
    with pytest.raises(
        TypeError,
        match=re.escape("You cannot instantiate `this` class."),
    ):
        pw.this()
