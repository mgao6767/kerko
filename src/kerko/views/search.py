import functools
import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from io import BytesIO

from babel.numbers import format_decimal
from flask import redirect, render_template, url_for
from flask_babel import get_locale, gettext, ngettext
from matplotlib.figure import Figure
from werkzeug.datastructures import MultiDict
from wordcloud import WordCloud, STOPWORDS

from kerko.criteria import create_feed_criteria
from kerko.searcher import SearcherSingleton
from kerko.shortcuts import composer, config
from kerko.sync import kerko_last_sync
from kerko.views import breadbox, pager, sorter
from kerko.views.item import build_item_context, inject_item_data


# Global cache dictionary
facets_cache = {}
MAX_FACETS_CACHE = 256

WORDCLOUD_STOPWORDS = set(STOPWORDS)
# Read additional stopwords from a file
stopwords_file_path = os.path.join(os.path.dirname(__file__), 'additional_stopwords.txt')
if os.path.exists(stopwords_file_path):
    with open(stopwords_file_path, 'r', encoding='utf-8') as file:
        additional_stopwords = [line.strip() for line in file if line.strip()]
    WORDCLOUD_STOPWORDS.update(additional_stopwords)


# Create a ThreadPoolExecutor instance
executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="wordcloud")

wordcloud_dir = os.path.join(os.path.dirname(__file__), '..', 'static', 'wordclouds')
wordcloud_dir_last_cleared = time.time()
os.makedirs(wordcloud_dir, exist_ok=True)

def clean_wordcloud_dir():
    """Clean up the wordcloud directory."""
    for filename in os.listdir(wordcloud_dir):
        file_path = os.path.join(wordcloud_dir, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"Failed to delete {file_path}. Reason: {e}")

clean_wordcloud_dir()


def _build_item_search_urls(items, criteria):
    """Generate an URL for each search result (switching the search to page-len=1)."""

    def build_url(item, position):
        return url_for(
            ".search",
            **criteria.params(
                options={
                    "page": (criteria.options.get("page", 1) - 1) * page_len + position + 1,
                    "page-len": 1,
                    "id": item["id"],
                }
            ),
        )

    page_len = criteria.options.get("page-len", config("kerko.pagination.page_len"))
    if page_len == "all":
        page_len = 0
    return [build_url(item, position) for position, item in enumerate(items)]


def empty_results(criteria, form):
    """Prepare the template context variables for an empty search results page."""
    context = {}
    facets = {}
    context["title"] = gettext("Your search did not match any resources")
    context["total_count"] = context["total_count_formatted"] = 0
    context["page_count"] = context["page_count_formatted"] = 0
    if criteria.has_filters():
        # When search results are empty, Whoosh cannot provide any groupings,
        # thus our facets cannot be built. However, we still want to display the
        # breadbox with active filters, if any. To build that, we perform a
        # separate search query for each active facet, each time ignoring all
        # other search criteria. Unless a given facet value alone leads to empty
        # results, we'll be able to get to build that facet.
        with SearcherSingleton() as searcher:
            for key, value in criteria.filters.lists():
                results = searcher.search(
                    filters=MultiDict({key: value}),
                    reject_any={"item_type": ["note", "attachment"]},
                    limit=1,  # We don't care about the actual items.
                    faceting=True,
                )
                facets.update(results.facets(composer().facets, criteria, active_only=True))
    context["breadbox"] = breadbox.build_breadbox(criteria, facets)
    return render_template(
        config("kerko.templates.search"),
        form=form,
        locale=get_locale(),
        is_searching=criteria.is_searching(),
        **context,
    )


