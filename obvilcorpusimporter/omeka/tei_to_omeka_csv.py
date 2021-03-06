#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tei_to_omeka_csv.py is part of the project OBVILCorpusImporter
Author: Valérie Hanoka

"""

import os
import csv
import glob
import logging
from re import sub

from teiexplorer.corpusreader import tei_content_scraper as tcscraper
from vignettes.image_generator import create_image


###########################################################
#                     GETTING METADATA
###########################################################


def tei_to_omeka_header(csv_header_info):
    """ Transforms an XML-TEI header path to a Omeka (semantic-web compliant) header."""


    # XML-TEI headers elements to Linked Data correspondences
    xml_tag_to_voc = {
        u"#fileDesc#titleStmt_title": u"dc:title",
        u"#fileDesc#titleStmt_author_key": u"dc:creator",
        u"#fileDesc#editionStmt#respStmt": u"dc:contributor",
        u"#fileDesc#publicationStmt_publisher": u"dc:publisher",
        u"#profileDesc#creation_when": u"dc:date",
        u"#profileDesc#langUsage_ident": u"dc:language",
        u"#fileDesc#publicationStmt_idno": u"dc:identifier",  # Obligatoire
        u"#fileDesc#titleStmt_editor_key": u"http://schema.org/editor",
        u'#fileDesc#publicationStmt#availability#licence': u"dc:rights",
        u"#fileDesc#publicationStmt#availability#licence_": u"dc:rights",
        u"#fileDesc#publicationStmt#licence": u"dc:rights",
    }

    new_csv_header_info = {xml_tag_to_voc.get(k, k): v for (k, v) in csv_header_info.items()}

    if u"dc:creator" not in new_csv_header_info:
        not_normalized_creator_form = new_csv_header_info.get(u"#fileDesc#titleStmt_author", False)

        if not_normalized_creator_form:
            new_csv_header_info[u"dc:creator"] = not_normalized_creator_form

    return {k: v for (k, v) in new_csv_header_info.items() if not k.startswith('#')}


def parse_tei_documents(corpora, omeka_csv_folder='crawled_data'):
    """
    Extracting metadata from all the XML-TEI documents in corpora.
    :param corpora: Corpora locations where TEI files are stored
    :param omeka_csv_folder: The folder where the transformed metadata
                             information in Omeka CSVimport format should
                             be written.
    :return:
    """

    # Creating the folder if it does not exists
    if not os.path.exists(omeka_csv_folder):
        os.makedirs(omeka_csv_folder)

    # The 'corpus_tag' corresponds to a label giving a hint on the corpus provenance.
    for (corpus_tag, corpus_location) in corpora.items():

        corpus_location = sub('__SAVE_DIRECTORY__', omeka_csv_folder, corpus_location)
        corpus_info = {}
        csv_headers = set([])

        for document_file in glob.glob(corpus_location):

            logging.info(u"Parsing %s" % document_file)
            document = tcscraper.TeiContent(document_file, corpus_tag)
            csv_header_info = document.header_to_omeka_dict()

            # Translating TEI headers to Semantic Web relations
            csv_header_info = tei_to_omeka_header(csv_header_info)

            # Adding other attributes
            csv_header_info.update({u"dc:format": "text/xml; text/epub"})

            # Usually, the identifiers given in the XML-TEI are faulty.
            # We need to compute a clean form of it, pointing to the html document.
            identifier = document_file.split('.')[0].split('/')[-1]
            #html_identifier = "http://132.227.201.10:8086/corpus/%s/html/%s.html" % (corpus_tag, identifier)
            csv_url_files = sub(r'\.xml$', '.csv', document_file)
            with open(csv_url_files, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f, delimiter='\t')
                links_to_document = sorted(
                    set([row[1].replace(' ', '') for row in reader]),
                    key=lambda x: x[-3:]  # sort by the 3 last letters of ext. Silly way to have a constant order
                )

            csv_header_info["dc:identifier"] = document.OMEKA_SPLIT_CHAR.join(links_to_document)

            # Producing the vignette
            image_identifier = "%s_%s" % (corpus_tag, identifier)
            create_image(
                identifier=image_identifier,
                title=csv_header_info.get("dc:title", "Sans titre"),
                author=csv_header_info.get("dc:creator", "Anonyme"),
                save_in_folder=omeka_csv_folder
            )
            csv_header_info['dc:relation'] = \
                'vignette : http://132.227.201.10:8086/corpus/vignettes_corpus/%s.png' % image_identifier

            csv_header_info['dc:rights'] = u'Copyright © 2018 Université Paris-Sorbonne, agissant pour le Laboratoire d’Excellence « Observatoire de la vie littéraire » (ci-après dénommé OBVIL). Ces ressources électroniques protégées par le code de la propriété intellectuelle sur les bases de données (L341-1) sont mises à disposition de la communauté scientifique internationale par l’OBVIL, selon les termes de la licence Creative Commons : « Attribution - Pas d’Utilisation Commerciale - Pas de Modification 3.0 France (CC BY-NC-ND 3.0 FR) ». Attribution : afin de référencer la source, toute utilisation ou publication dérivée de cette ressource électroniques comportera le nom de l’OBVIL et surtout l’adresse Internet de la ressource. Pas d’Utilisation Commerciale : dans l’intérêt de la communauté scientifique, toute utilisation commerciale est interdite. Pas de Modification : l’OBVIL s’engage à améliorer et à corriger cette ressource électronique, notamment en intégrant toutes les contributions extérieures, la diffusion de versions modifiées de cette ressource n’est pas souhaitable.'
            corpus_info[document_file] = csv_header_info
            csv_headers.update(csv_header_info.keys())
            del document

        csv_file = u'%s/%s.csv' % (omeka_csv_folder, corpus_tag)

        with open(csv_file, 'w', encoding='utf-8') as f:
            w = csv.DictWriter(f, csv_headers)
            w.writeheader()

            for doc_id, doc_metadata in corpus_info.items():
                w.writerow(doc_metadata)
