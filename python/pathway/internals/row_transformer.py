# Copyright © 2023 Pathway

from __future__ import annotations

from abc import ABC, abstractmethod
from functools import cached_property, lru_cache
from typing import TYPE_CHECKING, Any, Callable, Dict, Tuple, Type

import pathway
import pathway.internals.row_transformer_table as tt
from pathway.internals import operator as op
from pathway.internals import parse_graph, schema
from pathway.internals.api import BasePointer, ref_scalar
from pathway.internals.column import MaterializedColumn, MethodColumn
from pathway.internals.dtype import DType
from pathway.internals.schema import Schema, schema_from_types
from pathway.internals.shadows import inspect

if TYPE_CHECKING:
    from pathway import Table
    from pathway.internals.api import Pointer
    from pathway.internals.graph_runner.row_transformer_operator_handler import (
        RowReference,
    )
    from pathway.internals.universe import Universe


class RowTransformer:
    args: Dict[str, Type[ClassArg]]
    name: str

    def __init__(self, name, args, **kwargs) -> None:
        assert len(kwargs) == 0
        self.name = name
        self.args = args
        for index, class_arg in enumerate(self.class_args.values()):
            class_arg.transformer = self
            class_arg._index = index

    @classmethod
    def from_class(cls, transformer_cls) -> RowTransformer:
        args = {arg.name: arg for arg in attrs_of_type(transformer_cls, type(ClassArg))}
        return cls(transformer_cls.__name__, args)

    def __call__(self, *args, **kwargs):
        matched_args = self._match_args_to_properties(args, kwargs)

        tables = {
            name: arg for name, arg in matched_args.items() if name in self.class_args
        }

        assert len(tables) == len(self.class_args)

        return parse_graph.G.add_operator(
            lambda id: op.RowTransformerOperator(id, self),
            lambda operator: operator(tables),  # type: ignore
        )

    @cached_property
    def class_args(self) -> Dict[str, Type[ClassArg]]:
        return {
            name: arg for name, arg in self.args.items() if issubclass(arg, ClassArg)
        }

    def _match_args_to_properties(
        self, args: Tuple[Any, ...], kwargs: Dict[str, Any]
    ) -> Dict[str, Any]:
        result = {}
        for arg, (param_name, param) in zip(args, self.args.items()):
            assert param_name not in kwargs
            result[param_name] = arg
        result.update(kwargs)
        for arg, (param_name, param) in zip(result, self.args.items()):
            if isinstance(arg, pathway.Table):
                assert issubclass(param, ClassArg)
        return result

    @classmethod
    @lru_cache
    def method_call_transformer(cls, n, dtype: DType):
        arg_names = [f"arg_{i}" for i in range(n)]

        def func(self):
            return self.method(*(getattr(self, name) for name in arg_names))

        table_arg = ClassArgMeta(
            "table_arg",
            (ClassArg,),
            {
                "method": InputMethod(dtype=dtype),
                **{name: InputAttribute() for name in arg_names},
                "result": OutputAttribute(func, dtype=dtype),
            },
        )
        table_arg.name = "table"

        return cls(f"call_method_{n}", {"table": table_arg})

    def __getattr__(self, item):
        if item == "__wrapped__":
            return self.__getattribute__(item)
        try:
            return self.class_args[item]
        except KeyError:
            raise NotImplementedError("TODO")


class ClassArgMeta(type):
    input_schema: Type[Schema]
    output_schema: Type[Schema]

    name: str  # lateinit by __set_name__
    _index: int  # lateinit by parent RowTransformer
    transformer: RowTransformer

    _attributes: Dict[str, AbstractAttribute]

    @property
    def _output_attributes(self) -> Dict[str, AbstractOutputAttribute]:
        return {
            name: attr
            for name, attr in self._attributes.items()
            if isinstance(attr, AbstractOutputAttribute)
        }

    def _is_attribute(self, col_name: str) -> bool:
        return col_name in self._attributes

    def _get_attribute(self, col_name: str) -> AbstractAttribute:
        return self._attributes[col_name]

    def _get_class_property(self, name: str) -> Any:
        assert name not in self._attributes
        return inspect.getattr_static(self, name)

    def __set_name__(self, owner, name):
        self.name: str = name

    def __call__(self, ref: RowReference, ptr: Pointer) -> RowReference:  # type: ignore
        if ref._class_arg.transformer != self.transformer:
            raise ValueError(
                "creating a reference to a class_arg table defined for another transformer"
            )

        return ref._with_class_arg(self, ptr)