def search_single(criteria, form):
    """Perform search, and prepare template context for a results page containing a single item."""
    start_time = time.process_time()
    context = {}
    with SearcherSingleton() as searcher:
        results = searcher.search_page(
            page=criteria.options.get("page", 1),
            page_len=1,
            keywords=criteria.keywords,
            filters=criteria.filters,
            reject_any={"item_type": ["note", "attachment"]},
            sort_spec=criteria.get_active_sort_spec(),
            faceting=True,
        )

        criteria_id = criteria.options.get("id")
        if criteria_id and (results.is_empty() or criteria_id != results[0]["id"]):
            # The search URL is obsolete, the result no longer matches the expected item.
            return redirect(url_for(".item_view", item_id=criteria_id, _external=True), 301)

        if results.is_empty():
            return empty_results(criteria, form)

        criteria.fit_page(results.page_count)
        if criteria.is_searching():
            context["search_title"] = gettext("Your search")
        else:
            context["search_title"] = gettext("Full bibliography")

        if not criteria_id:
            # Item id is not present in the URL. Inject it into the preferred URL, which will allow
            # this view to redirect to the item page, should the same URL be accessed later but the
            # search results be different.
            context["preferred_url"] = url_for(
                ".search",
                **criteria.params(
                    options={
                        "id": results[0]["id"],
                    },
                ),
            )

        # Load item with all available fields.
        item = results.items(composer().fields, composer().facets, highlight=True)[0]
        facets = results.facets(composer().facets, criteria, active_only=True)

        inject_item_data(item)
        context.update(build_item_context(item))
        context["total_count"] = results.item_count
        context["total_count_formatted"] = format_decimal(results.item_count, locale=get_locale())
        context["page_count"] = results.page_count
        context["page_count_formatted"] = format_decimal(results.page_count, locale=get_locale())
        pager_sections = pager.get_sections(criteria.options["page"], results.page_count)
        context["pager"] = pager.build_pager(pager_sections, criteria)
        context["breadbox"] = breadbox.build_breadbox(criteria, facets)
        context["back_url"] = url_for(
            ".search",
            **criteria.params(
                options={
                    "page": int(
                        (criteria.options.get("page", 1) - 1) / config("kerko.pagination.page_len")
                        + 1
                    ),
                    "page-len": None,
                    "id": None,
                }
            ),
        )
    return render_template(
        config("kerko.templates.search_item"),
        form=form,
        time=time.process_time() - start_time,
        locale=get_locale(),
        is_searching=criteria.is_searching(),
        **context,
    )


def search_list(criteria, form, word_cloud):
    """Perform search, and prepare the template context variables for a list of search results."""
    start_time = time.process_time()
    # _search_list_context has a side effect: `fit_page`
    # For the front page, criteria has no `page` option. This patches it.
    criteria.options["page"] = criteria.options.get("page", 1)
    context = _search_list_context(criteria, word_cloud)
    if context is None:
        return empty_results(criteria, form)
    return render_template(
        config("kerko.templates.search"),
        form=form,
        time=time.process_time() - start_time,
        locale=get_locale(),
        is_searching=criteria.is_searching(),
        **context,
    )


def generate_word_cloud(text, word_cloud_hash):
    if not text:
        return ""
    # Generate a word cloud image
    wc = WordCloud(background_color=None,
                   mode="RGBA",
                   colormap="twilight",
                   max_words=100,
                   stopwords=WORDCLOUD_STOPWORDS,
                   max_font_size=40,
                   min_font_size=5,
                   width=400,
                   height=200,
                   scale=6,
                   random_state=42)
    try:
        wordcloud = wc.generate(text)
    except ValueError:
        # Maybe there's no word in `text`
        return ""

    fig = Figure(figsize=(8, 4), dpi=120, facecolor='none', edgecolor='none')
    fig.set_tight_layout({"pad": 1.0})
    ax = fig.subplots()
    ax.imshow(wordcloud, interpolation="bilinear")
    ax.axis("off")
    # Save it to a temporary buffer.
    buf = BytesIO()
    fig.savefig(buf, format="png")
    # Generate a unique filename
    filename = f"{word_cloud_hash}.png"
    filepath = os.path.join(wordcloud_dir, filename)

    # Save the image to the file
    with open(filepath, 'wb') as f:
        f.write(buf.getbuffer())

    # Return the URL to the client
    return url_for('static', filename=f'wordclouds/{filename}')


