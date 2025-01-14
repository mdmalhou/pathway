# Copyright © 2023 Pathway

from __future__ import annotations

from pathway.engine import ElasticSearchAuth as PwElasticSearchAuth
from pathway.engine import ElasticSearchParams
from pathway.internals import api, datasink
from pathway.internals._io_helpers import _format_output_value_fields
from pathway.internals.runtime_type_check import runtime_type_check
from pathway.internals.table import Table
from pathway.internals.trace import trace_user_frame


class ElasticSearchAuth:
    def __init__(self, engine_es_auth: PwElasticSearchAuth) -> None:
        self._engine_es_auth = engine_es_auth

    @classmethod
    def apikey(cls, apikey_id, apikey):
        return cls(
            PwElasticSearchAuth(
                "apikey",
                apikey_id=apikey_id,
                apikey=apikey,
            )
        )

    @classmethod
    def basic(cls, username, password):
        return cls(
            PwElasticSearchAuth(
                "basic",
                username=username,
                password=password,
            )
        )

    @classmethod
    def bearer(cls, bearer):
        return cls(
            PwElasticSearchAuth(
                "bearer",
                bearer=bearer,
            )
        )

    @property
    def engine_es_auth(self) -> PwElasticSearchAuth:
        return self._engine_es_auth


@runtime_type_check
@trace_user_frame
def write(table: Table, host: str, auth: ElasticSearchAuth, index_name: str) -> None:
    """Write a table to a given index in ElasticSearch.

    Args:
        table: the table to output.
        host: the host and port, on which Elasticsearch server works.
        auth: credentials for Elasticsearch authorization.
        index_name: name of the index, which gets the docs.

    Returns:
        None

    Example:

    Consider there is an instance of Elasticsearch, running locally on a port 9200.
    There we have an index "animals", containing an information about pets and their
    owners.

    For the sake of simplicity we will also consider that the cluster has a simple
    username-password authentication having both username and password equal to "admin".

    Now suppose we want to send a Pathway table pets to this local instance of
    Elasticsearch.

    It can be done as follows:

    >>> import pathway as pw
    >>> t = pw.io.elasticsearch.write(
    ...     table=pets,
    ...     host="http://localhost:9200",
    ...     auth=pw.io.elasticsearch.ElasticSearchAuth.basic("admin", "admin"),
    ...     index_name="animals",
    ... )

    All the updates of table t will be indexed to "animals" as well.
    """

    data_storage = api.DataStorage(
        storage_type="elasticsearch",
        elasticsearch_params=ElasticSearchParams(
            host=host,
            index_name=index_name,
            auth=auth.engine_es_auth,
        ),
    )

    data_format = api.DataFormat(
        format_type="jsonlines",
        key_field_names=[],
        value_fields=_format_output_value_fields(table),
    )

    table.to(
        datasink.GenericDataSink(
            data_storage,
            data_format,
        )
    )