class ClassArg(metaclass=ClassArgMeta):
    """Base class to inherit from when writing inner classes for class transformers.

    Example:

    >>> import pathway as pw
    >>> @pw.transformer
    ... class simple_transformer:
    ...     class table(pw.ClassArg):
    ...         arg = pw.input_attribute()
    ...         @pw.output_attribute
    ...         def ret(self) -> int:
    ...             return self.arg + 1
    >>> t1 = pw.debug.parse_to_table('''
    ... age
    ... 10
    ... 9
    ... 8
    ... 7
    ... ''')
    >>> t2 = simple_transformer(table=t1.select(arg=t1.age)).table
    >>> pw.debug.compute_and_print(t1 + t2, include_id=False)
    age | ret
    7   | 8
    8   | 9
    9   | 10
    10  | 11
    """

    transformer: RowTransformer  # stub for mypy
    id: Pointer  # stub for mypy

    def pointer_from(self, *args, optional=False) -> BasePointer:
        """Pseudo-random hash of its argument. Produces pointer types. Applied value-wise."""
        return ref_scalar(*args, optional=optional)

    def __init_subclass__(
        cls,
        input=Any,
        output=Any,
    ):
        cls._attributes = {
            attr.name: attr for attr in attrs_of_type(cls, AbstractAttribute)
        }
        cls.input_schema = input
        cls.output_schema = schema_from_types(
            **{attr.output_name: attr.dtype for attr in cls._output_attributes.values()}
        )
        if output is not Any and not schema.is_subschema(cls.output_schema, output):
            raise RuntimeError(
                f"output schema validation error, received {output.as_dict()} vs expected {cls.output_schema.as_dict()}"  # noqa
            )
        for attr in cls._attributes.values():
            attr.class_arg = cls


class AbstractAttribute(ABC):
    is_method = False
    is_output = False
    class_arg: ClassArgMeta  # lateinit by parent ClassArg

    def __init__(self, **params) -> None:
        super().__init__()
        self.params = params
        self.name = self.params.get("name", None)
        if "dtype" in self.params:
            self._dtype = self.params["dtype"]

    def __set_name__(self, owner, name):
        assert self.name is None
        self.name = name

    @abstractmethod
    def to_transformer_column(
        self, operator: op.RowTransformerOperator, input_table: Table
    ):
        pass

    @property
    def dtype(self) -> DType:
        return DType(Any)


class ToBeComputedAttribute(AbstractAttribute, ABC):
    def __init__(self, func, **params):
        super().__init__(**params)
        assert func is not None
        self.func = func
        self.__doc__ = func.__doc__

    def compute(self, context, *args):
        assert not args, "calling non-method attribute with args"
        return self.func(context)

    @property
    def output_name(self):
        return self.params.get("output_name", self.name)

    @cached_property
    def dtype(self) -> DType:
        if hasattr(self, "_dtype"):
            return self._dtype
        else:
            assert self.func is not None
            sig = inspect.signature(self.func)
            return sig.return_annotation


class AbstractOutputAttribute(ToBeComputedAttribute, ABC):
    is_output = True

    def to_output_column(self, universe: Universe):
        return MaterializedColumn(self.dtype, universe)


class Attribute(ToBeComputedAttribute):
    def to_transformer_column(
        self, operator: op.RowTransformerOperator, input_table: Table
    ):
        return tt.ToBeComputedTransformerColumn(self, operator)


class OutputAttribute(AbstractOutputAttribute):
    def to_transformer_column(
        self, operator: op.RowTransformerOperator, input_table: Table
    ):
        return tt.OutputAttributeTransformerColumn(self, operator)


class Method(AbstractOutputAttribute):
    is_method = True

    def compute(self, context, *args):
        return self.func(context, *args)

    def to_transformer_column(
        self, operator: op.RowTransformerOperator, input_table: Table
    ):
        return tt.MethodTransformerColumn(self, operator)

    def to_output_column(self, universe: Universe):
        return MethodColumn(self.dtype, universe)

    @cached_property
    def dtype(self) -> DType:
        return DType(Callable[..., super().dtype])


class InputAttribute(AbstractAttribute):
    def to_transformer_column(
        self, operator: op.RowTransformerOperator, input_table: Table
    ):
        return tt.InputAttributeTransformerColumn(self, operator, input_table)


class InputMethod(AbstractAttribute):
    is_method = True

    def to_transformer_column(
        self, operator: op.RowTransformerOperator, input_table: Table
    ):
        return tt.InputMethodTransformerColumn(self, operator, input_table)


def attrs_of_type(cls: Type, type_: Type):
    for name in dir(cls):
        attr = getattr(cls, name)
        if isinstance(attr, type_):
            assert name == attr.name
            yield attr