@functools.lru_cache(maxsize=1024)
def _search_list_context(criteria, word_cloud=True):
    context = {}
    with SearcherSingleton() as searcher:
        page_len = criteria.options.get("page-len", config("kerko.pagination.page_len"))
        common_search_args = {
            "keywords": criteria.keywords,
            "filters": criteria.filters,
            "reject_any": {"item_type": ["note", "attachment"]},
            "sort_spec": criteria.get_active_sort_spec(),
            "faceting": True,
        }
        if page_len == "all":
            results = searcher.search(
                limit=None,
                **common_search_args,
            )
        else:
            results = searcher.search_page(
                page=criteria.options.get("page", 1),
                page_len=page_len,
                **common_search_args,
            )

        if results.is_empty():
            return None

        # This has side effect, modifying `page` of criteria.options
        # This affects lru caching on the front page where `page` does not exist.
        criteria.fit_page(results.page_count)

        if criteria.is_searching():
            context["title"] = ngettext("Result", "Results", results.item_count)
        else:
            context["title"] = gettext("Full bibliography")
        context["total_count"] = results.item_count
        context["total_count_formatted"] = format_decimal(results.item_count, locale=get_locale())
        context["page_count"] = results.page_count
        context["page_count_formatted"] = format_decimal(results.page_count, locale=get_locale())
        context["pager"] = pager.build_pager(
            pager.get_sections(criteria.options["page"], results.page_count),
            criteria,
        )
        context["sorter"] = sorter.build_sorter(criteria)
        context["show_abstracts"] = criteria.options.get(
            "abstracts", config("kerko.features.results_abstracts")
        )
        context["abstracts_toggler_url"] = url_for(
            ".search",
            **criteria.params(
                options={
                    "abstracts": int(
                        not criteria.options.get(
                            "abstracts", config("kerko.features.results_abstracts")
                        )
                    ),
                }
            ),
        )
        context["print_url"] = url_for(
            ".search",
            **criteria.params(
                options={
                    "page": None,
                    "page-len": "all",
                    "print-preview": 1,
                }
            ),
        )
        context["print_preview"] = criteria.options.get("print-preview", 0)
        context["download_urls"] = {
            key: url_for(
                ".search_bib_download",
                bib_format_key=key,
                **criteria.params(
                    options={
                        "page": None,
                    }
                ),
            )
            for key in composer().bib_formats.keys()
        }
        if "atom" in config("kerko.feeds.formats"):
            context["atom_feed_url"] = url_for(
                ".atom_feed",
                **create_feed_criteria(initial=criteria).params(
                    options={
                        "page": None,
                    }
                ),
            )
            if criteria.is_searching():
                context["atom_feed_help"] = gettext("Custom feed based on your search")
                context["atom_feed_title"] = gettext("Custom feed")
            else:
                context["atom_feed_title"] = gettext("Main feed")

        # Prepare search result items.
        field_specs = composer().select_fields(
            config("kerko.search.result_fields")
            + [badge.field.key for badge in composer().badges.values()],
        )
        items = results.items(field_specs, highlight=True)

        # Cache `results_facets` which don't change with criteria...
        # But need to remove the page number from options so that all pages
        # have the same criteria
        _page = criteria.options.pop("page")
        criteria_hash = hash(criteria)
        # Check if the hash exists in the cache
        if criteria_hash in facets_cache:
            results_facets = facets_cache[criteria_hash]
        else:
            # Prevent the cache dict from growing forever
            if len(facets_cache) > MAX_FACETS_CACHE:
                for k in list(facets_cache.keys())[:len(facets_cache) - MAX_FACETS_CACHE]:
                    del facets_cache[k]
            # Compute the results_facets and store it in the cache
            results_facets = results.facets(composer().facets, criteria)
            facets_cache[criteria_hash] = results_facets
        # Need restore the original criteria
        criteria.options["page"] = _page

        # The use of cache means that we cannot use generators
        context["search_results"] = list(zip(items, _build_item_search_urls(items, criteria)))
        context["facet_results"] = "".join(
            spec.render(results_facets[spec.key], "search")
            for spec in composer().get_ordered_specs("facets")
        )
        context["breadbox"] = breadbox.build_breadbox(criteria, results_facets)

        if word_cloud:
            word_cloud_hash = hash(criteria)
            context["word_cloud"] = word_cloud_hash
            word_cloud_img = os.path.join(wordcloud_dir, f"{word_cloud_hash}.png")
            if not os.path.exists(word_cloud_img):
                # Word cloud (#TODO Add fulltext as well?)
                text_wordcloud = " ".join(hit["z_abstractNote"] for hit in results 
                                        if "z_abstractNote" in hit)
                text_wordcloud += " ".join(item["data"]["title"] for item in items 
                                            if "data" in items and "title" in item["data"])
                # Submit the generate_word_cloud function to the executor
                executor.submit(generate_word_cloud, text_wordcloud, word_cloud_hash)

        last_sync = kerko_last_sync()
        if last_sync:
            context["last_sync"] = datetime.fromtimestamp(
                last_sync,
                tz=datetime.now().astimezone().tzinfo,
            )

    return context
