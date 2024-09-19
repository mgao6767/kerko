from abc import ABC, abstractmethod
from collections.abc import Iterable

from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search, Q

from kerko.exceptions import except_raise
from kerko.shortcuts import composer
from kerko.storage import SchemaError


class Searcher:
    """
    Provide a convenient API for searching using Elasticsearch.
    """

    def __init__(self, index="index", schema=None, field_specs=None, facet_specs=None):
        self.client = Elasticsearch("http://localhost:9200/")
        self.index = index
        self.schema = schema or composer().schema
        self.field_specs = field_specs or composer().fields
        self.facet_specs = {  # Reorganize by filter key instead of spec key.
            f.filter_key: f
            for f in (
                facet_specs.values() if facet_specs else composer().facets.values()
            )
        }
        self.search_args = {}  # Arguments to pass to Elasticsearch's searcher.

    def close(self):
        self.client.transport.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def _prepare_search_args(
        self,
        *,
        keywords=None,
        filters=None,
        require_all=None,
        require_any=None,
        require_date_ranges=None,
        reject_any=None,
        sort_spec=None,
        faceting=False,
    ):
        """
        Prepare search arguments.

        :param bool faceting: Whether to compute groupings along with the search
            results.
        """
        self._prepare_keywords(keywords)
        self._prepare_filters(
            filters, require_all, require_any, require_date_ranges, reject_any
        )
        self._prepare_sorting(sort_spec)
        if faceting:
            self._prepare_faceting()

    def _prepare_keywords(self, keywords=None):
        """
        Prepare query parsers and filters.

        :param MultiDict keywords: The search texts keyed by scope key. If falsy,
            the query will match every document.
        """
        if keywords:
            queries = []
            for key, value in keywords.items(multi=True):
                fields = [
                    field_spec.key
                    for field_spec in self.field_specs.values()
                    if key in field_spec.scopes
                ]
                if not fields:
                    raise KeyError  # No known field for that scope key.
                queries.append(Q("multi_match", query=value, fields=fields))
            self.search_args["query"] = Q("bool", must=queries)
        else:
            self.search_args["query"] = Q("match_all")

    def _prepare_filters(
        self,
        filters=None,
        require_all=None,
        require_any=None,
        require_date_ranges=None,
        reject_any=None,
    ):
        """
        Prepare query filtering terms.

        :param MultiDict filters: The facet filters to apply keyed by filter
            key. If falsy, no filters will be applied.

        :param dict require_all: Values that are all required to match, that
            will be combined to the search with the `And` boolean search
            operator. Each key must correspond to a schema field name. The value
            must be a list of one or more accepted values (which will be
            combined together with a nested `Or` boolean search operator).

        :param dict require_any: A dict of inclusion filters, where the key and
            value are, respectively, the schema field name and the list of field
            values to allow in the search results. Any match will allow an item
            in the results, but at least one match is required (values are
            expanded to a flat list of field, value pairs, which are combined
            with the `Or` boolean search operator).

        :param dict reject_any: A dict of exclusion filters, where the key and
            value are, respectively, the schema field name and a list of one or
            more field values to reject. Any match will cause an item to be
            rejected from the results (values are expanded to a flat list of
            field, value pairs, which are combined with the `And` and `Not`
            boolean search operators).

        :param dict require_date_ranges: A dict of date ranges that are all
            required to match. Each key and value are, respectively, the schema
            field name and a tuple with start and end `datetime` objects (the
            range may be open at either end, using `None` instead of a
            `datetime` instance). Items falling outside the date range will be
            rejected from the results.
        """
        terms = []
        if require_all:
            for field_key in require_all.keys() & self.field_specs.keys():
                terms.append(Q("terms", **{field_key: require_all[field_key]}))
        if require_any:
            terms.append(
                Q(
                    "bool",
                    should=[
                        Q("terms", **{field_name: allow_values})
                        for field_name, allow_values in require_any.items()
                        if field_name in self.field_specs.keys()
                    ],
                )
            )
        if require_date_ranges:
            for field_key in require_date_ranges.keys() & self.field_specs.keys():
                start, end = require_date_ranges[field_key]
                terms.append(Q("range", **{field_key: {"gte": start, "lte": end}}))
        if reject_any:
            for field_name, reject_values in reject_any.items():
                if field_name in self.field_specs.keys():
                    terms.extend(
                        [
                            Q("bool", must_not=[Q("term", **{field_name: value})])
                            for value in reject_values
                        ]
                    )
        if filters:
            for filter_key, filter_values in filters.lists():
                spec = self.facet_specs.get(filter_key)
                if spec:
                    for v in filter_values:
                        if v == "":  # If trying to filter with a missing value.
                            # Exclude all results with a value in facet field.
                            terms.append(
                                Q("bool", must_not=[Q("exists", field=spec.key)])
                            )
                        else:
                            v = spec.codec.transform_for_query(v)  # noqa: PLW2901
                            # TODO: In Whoosh version, either Terms or Prefix was used.
                            # For now, use "prefix" for everything.
                            terms.append(Q("prefix", **{f"{spec.key}.keyword": v}))
        if terms:
            self.search_args["filter"] = Q("bool", filter=terms)

    def _prepare_sorting(self, sort_spec=None):
        if sort_spec and sort_spec.fields:
            if isinstance(sort_spec.reverse, Iterable):
                sort_orders = [
                    {"order": "desc" if reverse else "asc"}
                    for reverse in sort_spec.reverse
                ]
            else:
                sort_orders = [{"order": "desc" if sort_spec.reverse else "asc"}] * len(
                    sort_spec.fields
                )
            self.search_args["sort"] = [
                {
                    (
                        field_key if "date" in field_key else f"{field_key}.keyword"
                    ): sort_order
                }
                for field_key, sort_order in zip(
                    sort_spec.get_field_keys(), sort_orders
                )
            ]

    def _prepare_faceting(self):
        self.search_args["aggs"] = {
            facet_spec.key: {
                # A large `size` so to retrieve all items under a facet.
                # TODO: Determine `size`.
                "terms": {"field": f"{facet_spec.key}.keyword", "size": 10000}
            }
            for facet_spec in self.facet_specs.values()
        }

    @except_raise(
        KeyError, SchemaError, "Schema changes are required. Please clean index."
    )
    def search(self, *, limit=None, **kwargs):
        self._prepare_search_args(**kwargs)
        search = (
            Search(using=self.client, index=self.index)
            .query(self.search_args["query"])
            .extra(track_total_hits=True)
        )
        if "filter" in self.search_args:
            search = search.filter(self.search_args["filter"])
        if "sort" in self.search_args:
            search = search.sort(*self.search_args["sort"])
        if "aggs" in self.search_args:
            search = search.update_from_dict({"aggs": self.search_args["aggs"]})
        response = search[0:limit].execute()
        return UnpagedResults(response)

    @except_raise(
        KeyError, SchemaError, "Schema changes are required. Please clean index."
    )
    def search_page(self, *, page, page_len, **kwargs):
        self._prepare_search_args(**kwargs)
        search = (
            Search(using=self.client, index=self.index)
            .query(self.search_args["query"])
            .extra(track_total_hits=True)
        )
        if "filter" in self.search_args:
            search = search.filter(self.search_args["filter"])
        if "sort" in self.search_args:
            search = search.sort(*self.search_args["sort"])
        if "aggs" in self.search_args:
            search = search.update_from_dict({"aggs": self.search_args["aggs"]})
        start = (page - 1) * page_len
        response = search[start : start + page_len].execute()
        return PagedResults(response, page_len)


