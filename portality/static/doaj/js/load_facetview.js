jQuery(document).ready(function($) {
  $('.facet-view-simple').each(function() {
  $(this).facetview({
    search_url: 'http://' + es_domain + '/query/journal,article/_search?',
    search_index: 'elasticsearch',
    sharesave_link: false,
    searchbox_shade: 'none',
    pager_on_top: true,
    pager_slider: true,
    display_images: false,
    pre_search_callback: customise_facetview_presearch,
    post_search_callback: customise_facetview_results,
    post_init_callback: customise_facetview_init,
    freetext_submit_delay:"1000",
    results_render_callbacks: {
        'bibjson.author_pays': fv_author_pays,
        'created_date': fv_created_date,
        'bibjson.abstract': fv_abstract,
        'addthis-social-share-button': fv_addthis,
        'journal_license' : fv_journal_license,
        "title_field" : fv_title_field,
        "doi_link" : fv_doi_link,
        "links" : fv_links,
        "issns" : fv_issns
    },
    hide_inactive_facets: true,
    facets: [
        {'field': '_type', 'display': 'Journals vs. Articles'},
        {'field': 'index.classification.exact', 'display': 'Subject'},
        {'field': 'index.language.exact', 'display': 'Journal Language'},
        {'field': 'index.country.exact', 'display': 'Journal Country'},
        {'field': 'index.publisher.exact', 'display': 'Publisher'},
        {'field': 'bibjson.provider.exact', 'display': 'Provider'},
        {'field': 'bibjson.author_pays.exact', 'display': 'Publication charges?'},
        {'field': 'index.license.exact', 'display': 'Journal License'},
        // Articles
        {'field': 'bibjson.author.exact', 'display': 'Author (Articles)'},
        {'field': 'bibjson.year.exact', 'display': 'Year of publication (Articles)'},
        {'field': 'bibjson.journal.title.exact', 'display': 'Journal title (Articles)'},
    ],
    search_sortby: [
        {'display':'Date added to DOAJ','field':'created_date'},
        {'display':'Title','field':'bibjson.title.exact'},
        {'display':'Article: Publication date','field':['bibjson.year.exact', 'bibjson.month.exact']},
    ],
    searchbox_fieldselect: [
        {'display':'Title','field':'index.title'},
        {'display':'Keywords','field':'index.keywords'},
        {'display':'Subject','field':'index.classification'},
        {'display':'ISSN', 'field':'index.issn.exact'},
        {'display':'DOI', 'field' : 'bibjson.identifier'},
        // {'display':'Identifier (ISSN, DOI)','field':'bibjson.identifier'},
        {'display':'Journal Country','field':'index.country'},
        {'display':'Journal Language','field':'index.language'},
        {'display':'Publisher','field':'index.publisher'},

        {'display':'Article: Abstract','field':'bibjson.abstract'},
        {'display':'Article: Author','field':'bibjson.author'},
        {'display':'Article: Year','field':'bibjson.year'},
        {'display':'Article: Journal Title','field':'bibjson.journal.title'},

        {'display':'Journal: Alternative Title','field':'bibjson.alternative_title'},
        {'display':'Journal: Provider','field':'bibjson.provider'},
    ],
    paging: {
      size: 10
    },
    default_operator: "AND",
    result_display: [
    // Journals
        [
            {
                "field" : "title_field"
            }
            /*
            {
                "pre": '<span class="title">',
                "field": "bibjson.title",
                "post": "</span>"
            }
            */
        ],
        [
            {
                "pre": '<span class="alt_title">Alternative title: ',
                "field": "bibjson.alternative_title",
                "post": "</span>"
            }
        ],
        [
            {
                "pre": "<strong>Subjects</strong>: ",
                "field": "bibjson.subject.term",
            }
        ],
        [
            {
                "pre": "<strong>Publisher</strong>: ",
                "field": "bibjson.publisher",
            }
        ],
        [
            {
                "pre": "<strong>Provider</strong>: ",
                "field": "bibjson.provider",
            }
        ],
        [
            {
                "pre": "<strong>Publication charges?</strong>: ",
                "field": "bibjson.author_pays",
            }
        ],
        /*
        [
            {
                "pre": "<strong>More information on publishing charges</strong>: ",
                "field": "bibjson.author_pays_url",
            }
        ],
        */
        [
            {
                "pre": "<strong>Started publishing Open Access content in</strong>: ",
                "field": "bibjson.oa_start.year",
            }
        ],
        [
            {
                "pre": "<strong>Stopped publishing Open Access content in</strong>: ",
                "field": "bibjson.oa_end.year",
            }
        ],
        [
            {
                "pre": "<strong>Journal Country</strong>: ",
                "field": "bibjson.country",
            }
        ],
        [
            {
                "pre": "<strong>Journal Language</strong>: ",
                "field": "bibjson.language",
            }
        ],
// Articles
        [
            {
                "pre": "<strong>Authors</strong>: ",
                "field": "bibjson.author.name",
            }
        ],
        [
            {
                "pre": "<strong>Publisher</strong>: ",
                "field": "bibjson.journal.publisher",
            }
        ],
        [
            {
                "pre":'<strong>Date of publication</strong>: ',
                "field": "bibjson.year",
            },
            {
                "pre":' <span class="date-month">',
                "field": "bibjson.month",
                "post": "</span>"
            },
        ],
        [
            {
                "pre": "<strong>Published in</strong>: ",
                "field": "bibjson.journal.title",
                "notrailingspace": true
            },
            {
                "pre": ", Vol ",
                "field": "bibjson.journal.volume",
                "notrailingspace": true
            },
            {
                "pre": ", Iss ",
                "field": "bibjson.journal.number",
                "notrailingspace": true
            },
            {
                "pre": ", Pp ",
                "field": "bibjson.start_page",
                "notrailingspace": true
            },
            {
                "pre": "-",
                "field": "bibjson.end_page",
            },
            {
                "pre" : "(",
                "field": "bibjson.year",
                "post" : ")"
            }
        ],
        [
            {
                "pre" : "<strong>ISSN(s)</strong>: ",
                "field" : "issns"
            }
        ],
        [
            {
                "pre": "<strong>Keywords</strong>: ",
                "field": "bibjson.keywords",
            }
        ],
        [
            {
                "pre": "<strong>Date added to DOAJ</strong>: ",
                "field": "created_date",
            }
        ],
        [
            {
                "pre": "<strong>DOI</strong>: ",
                "field": "doi_link",
            }
        ],
        [
            {
                "field" : "links"
            }
            /*
            {
                "pre": "<strong>More information - ",
                "field": "bibjson.link.type",
                "post": "</strong>: ",
            },
            {
                "field": "bibjson.link.url",
            },
            */
        ],
        [
            {
                "pre": "<strong>Journal Language(s)</strong>: ",
                "field": "bibjson.journal.language"
            }
        ],
        [
            {
                "pre": "<strong>Journal License</strong>: ",
                "field": "journal_license"
            }
        ],
        [
            {
                "pre": "<strong>Country of publication</strong>: ",
                "field": "bibjson.journal.country"
            }
        ],
        [
            {
                "pre": '<strong>Abstract</strong>: ',
                "field": "bibjson.abstract",
            }
        ],

// Share Button
        [
            {
                "field": "addthis-social-share-button",
            }
        ],
    ],
  });
  });
});
