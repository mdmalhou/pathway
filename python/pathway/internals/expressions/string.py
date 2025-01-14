# Copyright © 2023 Pathway

from typing import Optional, Union

import pathway.internals.expression as expr
from pathway.internals import api


class StringNamespace:
    """A module containing methods related to string.
    They can be called using a `str` attribute of an expression.

    Typical use:

    >>> import pathway as pw
    >>> table = pw.debug.table_from_markdown(
    ...     '''
    ...      | name
    ...    1 | ALICE
    ... '''
    ... )
    >>> table += table.select(name_lower=table.name.str.lower())
    >>> pw.debug.compute_and_print(table, include_id=False)
    name  | name_lower
    ALICE | alice
    """

    _expression: expr.ColumnExpression

    def __init__(self, expression: expr.ColumnExpression):
        self._expression = expression

    def lower(self) -> expr.ColumnExpression:
        """Returns a lowercase copy of a string.

        Returns:
            Lowercase string

        Example:

        >>> import pathway as pw
        >>> table = pw.debug.table_from_markdown(
        ...     '''
        ...      | name
        ...    1 | Alice
        ...    2 | Bob
        ...    3 | CAROLE
        ...    4 | david
        ... '''
        ... )
        >>> table += table.select(name_lower=table.name.str.lower())
        >>> pw.debug.compute_and_print(table, include_id=False)
        name   | name_lower
        Alice  | alice
        Bob    | bob
        CAROLE | carole
        david  | david
        """

        return expr.MethodCallExpression.with_static_type(
            {
                str: lambda x: api.Expression.apply(str.lower, x),
            },
            str,
            "str.lower",
            self._expression,
        )

    def upper(self) -> expr.ColumnExpression:
        """Returns a uppercase copy of a string.

        Returns:
            Uppercase string

        Example:

        >>> import pathway as pw
        >>> table = pw.debug.table_from_markdown(
        ...     '''
        ...      | name
        ...    1 | Alice
        ...    2 | Bob
        ...    3 | CAROLE
        ...    4 | david
        ... '''
        ... )
        >>> table += table.select(name_upper=table.name.str.upper())
        >>> pw.debug.compute_and_print(table, include_id=False)
        name   | name_upper
        Alice  | ALICE
        Bob    | BOB
        CAROLE | CAROLE
        david  | DAVID
        """

        return expr.MethodCallExpression.with_static_type(
            {
                str: lambda x: api.Expression.apply(str.upper, x),
            },
            str,
            "str.upper",
            self._expression,
        )

    def reversed(self) -> expr.ColumnExpression:
        """Returns a reverse copy of a string.

        Returns:
            Reverse string

        Example:

        >>> import pathway as pw
        >>> table = pw.debug.table_from_markdown(
        ...     '''
        ...      | name
        ...    1 | Alice
        ...    2 | Bob
        ...    3 | CAROLE
        ...    4 | david
        ... '''
        ... )
        >>> table += table.select(name_reverse=table.name.str.reversed())
        >>> pw.debug.compute_and_print(table, include_id=False)
        name   | name_reverse
        Alice  | ecilA
        Bob    | boB
        CAROLE | ELORAC
        david  | divad
        """

        return expr.MethodCallExpression.with_static_type(
            {
                str: lambda x: api.Expression.apply(lambda y: y[::-1], x),
            },
            str,
            "str.reverse",
            self._expression,
        )

    def len(self) -> expr.ColumnExpression:
        """Returns the length of a string.

        Returns:
            Length of the string

        Example:

        >>> import pathway as pw
        >>> table = pw.debug.table_from_markdown(
        ...     '''
        ...      | name
        ...    1 | Alice
        ...    2 | Bob
        ...    3 | CAROLE
        ...    4 | david
        ... '''
        ... )
        >>> table += table.select(length=table.name.str.len())
        >>> pw.debug.compute_and_print(table, include_id=False)
        name   | length
        Alice  | 5
        Bob    | 3
        CAROLE | 6
        david  | 5
        """

        return expr.MethodCallExpression.with_static_type(
            {
                str: lambda x: api.Expression.apply(len, x),
            },
            int,
            "str.len",
            self._expression,
        )

    def replace(
        self,
        old_value: Union[expr.ColumnExpression, str],
        new_value: Union[expr.ColumnExpression, str],
        count: Union[expr.ColumnExpression, int] = -1,
        /,
    ) -> expr.ColumnExpression:
        """Returns the a string where the occurrences of the old_value substrings are
            replaced by the new_value substring.

        Args:
            count: Maximum number of occurrences to replace. When set to -1, replaces
                all occurrences. Defaults to -1.

        Returns:
            The new string where old_value is replaced by new_value

        Example:

        >>> import pathway as pw
        >>> table = pw.debug.table_from_markdown(
        ...     '''
        ...      | name
        ...    1 | Alice
        ...    2 | Bob
        ...    3 | CAROLE
        ...    4 | david
        ...    5 | Edward
        ... '''
        ... )
        >>> table += table.select(name_replace=table.name.str.replace("d","Z"))
        >>> pw.debug.compute_and_print(table, include_id=False)
        name   | name_replace
        Alice  | Alice
        Bob    | Bob
        CAROLE | CAROLE
        Edward | EZwarZ
        david  | ZaviZ
        >>> table = pw.debug.table_from_markdown(
        ...     '''
        ...      | value      | old | new | count
        ...    1 | Scaciscics | c   | t   | 3
        ...    2 | yelliwwiid | i   | o   | 2
        ... '''
        ... )
        >>> table = table.select(
        ...    pw.this.value,
        ...    value_replace=pw.this.value.str.replace(
        ...       pw.this.old, pw.this.new, pw.this.count
        ...    )
        ... )
        >>> pw.debug.compute_and_print(table, include_id=False)
        value      | value_replace
        Scaciscics | Statistics
        yelliwwiid | yellowwoid
        """

        return expr.MethodCallExpression.with_static_type(
            {
                (str, str, str, int): lambda x, y, z, c: api.Expression.apply(
                    lambda s1, s2, s3, cnt: s1.replace(s2, s3, cnt), x, y, z, c
                ),
            },
            str,
            "str.replace",
            self._expression,
            old_value,
            new_value,
            count,
        )

    def startswith(
        self,
        prefix: Union[expr.ColumnExpression, str],
    ) -> expr.ColumnExpression:
        """Returns True if the string starts with prefix.

        Example:

        >>> import pathway as pw
        >>> table = pw.debug.table_from_markdown(
        ...     '''
        ...      | name
        ...    1 | Alice
        ...    2 | Bob
        ...    3 | CAROLE
        ...    4 | david
        ... '''
        ... )
        >>> table += table.select(starts_with_A=table.name.str.startswith("A"))
        >>> pw.debug.compute_and_print(table, include_id=False)
        name   | starts_with_A
        Alice  | True
        Bob    | False
        CAROLE | False
        david  | False
        """

        return expr.MethodCallExpression.with_static_type(
            {
                (str, str): lambda x, y: api.Expression.apply(str.startswith, x, y),
            },
            bool,
            "str.starts_with",
            self._expression,
            prefix,
        )

    def endswith(
        self,
        suffix: Union[expr.ColumnExpression, str],
    ) -> expr.ColumnExpression:
        """Returns True if the string ends with suffix.

        Example:

        >>> import pathway as pw
        >>> table = pw.debug.table_from_markdown(
        ...     '''
        ...      | name
        ...    1 | Alice
        ...    2 | Bob
        ...    3 | CAROLE
        ...    4 | david
        ... '''
        ... )
        >>> table += table.select(ends_with_e=table.name.str.endswith("e"))
        >>> pw.debug.compute_and_print(table, include_id=False)
        name   | ends_with_e
        Alice  | True
        Bob    | False
        CAROLE | False
        david  | False
        """

        return expr.MethodCallExpression.with_static_type(
            {
                (str, str): lambda x, y: api.Expression.apply(str.endswith, x, y),
            },
            bool,
            "str.ends_with",
            self._expression,
            suffix,
        )

    def swapcase(self) -> expr.ColumnExpression:
        """Returns a copy of the string where the case is inverted.

        Example:

        >>> import pathway as pw
        >>> table = pw.debug.table_from_markdown(
        ...     '''
        ...      | name
        ...    1 | Alice
        ...    2 | Bob
        ...    3 | CAROLE
        ...    4 | david
        ... '''
        ... )
        >>> table += table.select(name_swap=table.name.str.swapcase())
        >>> pw.debug.compute_and_print(table, include_id=False)
        name   | name_swap
        Alice  | aLICE
        Bob    | bOB
        CAROLE | carole
        david  | DAVID
        """

        return expr.MethodCallExpression.with_static_type(
            {
                str: lambda x: api.Expression.apply(str.swapcase, x),
            },
            str,
            "str.swap_case",
            self._expression,
        )

    def strip(
        self, chars: Optional[Union[expr.ColumnExpression, str]] = None
    ) -> expr.ColumnExpression:
        """Returns a copy of the string with specified characters.
        If no arguments are passed, remove the leading and trailing whitespaces.


        Example:

        >>> import pathway as pw
        >>> table = pw.debug.table_from_markdown(
        ...     '''
        ...      | name
        ...    1 | Alice
        ...    2 | Bob
        ...    3 | CAROLE
        ...    4 | david
        ... '''
        ... )
        >>> table += table.select(name_strip=table.name.str.strip("Aod"))
        >>> pw.debug.compute_and_print(table, include_id=False)
        name   | name_strip
        Alice  | lice
        Bob    | Bob
        CAROLE | CAROLE
        david  | avi
        """

        if chars is None:
            return expr.MethodCallExpression.with_static_type(
                {
                    str: lambda x: api.Expression.apply(str.strip, x),
                },
                str,
                "str.strip",
                self._expression,
            )

        return expr.MethodCallExpression.with_static_type(
            {
                (str, str): lambda x, y: api.Expression.apply(str.strip, x, y),
            },
            str,
            "str.strip",
            self._expression,
            chars,
        )

    def title(self) -> expr.ColumnExpression:
        """Returns a copy of the string where where words start with an uppercase character
        and the remaining characters are lowercase.


        Example:

        >>> import pathway as pw
        >>> table = pw.debug.table_from_markdown(
        ...     '''
        ...      | col
        ...    1 | title
        ... '''
        ... )
        >>> table = table.select(col_title=table.col.str.title())
        >>> pw.debug.compute_and_print(table, include_id=False)
        col_title
        Title
        """

        return expr.MethodCallExpression.with_static_type(
            {
                str: lambda x: api.Expression.apply(str.title, x),
            },
            str,
            "str.title",
            self._expression,
        )

    def count(
        self,
        sub: Union[expr.ColumnExpression, str],
        start: Optional[Union[expr.ColumnExpression, int]] = None,
        end: Optional[Union[expr.ColumnExpression, int]] = None,
    ) -> expr.ColumnExpression:
        """Returns the number of non-overlapping occurrences of substring sub in the range [start, end].
        Optional arguments start and end are interpreted as in slice notation.


        Example:

        >>> import pathway as pw
        >>> table = pw.debug.table_from_markdown(
        ...     '''
        ...      | name
        ...    1 | Alice
        ...    2 | Hello
        ...    3 | World
        ...    4 | Zoo
        ... '''
        ... )
        >>> table += table.select(count=table.name.str.count("o"))
        >>> pw.debug.compute_and_print(table, include_id=False)
        name  | count
        Alice | 0
        Hello | 1
        World | 1
        Zoo   | 2
        """

        if start is None and end is None:
            return expr.MethodCallExpression.with_static_type(
                {
                    (str, str): lambda x, y: api.Expression.apply(str.count, x, y),
                },
                int,
                "str.count",
                self._expression,
                sub,
            )

        if end is None:
            return expr.MethodCallExpression.with_static_type(
                {
                    (str, str, int): lambda x, y, z: api.Expression.apply(
                        str.count, x, y, z
                    ),
                },
                int,
                "str.count",
                self._expression,
                sub,
                start,
            )

        if start is None:
            raise ValueError("str.count: missing end argument.")

        return expr.MethodCallExpression.with_static_type(
            {
                (str, str, int, int): lambda x, y, z, t: api.Expression.apply(
                    str.count, x, y, z, t
                ),
            },
            int,
            "str.count",
            self._expression,
            sub,
            start,
            end,
        )

    def find(
        self,
        sub: Union[expr.ColumnExpression, str],
        start: Optional[Union[expr.ColumnExpression, int]] = None,
        end: Optional[Union[expr.ColumnExpression, int]] = None,
    ) -> expr.ColumnExpression:
        """Return the lowest index in the string where substring sub is found within
        the slice s[start:end]. Optional arguments start and end are interpreted as in
        slice notation. Return -1 if sub is not found.


        Example:

        >>> import pathway as pw
        >>> table = pw.debug.table_from_markdown(
        ...     '''
        ...      | name
        ...    1 | Alice
        ...    2 | Hello
        ...    3 | World
        ...    4 | Zoo
        ... '''
        ... )
        >>> table += table.select(count=table.name.str.find("o"))
        >>> pw.debug.compute_and_print(table, include_id=False)
        name  | count
        Alice | -1
        Hello | 4
        World | 1
        Zoo   | 1
        """

        if start is None and end is None:
            return expr.MethodCallExpression.with_static_type(
                {
                    (str, str): lambda x, y: api.Expression.apply(str.find, x, y),
                },
                int,
                "str.find",
                self._expression,
                sub,
            )

        if end is None:
            return expr.MethodCallExpression.with_static_type(
                {
                    (str, str, int): lambda x, y, z: api.Expression.apply(
                        str.find, x, y, z
                    ),
                },
                int,
                "str.find",
                self._expression,
                sub,
                start,
            )

        if start is None:
            raise ValueError("str.find: missing end argument.")

        return expr.MethodCallExpression.with_static_type(
            {
                (str, str, int, int): lambda x, y, z, t: api.Expression.apply(
                    lambda s1, s2, s, e: str.find, x, y, z, t
                ),
            },
            int,
            "str.find",
            self._expression,
            sub,
            start,
            end,
        )

    def rfind(
        self,
        sub: Union[expr.ColumnExpression, str],
        start: Optional[Union[expr.ColumnExpression, int]] = None,
        end: Optional[Union[expr.ColumnExpression, int]] = None,
    ) -> expr.ColumnExpression:
        """Return the highest index in the string where substring sub is found within
        the slice s[start:end]. Optional arguments start and end are interpreted as in
        slice notation. Return -1 if sub is not found.


        Example:

        >>> import pathway as pw
        >>> table = pw.debug.table_from_markdown(
        ...     '''
        ...      | name
        ...    1 | Alice
        ...    2 | Hello
        ...    3 | World
        ...    4 | Zoo
        ... '''
        ... )
        >>> table += table.select(count=table.name.str.rfind("o"))
        >>> pw.debug.compute_and_print(table, include_id=False)
        name  | count
        Alice | -1
        Hello | 4
        World | 1
        Zoo   | 2
        """

        if start is None and end is None:
            return expr.MethodCallExpression.with_static_type(
                {
                    (str, str): lambda x, y: api.Expression.apply(str.rfind, x, y),
                },
                int,
                "str.rfind",
                self._expression,
                sub,
            )

        if end is None:
            return expr.MethodCallExpression.with_static_type(
                {
                    (str, str, int): lambda x, y, z: api.Expression.apply(
                        str.rfind, x, y, z
                    ),
                },
                int,
                "str.rfind",
                self._expression,
                sub,
                start,
            )

        if start is None:
            raise ValueError("str.rfind: missing end argument.")

        return expr.MethodCallExpression.with_static_type(
            {
                (str, str, int, int): lambda x, y, z, t: api.Expression.apply(
                    str.rfind, x, y, z, t
                ),
            },
            int,
            "str.rfind",
            self._expression,
            sub,
            start,
            end,
        )

    def removeprefix(
        self,
        prefix: Union[expr.ColumnExpression, str],
        /,
    ) -> expr.ColumnExpression:
        """If the string starts with prefix, returns a copy of the string without the prefix.
        Otherwise returns the original string.

        Example:

        >>> import pathway as pw
        >>> table = pw.debug.table_from_markdown(
        ...     '''
        ...      | name
        ...    1 | Alice
        ...    2 | Bob
        ...    3 | CAROLE
        ...    4 | david
        ... '''
        ... )
        >>> table += table.select(without_da=table.name.str.removeprefix("da"))
        >>> pw.debug.compute_and_print(table, include_id=False)
        name   | without_da
        Alice  | Alice
        Bob    | Bob
        CAROLE | CAROLE
        david  | vid
        >>> table = pw.debug.table_from_markdown(
        ...     '''
        ...      | note | prefix
        ...    1 | AAA  | A
        ...    2 | BB   | B
        ... '''
        ... )
        >>> table = table.select(
        ...    pw.this.note,
        ...    new_note=pw.this.note.str.removeprefix(pw.this.prefix)
        ... )
        >>> pw.debug.compute_and_print(table, include_id=False)
        note | new_note
        AAA  | AA
        BB   | B
        """

        return expr.MethodCallExpression.with_static_type(
            {
                (str, str): lambda x, y: api.Expression.apply(str.removeprefix, x, y),
            },
            str,
            "str.remove_prefix",
            self._expression,
            prefix,
        )

    def removesuffix(
        self,
        suffix: Union[expr.ColumnExpression, str],
        /,
    ) -> expr.ColumnExpression:
        """If the string ends with suffix, returns a copy of the string without the suffix.
        Otherwise returns the original string.

        Example:

        >>> import pathway as pw
        >>> table = pw.debug.table_from_markdown(
        ...     '''
        ...      | name
        ...    1 | Alice
        ...    2 | Bob
        ...    3 | CAROLE
        ...    4 | david
        ... '''
        ... )
        >>> table += table.select(without_LE=table.name.str.removesuffix("LE"))
        >>> pw.debug.compute_and_print(table, include_id=False)
        name   | without_LE
        Alice  | Alice
        Bob    | Bob
        CAROLE | CARO
        david  | david
        >>> table = pw.debug.table_from_markdown(
        ...     '''
        ...      | fruit  | suffix
        ...    1 | bamboo | o
        ...    2 | banana | na
        ... '''
        ... )
        >>> table = table.select(
        ...    pw.this.fruit,
        ...    fruit_cropped=pw.this.fruit.str.removesuffix(pw.this.suffix)
        ... )
        >>> pw.debug.compute_and_print(table, include_id=False)
        fruit  | fruit_cropped
        bamboo | bambo
        banana | bana
        """

        return expr.MethodCallExpression.with_static_type(
            {
                (str, str): lambda x, y: api.Expression.apply(str.removesuffix, x, y),
            },
            str,
            "str.remove_suffix",
            self._expression,
            suffix,
        )

    def slice(
        self,
        start: Union[expr.ColumnExpression, int],
        end: Union[expr.ColumnExpression, int],
        /,
    ) -> expr.ColumnExpression:
        """Return a slice of the string.

        Example:

        >>> import pathway as pw
        >>> table = pw.debug.table_from_markdown(
        ...     '''
        ...      | name
        ...    1 | Alice
        ...    2 | Bob
        ...    3 | CAROLE
        ...    4 | david
        ... '''
        ... )
        >>> table += table.select(slice=table.name.str.slice(1,4))
        >>> pw.debug.compute_and_print(table, include_id=False)
        name   | slice
        Alice  | lic
        Bob    | ob
        CAROLE | ARO
        david  | avi
        """

        return expr.MethodCallExpression.with_static_type(
            {
                (str, int, int): lambda x, y, z: api.Expression.apply(
                    lambda s, slice_start, slice_end: s[slice_start:slice_end], x, y, z
                ),
            },
            str,
            "str.slice",
            self._expression,
            start,
            end,
        )
