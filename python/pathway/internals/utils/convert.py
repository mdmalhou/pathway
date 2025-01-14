# Copyright © 2023 Pathway

from datetime import datetime, timedelta
from typing import Tuple

import pandas as pd
from dateutil import tz

MICROSECOND = timedelta(microseconds=1)


def _datetime_to_rust(dt: datetime) -> Tuple[int, bool]:
    """Returns (timestamp [ns], is_timezone_aware)"""
    tz_aware = dt.tzinfo is not None
    epoch = datetime(1970, 1, 1)
    if tz_aware:
        epoch = epoch.replace(tzinfo=tz.UTC)
    return _timedelta_to_rust(dt - epoch), tz_aware


def _timedelta_to_rust(td: timedelta) -> int:
    """Returns duration in ns"""
    return (td // MICROSECOND) * 1000


def _pd_timestamp_to_rust(ts: pd.Timestamp) -> Tuple[int, bool]:
    """Returns (timestamp [ns], is_timezone_aware)"""
    return ts.value, ts.tz is not None


def _pd_timedelta_to_rust(td: pd.Timedelta) -> int:
    """Returns duration in ns"""
    return td.value


def _pd_timestamp_from_naive_ns(timestamp: int) -> pd.Timestamp:
    """Accepts timestamp in ns"""
    return pd.Timestamp(timestamp, tz=None)


def _pd_timestamp_from_utc_ns(timestamp: int) -> pd.Timestamp:
    """Accepts timestamp in ns"""
    return pd.Timestamp(timestamp, tz=tz.UTC)


def _pd_timedelta_from_ns(duration: int) -> pd.Timedelta:
    """Accepts duration in ns"""
    return pd.Timedelta(duration)
