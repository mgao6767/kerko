"""Update the search index from the local cache."""

from flask import current_app
from elasticsearch import Elasticsearch, helpers
from whoosh.query import Term

from kerko.shortcuts import composer, config
from kerko.storage import SearchIndexError, load_object, save_object, open_index
from kerko.sync.index_es_setting import INDEX_SETTING
from kerko.tags import TagGate


def init_elasticsearch():
    es = Elasticsearch([{"host": "localhost", "port": 9200, "scheme": "http"}])
    index_name = "index"
    # Create the new index if it doesn't exist
    if not es.indices.exists(index=index_name):
        es.indices.create(index=index_name, body=INDEX_SETTING)
    return es, index_name


def sync_index(full=False):  # noqa: ARG001
    """
    Build the search index from the local cache.

    Return the number of synchronized items.
    """
    current_app.logger.info("Starting index sync...")
    library_context = load_object("cache", "library")

    es, index_name = init_elasticsearch()
    cache = open_index("cache")
    cache_version = load_object("cache", "version", default=0)
    if not cache_version:
        msg = "The cache is empty and needs to be synchronized first."
        raise SearchIndexError(msg)

    def yield_items(parent_key):
        with cache.searcher() as searcher:
            results = searcher.search(Term("parentItem", parent_key), limit=None)
            for hit in results:
                yield hit.fields()

    def yield_top_level_items():
        return yield_items("")

    def yield_children(parent):
        return yield_items(parent["key"])

    count = 0
    actions = []
    gate = TagGate(
        config("kerko.zotero.item_include_re"),
        config("kerko.zotero.item_exclude_re"),
    )
    for item in yield_top_level_items():
        count += 1
        if gate.check(item["data"]):
            item["children"] = list(yield_children(item))  # Extend the base Zotero item dict.
            document = {}
            for spec in list(composer().fields.values()) + list(composer().facets.values()):
                spec.extract_to_document(document, item, library_context)
            actions.append({
                "_index": index_name,
                "_id": item["key"],
                "_source": document
            })

    if actions:
        try:
            helpers.bulk(es, actions)
        except helpers.BulkIndexError as e:
            current_app.logger.error(f"Bulk indexing error: {e}")
            for error in e.errors:
                current_app.logger.error(f"Failed document: {error}")

    save_object("index", "version", cache_version)
    current_app.logger.info(f"Index sync completed with {count} items synchronized.")

    return count