class SearcherSingleton(Searcher):
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(SearcherSingleton, cls).__new__(cls)
        return cls._instance

    def __init__(self, schema=None, field_specs=None, facet_specs=None):
        if not self._initialized:
            super().__init__("index", schema, field_specs, facet_specs)
            self._initialized = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Do not close the searcher
        pass


class Results(ABC):
    def __init__(self, response):
        self._response = response

    def __iter__(self):
        """Yield a `elasticsearch_dsl.response.hit.Hit` object for each result in ranked order."""
        return (hit.to_dict() for hit in self._response.hits)

    def __getitem__(self, n):
        return self._response.hits[n].to_dict()

    def __len__(self):
        return len(self._response.hits)

    def is_empty(self):
        return len(self._response.hits) == 0

    def __nonzero__(self):
        return not self.is_empty()

    __bool__ = __nonzero__

    @property
    @abstractmethod
    def page_count(self):
        pass

    @property
    @abstractmethod
    def item_count(self):
        pass

    def items(self, field_specs, facet_specs=None):
        """
        Load items from search results.

        :param dict field_specs: The specifications of the fields to load into
            each item. Any requested field that is not present in a result is
            silently ignored for that result.

        :param dict facet_specs: The specifications of the facets to load into
            each item. Any requested facet that is not present in a result is
            silently ignored for that result.
        """
        return [
            self._item(hit, field_specs, facet_specs) for hit in self._response.hits
        ]

    def facets(self, facet_specs, criteria, active_only=False):
        """
        Load facets from search results.

        This may be called only while the searcher object is still alive.

        :param dict facet_specs: The specifications of the facets to load. Any
            requested facet that doesn't have a corresponding grouping in the
            search results is silently ignored.
        """
        return {
            key: facet_specs[key].build(self._groups(key), criteria, active_only)
            for key in facet_specs.keys() & self._facet_names()
        }

    @staticmethod
    def _item(hit, field_specs, facet_specs=None):
        """
        Copy specified fields from a `elasticsearch_dsl.response.hit.Hit` object into a `dict`.
        """
        hit = hit.to_dict()
        facet_specs = facet_specs or {}
        return {
            **{
                key: field_specs[key].decode(hit[key])
                for key in field_specs.keys() & hit.keys()
            },
            **{key: hit[key] for key in facet_specs.keys() & hit.keys()},
        }

    @abstractmethod
    def _groups(self, name=None):
        """
        Return groups resulting from the 'aggregations' search argument.
        """

    @abstractmethod
    def _facet_names(self):
        pass


class UnpagedResults(Results):
    """Interface results from an Elasticsearch response object."""

    @property
    def page_count(self):
        return 1

    @property
    def item_count(self):
        return len(self._response.hits)

    def _groups(self, name=None):
        if name:
            return {
                d["key"]: d["doc_count"]
                for d in self._response.aggregations[name].buckets
            }
        return self._response.aggregations

    def _facet_names(self):
        return self._response.aggregations.keys()


class PagedResults(Results):
    """Interface paged results from an Elasticsearch response object."""

    def __init__(self, results, page_len):
        super().__init__(results)
        self.page_len = page_len

    @property
    def page_count(self):
        return (self._response.hits.total.value + self.page_len - 1) // self.page_len

    @property
    def item_count(self):

        return self._response.hits.total.value

    def _groups(self, name=None):
        if name:
            # Ensure all docs are retrieved to build facets.
            assert self._response.aggregations[name].sum_other_doc_count == 0
            return {
                d["key"]: d["doc_count"]
                for d in self._response.aggregations[name].buckets
            }
        return self._response.aggregations

    def _facet_names(self):
        return self._response.aggregations.keys()
