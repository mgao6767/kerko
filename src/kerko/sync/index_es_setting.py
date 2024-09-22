INDEX_SETTING = {
    "settings": {
        "analysis": {
            "analyzer": {
                "my_english_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",
                        "english_possessive_stemmer",
                        "english_stop",
                        "english_stemmer",
                    ],
                }
            },
            "filter": {
                "english_stop": {"type": "stop", "stopwords": "_english_"},
                "english_stemmer": {"type": "stemmer", "language": "english"},
                "english_possessive_stemmer": {
                    "type": "stemmer",
                    "language": "possessive_english",
                },
            },
        }
    },
    "mappings": {
        "properties": {
            "alternate_id": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "attachments": {
                "properties": {
                    "data": {
                        "properties": {
                            "contentType": {
                                "type": "text",
                                "fields": {
                                    "keyword": {"type": "keyword", "ignore_above": 256}
                                },
                            },
                            "filename": {
                                "type": "text",
                                "fields": {
                                    "keyword": {"type": "keyword", "ignore_above": 256}
                                },
                            },
                            "md5": {
                                "type": "text",
                                "fields": {
                                    "keyword": {"type": "keyword", "ignore_above": 256}
                                },
                            },
                            "mtime": {"type": "long"},
                        }
                    },
                    "id": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                }
            },
            "bib": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "bibtex": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "coins": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "creator_types": {
                "properties": {
                    "creatorType": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "localized": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                }
            },
            "data": {
                "properties": {
                    "DOI": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "ISSN": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "abstractNote": {
                        "type": "text",
                        "analyzer": "my_english_analyzer",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "accessDate": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "archive": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "archiveLocation": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "callNumber": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "collections": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "creators": {
                        "properties": {
                            "creatorType": {
                                "type": "text",
                                "fields": {
                                    "keyword": {"type": "keyword", "ignore_above": 256}
                                },
                            },
                            "firstName": {
                                "type": "text",
                                "fields": {
                                    "keyword": {"type": "keyword", "ignore_above": 256}
                                },
                            },
                            "lastName": {
                                "type": "text",
                                "fields": {
                                    "keyword": {"type": "keyword", "ignore_above": 256}
                                },
                            },
                        }
                    },
                    "date": {"type": "text"},
                    "dateAdded": {"type": "text"},
                    "dateModified": {"type": "text"},
                    "extra": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "issue": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "itemType": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "journalAbbreviation": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "key": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "language": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "libraryCatalog": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "pages": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "publicationTitle": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "relations": {
                        "properties": {
                            "owl:sameAs": {
                                "type": "text",
                                "fields": {
                                    "keyword": {"type": "keyword", "ignore_above": 256}
                                },
                            }
                        }
                    },
                    "rights": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "series": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "seriesText": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "seriesTitle": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "shortTitle": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "tags": {
                        "properties": {
                            "tag": {
                                "type": "text",
                                "fields": {
                                    "keyword": {"type": "keyword", "ignore_above": 256}
                                },
                            },
                            "type": {"type": "long"},
                        }
                    },
                    "title": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "url": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "version": {"type": "long"},
                    "volume": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                }
            },
            "date_added": {"type": "text"},
            "date_modified": {"type": "text"},
            "facet_journals": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "facet_tag": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "facet_year": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "filter_date": {"type": "text"},
            "id": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "item_fields": {
                "properties": {
                    "field": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                    "localized": {
                        "type": "text",
                        "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                    },
                }
            },
            "item_type": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "item_type_label": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "ris": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "sort_creator": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "sort_date": {"type": "long"},
            "sort_date_added": {"type": "long"},
            "sort_date_modified": {"type": "long"},
            "sort_title": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "text_collections": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "text_creator": {
                "type": "text",
                "analyzer": "my_english_analyzer",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "text_docs": {
                "type": "text",
                "analyzer": "my_english_analyzer",
            },
            "text_tags": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "url": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "year": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "z_abstractNote": {
                "type": "text",
                "analyzer": "my_english_analyzer",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "z_archive": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "z_archiveLocation": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "z_callNumber": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "z_date": {"type": "text"},
            "z_extra": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "z_issue": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "z_journalAbbreviation": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "z_language": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "z_libraryCatalog": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "z_publicationTitle": {
                "type": "text",
                "analyzer": "my_english_analyzer",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "z_rights": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "z_series": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "z_seriesText": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "z_seriesTitle": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "z_shortTitle": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "z_title": {
                "type": "text",
                "analyzer": "my_english_analyzer",
                "fields": {"keyword": {"type": "keyword"}},
            },
            "z_volume": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "zotero_app_url": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
            "zotero_web_url": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
            },
        }
    },
}
