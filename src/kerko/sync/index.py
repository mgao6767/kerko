"""Update the search index from the local cache."""

import os

import whoosh
from flask import current_app
from whoosh.query import Term

from kerko.extractors import ItemTitleExtractor
from kerko.searcher import SearcherSingleton, UnpagedResults
from kerko.shortcuts import composer, config
from kerko.storage import SchemaError, SearchIndexError, load_object, open_index, save_object
from kerko.tags import TagGate


def sync_index(full=False):  # noqa: ARG001
    """
    Build the search index from the local cache.

    Return the number of synchronized items.
    """
    current_app.logger.info("Starting index sync...")
    library_context = load_object("cache", "library")

    cache = open_index("cache")
    cache_version = load_object("cache", "version", default=0)
    if not cache_version:
        msg = "The cache is empty and needs to be synchronized first."
        raise SearchIndexError(msg)

    # FIXME: The following does not detect when just the collections have changed in the cache
    #        (with no item changes). Should check the collections_version!
    #        https://pyzotero.readthedocs.io/en/latest/#zotero.Zotero.collection_versions
    # if not full and load_object('index', 'version', default=0) == cache_version:
    #     current_app.logger.warning(
    #         f"The index is already up-to-date with cache version {cache_version}, nothing to do."
    #     )
    #     return 0
    def has_diff_value_for_common_keys(dict1, dict2):
        # Keys present in both but with different values
        for k in dict1.keys() & dict2.keys():
            if dict1[k] != dict2[k]:
                return True
        return False

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
    index = open_index("index", schema=composer().schema, auto_create=True, write=True)
    writer = index.writer(
        limitmb=config("kerko.performance.whoosh_index_memory_limit"),
        procs=config("kerko.performance.whoosh_index_processors"),
    )
    try:
        # writer.mergetype = whoosh.writing.CLEAR
        gate = TagGate(
            config("kerko.zotero.item_include_re"),
            config("kerko.zotero.item_exclude_re"),
        )
        searcher = SearcherSingleton().searcher
        for item in yield_top_level_items():
            if gate.check(item["data"]):
                item["children"] = list(yield_children(item))  # Extend the base Zotero item dict.
                document = {}
                for spec in list(composer().fields.values()) + list(composer().facets.values()):
                    spec.extract_to_document(document, item, library_context)
                results = searcher.search(q=Term("id", document["id"]), limit=1)
                if len(results):
                    result = UnpagedResults(results).items(composer().fields).pop()
                    if not has_diff_value_for_common_keys(document, result):
                        current_app.logger.debug(f"No change to document {document['id']}.")
                        continue
                count += 1
                writer.update_document(**document)
                current_app.logger.debug(
                    f"Item {count} updated ({item['key']}, {item.get('itemType')}): "
                    f"{ItemTitleExtractor().extract(item, library_context, None)}"
                )
                # Commit after 500 items.
                # Recreate the writer because it closes after commit.
                # Cannot set `writer.mergetype` to `whoosh.writing.CLEAR`,
                # because this would clear existing index.
                # Removing it has no impact since `update_document` deletes old
                # then adds new doc with the same key.
                if count % 500 == 0:
                    writer.commit()
                    current_app.logger.info(f"Item {count} updated.")
                    writer = index.writer(
                        limitmb=config("kerko.performance.whoosh_index_memory_limit"),
                        procs=config("kerko.performance.whoosh_index_processors"),
                    )
            else:
                current_app.logger.debug(f"Item {count} excluded ({item['key']})")
    except (whoosh.fields.FieldConfigurationError, whoosh.fields.UnknownFieldError) as e:
        writer.cancel()
        current_app.logger.error(e)
        msg = "Schema changes are required. Please clean index."
        raise SchemaError(msg) from e
    except Exception:
        writer.cancel()
        raise
    else:
        # This commit takes care of the remaining documents in writer.
        writer.commit()
        # Save the cache's last_modified timestamp. Later, we cannot access the
        # cache directly to show the user when the data was last synchronized
        # from Zotero, because there is no guarantee that what the user's sees
        # (i.e., the current content of the index) is still in sync with the
        # cache (the cache might have been cleaned, or it might have been just
        # updated, with an index update still pending).
        save_object("index", "last_update_from_zotero", cache.last_modified())
        save_object("index", "version", cache_version)
        current_app.logger.info(
            f"Index sync successful, now at version {cache_version} "
            f"({count} top level item(s) processed)."
        )
    finally:
        searcher.close()
        # Clear flask-caching's cache
        if "cache" in current_app.extensions:
            current_app.extensions["cache"].clear()
        # Somehow .clear() leaves one cache file on disk...
        if os.path.exists(".flask_cache"):
            for filename in os.listdir(".flask_cache"):
                file_path = os.path.join(".flask_cache", filename)
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
        current_app.logger.info("Flask cache cleared.")
    return count
