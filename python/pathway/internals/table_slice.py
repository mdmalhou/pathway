# Copyright © 2023 Pathway

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Union, overload

from pathway.internals.expression import ColumnReference
from pathway.internals.runtime_type_check import runtime_type_check
from pathway.internals.thisclass import ThisMetaclass, this

if TYPE_CHECKING:
    from pathway.internals.table import Table


class TableSlice:
    """Collection of references to Table columns.
    Created by Table.slice method, or automatically by using left/right/this constructs.
    Supports basic column manipulation methods.

    Example:

    >>> import pathway as pw
    >>> t1 = pw.debug.parse_to_table('''
    ... age | owner | pet
    ... 10  | Alice | dog
    ... 9   | Bob   | dog
    ... 8   | Alice | cat
    ... 7   | Bob   | dog
    ... ''')
    >>> t1.slice.without("age").with_suffix("_col")
    TableSlice({'owner_col': <table1>.owner, 'pet_col': <table1>.pet})
    """

    _mapping: dict[str, ColumnReference]
    _table: Table

    def __init__(self, mapping, table):
        self._mapping = mapping
        self._table = table

    def __iter__(self):
        return iter(self._mapping.values())

    def __repr__(self):
        return f"TableSlice({self._mapping})"

    def keys(self):
        return self._mapping.keys()

    @overload
    def __getitem__(self, args: Union[str, ColumnReference]) -> ColumnReference:
        ...

    @overload
    def __getitem__(self, args: List[Union[str, ColumnReference]]) -> TableSlice:
        ...

    def __getitem__(
        self, arg: Union[str, ColumnReference] | List[Union[str, ColumnReference]]
    ) -> Union[ColumnReference, TableSlice]:
        if isinstance(arg, (ColumnReference, str)):
            return self._mapping[self._normalize(arg)]
        else:
            return TableSlice({self._normalize(k): self[k] for k in arg}, self._table)

    def __getattr__(self, name: str) -> ColumnReference:
        from pathway.internals import Table

        if hasattr(Table, name) and name != "id":
            raise ValueError(
                f"{name!r} is a method name. It is discouraged to use it as a column"
                + f" name. If you really want to use it, use [{name!r}]."
            )
        if name not in self._mapping:
            raise AttributeError(f"Column name {name!r} not found in {self!r}.")
        return self._mapping[name]

    @runtime_type_check
    def without(self, *cols: Union[str, ColumnReference]) -> TableSlice:
        mapping = self._mapping.copy()
        for col in cols:
            colname = self._normalize(col)
            if colname not in mapping:
                raise KeyError(f"Column name {repr(colname)} not found in a {self}.")
            mapping.pop(colname)
        return TableSlice(mapping, self._table)

    @runtime_type_check
    def rename(
        self,
        rename_dict: Dict[Union[str, ColumnReference], Union[str, ColumnReference]],
    ) -> TableSlice:
        rename_dict_normalized = {
            self._normalize(old): self._normalize(new)
            for old, new in rename_dict.items()
        }
        mapping = self._mapping.copy()
        for old in rename_dict_normalized.keys():
            if old not in mapping:
                raise KeyError(f"Column name {repr(old)} not found in a {self}.")
            mapping.pop(old)
        for old, new in rename_dict_normalized.items():
            mapping[new] = self._mapping[old]
        return TableSlice(mapping, self._table)

    @runtime_type_check
    def with_prefix(self, prefix: str) -> TableSlice:
        return self.rename({name: prefix + name for name in self.keys()})

    @runtime_type_check
    def with_suffix(self, suffix: str) -> TableSlice:
        return self.rename({name: name + suffix for name in self.keys()})

    @property
    def slice(self):
        return self

    def _normalize(self, arg: Union[str, ColumnReference]):
        if isinstance(arg, ColumnReference):
            if isinstance(arg.table, ThisMetaclass):
                if arg.table != this:
                    raise ValueError(
                        f"TableSlice expects {repr(arg.name)} or this.{arg.name} argument as column reference."
                    )
            else:
                if arg.table != self._table:
                    raise ValueError(
                        "TableSlice method arguments should refer to table of which the slice was created."
                    )
            return arg.name
        else:
            return arg
