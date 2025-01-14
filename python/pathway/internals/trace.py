# Copyright © 2023 Pathway

from __future__ import annotations

import contextlib
import functools
import traceback
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from pathway.internals import api


@dataclass
class Frame:
    filename: str
    line_number: Optional[int]
    line: Optional[str]
    function: str

    def is_external(self) -> bool:
        if "pathway/tests/test_" in self.filename:
            return True
        exclude_patterns = [
            "pathway/tests",
            "pathway/internals",
            "pathway/io",
            "pathway/stdlib",
            "pathway/debug",
            "@beartype",
        ]
        return all(pattern not in self.filename for pattern in exclude_patterns)

    def is_marker(self) -> bool:
        return self.function == "_pathway_trace_marker"


@dataclass
class Trace:
    frames: List[Frame]
    user_frame: Optional[Frame]

    @staticmethod
    def from_traceback():
        frames = [
            Frame(
                filename=e.filename,
                line_number=e.lineno,
                line=e.line,
                function=e.name,
            )
            for e in traceback.extract_stack()[:-1]
        ]

        user_frame: Optional[Frame] = None
        for frame in frames:
            if frame.is_marker():
                break
            elif frame.is_external():
                user_frame = frame

        return Trace(frames=frames, user_frame=user_frame)

    def to_engine(self) -> Optional[api.PyTrace]:
        user_frame = self.user_frame
        if (
            user_frame is None
            or user_frame.line_number is None
            or user_frame.line is None
        ):
            return None
        else:
            from pathway.internals import api

            return api.PyTrace(
                file_name=user_frame.filename,
                line_number=user_frame.line_number,
                line=user_frame.line,
            )


def _format_frame(frame: Frame) -> str:
    return f"""Occurred here:
    Line: {frame.line}
    File: {frame.filename}:{frame.line_number}"""


def _reraise_with_user_frame(e: Exception, trace: Optional[Trace] = None):
    if hasattr(e, "__pathway_wrapped__"):
        raise e

    if trace is None:
        trace = Trace.from_traceback()

    user_frame = trace.user_frame

    if user_frame is None:
        raise e
    else:
        error_type = type(e)

        class Wrapper(error_type):  # type: ignore
            __name__ = error_type.__name__
            __qualname__ = error_type.__qualname__
            __module__ = error_type.__module__
            __pathway_wrapped__ = e

            __repr__ = Exception.__repr__
            __str__ = Exception.__str__

            def __init__(self, msg: str):
                Exception.__init__(self, msg)

        message = f"{e}\n{_format_frame(user_frame)}"

        traceback = e.__traceback__
        if traceback is not None:
            traceback = traceback.tb_next

        raise Wrapper(message).with_traceback(traceback) from e.__cause__


def trace_user_frame(func):
    @functools.wraps(func)
    def _pathway_trace_marker(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            _reraise_with_user_frame(e)

    return _pathway_trace_marker


@contextlib.contextmanager
def custom_trace(trace: Trace):
    try:
        yield
    except Exception as e:
        _reraise_with_user_frame(e, trace)
