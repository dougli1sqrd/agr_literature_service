"""
xml_to_json
===========

module that converts XMLs to JSON files


pipenv run python xml_to_json.py -f /home/azurebrd/git/agr_literature_service_demo/src/xml_processing/inputs/sample_set

22 minutes on dev.wormbase for 646727 documents from filesystem. 12G of xml to 6.0G of json
1 hour 55 minutes on agr-literature-dev for 649074 documents from filesystem.  15G of xml to 8.0G of json

pipenv run python xml_to_json.py -u "http://tazendra.caltech.edu/~azurebrd/cgi-bin/forms/generic.cgi?action=ListPmids"


not using author firstinit, nlm, issn

update sample
cp pubmed_json/32542232.json pubmed_sample
cp pubmed_json/32644453.json pubmed_sample
cp pubmed_json/33408224.json pubmed_sample
cp pubmed_json/33002525.json pubmed_sample
cp pubmed_json/33440160.json pubmed_sample
cp pubmed_json/33410237.json pubmed_sample
git add pubmed_sample/32542232.json
git add pubmed_sample/32644453.json
git add pubmed_sample/33408224.json
git add pubmed_sample/33002525.json
git add pubmed_sample/33440160.json
git add pubmed_sample/33410237.json

https://ftp.ncbi.nih.gov/pubmed/J_Medline.txt

Processing CommentIn/CommentOn from commentsCorrections results in 12-deep recursive chain of PMID comments, e.g. 32919857, but also many others fairly deep.
Removing CommentIn/CommentOn from allowed RefType values the deepest set is 4 deep, Recursive example 26757732 -> 26868856 -> 26582243 -> 26865040 -> 27032729

Need to set up a queue that queries postgres to get a list of pubmed id that don't have a pubmed final flag
Need to set up flags to take in pmids from postgres queue, file in filesystem, file in URL, list from command line

to get set of pmids with search term 'elegans'
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=elegans&retmax=100000000
"""


import hashlib
import json
import logging
import os
import re
import sys
import urllib.request

import click
import coloredlogs

import calendar

# from dotenv import load_dotenv
#
# load_dotenv()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
coloredlogs.install(level="DEBUG")


known_article_id_types = {
    "pubmed": {"prefix": "PMID:"},
    "doi": {"prefix": "DOI:"},
    "pmc": {"prefix": "PMCID:"},
}
#     'pubmed': {'pages': 'PubMed', 'prefix': 'PMID:'},
#     'doi': {'pages': 'DOI', 'prefix': 'DOI:'},
#     'pmc': {'pages': 'PMC', 'prefix': 'PMCID:'}}
ignore_article_id_types = {"bookaccession", "mid", "pii", "pmcid"}
unknown_article_id_types = set([])


# def represents_int(s):
#     """
#
#     :param s:
#     :return:
#     """
#
#     try:
#         int(s)
#         return True
#     except ValueError:
#         return False


# def month_name_to_number_string(string):
#     """
#
#     :param string:
#     :return:
#     """
#
#     m = {
#         'jan': '01',
#         'feb': '02',
#         'mar': '03',
#         'apr': '04',
#         'may': '05',
#         'jun': '06',
#         'jul': '07',
#         'aug': '08',
#         'sep': '09',
#         'oct': '10',
#         'nov': '11',
#         'dec': '12'}
#     s = string.strip()[:3].lower()
#
#     try:
#         out = m[s]
#         return out
#     except ValueError:
#         raise ValueError(string + ' is not a month')


def get_year_month_day_from_xml_date(pub_date):
    """

    :param pub_date:
    :return:
    """

    date_list = []
    year = ""
    month = "01"
    day = "01"
    year_re_output = re.search("<Year>(.+?)</Year>", pub_date)
    if year_re_output is not None:
        year = year_re_output.group(1)
    month_re_output = re.search("<Month>(.+?)</Month>", pub_date)
    if month_re_output is not None:
        month_text = month_re_output.group(1)
        if type(month_text) == int:
            month = month_text
        else:
            month = list(calendar.month_abbr).index(month_text)
    day_re_output = re.search("<Day>(.+?)</Day>", pub_date)
    if day_re_output is not None:
        day = day_re_output.group(1)
    date_list.append(year)
    date_list.append(month)
    date_list.append(day)

    return date_list


def get_medline_date_from_xml_date(pub_date):
    """

    :param pub_date:
    :return:
    """

    medline_re_output = re.search("<MedlineDate>(.+?)</MedlineDate>", pub_date)
    if medline_re_output is not None:
        return medline_re_output.group(1)


def generate_json(pmids, previous_pmids, base_path):  # noqa: C901
    """

    :param pmids:
    :param previous_pmids:
    :return:
    """

    # open input xml file and read data in form of python dictionary using xmltodict module
    md5data = ""
    # storage_path = base_path + 'pubmed_xml_20210322/'
    # json_storage_path = base_path + 'pubmed_json_20210322/'
    storage_path = base_path + "pubmed_xml/"
    json_storage_path = base_path + "pubmed_json/"

    if not os.path.exists(storage_path):
        os.makedirs(storage_path)
    if not os.path.exists(json_storage_path):
        os.makedirs(json_storage_path)

    # new_pmids = []
    # ref_types = []
    new_pmids_set = set([])
    ref_types_set = set([])
    for pmid in pmids:
        filename = storage_path + pmid + ".xml"
        # if getting pmids from directories split into multiple sub-subdirectories
        # filename = get_path_from_pmid(pmid, 'xml')
        if not os.path.exists(filename):
            continue
        # logger.info("processing %s", filename)
        with open(filename) as xml_file:

            xml = xml_file.read()
            # print (xml)

            # xmltodict is treating html markup like <i>text</i> as xml,
            # which is creating mistaken structure in the conversion.
            # may be better to parse full xml instead.
            # data_dict = xmltodict.parse(xml_file.read())
            xml_file.close()

            # print (pmid)
            data_dict = {}

            # e.g. 21290765 has BookDocument and ArticleTitle
            book_re_output = re.search("<BookDocument>", xml)
            if book_re_output is not None:
                data_dict["is_book"] = "book"

            title_re_output = re.search(
                "<ArticleTitle[^>]*?>(.+?)</ArticleTitle>", xml, re.DOTALL
            )
            if title_re_output is not None:
                title = title_re_output.group(1).rstrip()
                title = re.sub(r"\s+", " ", title)
                data_dict["title"] = title
                if "is_book" not in data_dict:
                    data_dict["is_journal"] = "journal"
            else:
                # e.g. 33054145 21413221
                book_title_re_output = re.search(
                    "<BookTitle[^>]*?>(.+?)</BookTitle>", xml, re.DOTALL
                )
                if book_title_re_output is not None:
                    title = book_title_re_output.group(1).rstrip()
                    title = re.sub(r"\s+", " ", title)
                    data_dict["title"] = title
                    data_dict["is_book"] = "book"
                else:
                    # e.g. 28304499 28308877
                    vernacular_title_re_output = re.search(
                        "<VernacularTitle[^>]*?>(.+?)</VernacularTitle>", xml, re.DOTALL
                    )
                    if vernacular_title_re_output is not None:
                        title = vernacular_title_re_output.group(1).rstrip()
                        title = re.sub(r"\s+", " ", title)
                        data_dict["title"] = title
                        data_dict["is_vernacular"] = "vernacular"
                    else:
                        logger.info("%s has no title", pmid)

            journal_re_output = re.search("<MedlineTA>(.+?)</MedlineTA>", xml)
            if journal_re_output is not None:
                data_dict["journal"] = journal_re_output.group(1)

            pages_re_output = re.search("<MedlinePgn>(.+?)</MedlinePgn>", xml)
            if pages_re_output is not None:
                data_dict["pages"] = pages_re_output.group(1)

            volume_re_output = re.search("<Volume>(.+?)</Volume>", xml)
            if volume_re_output is not None:
                data_dict["volume"] = volume_re_output.group(1)

            issue_re_output = re.search("<Issue>(.+?)</Issue>", xml)
            if issue_re_output is not None:
                data_dict["issueName"] = issue_re_output.group(1)

            pubstatus_re_output = re.search(
                "<PublicationStatus>(.+?)</PublicationStatus>", xml
            )
            if pubstatus_re_output is not None:
                # print pubstatus
                data_dict["publicationStatus"] = pubstatus_re_output.group(1)

            if re.findall("<PublicationType>(.+?)</PublicationType>", xml):
                types_group = re.findall(
                    "<PublicationType>(.+?)</PublicationType>", xml
                )
                data_dict["pubMedType"] = types_group
            elif re.findall('<PublicationType UI=".*?">(.+?)</PublicationType>', xml):
                types_group = re.findall(
                    '<PublicationType UI=".*?">(.+?)</PublicationType>', xml
                )
                data_dict["pubMedType"] = types_group

            # <CommentsCorrectionsList><CommentsCorrections RefType="CommentIn"><RefSource>Mult Scler.
            # 1999 Dec;5(6):378</RefSource><PMID Version="1">10644162</PMID></CommentsCorrections><CommentsCorrections
            # RefType="CommentIn"><RefSource>Mult Scler. 2000 Aug;6(4):291-2</RefSource><PMID Version="1">10962551</PMID>
            # </CommentsCorrections></CommentsCorrectionsList>
            comments_corrections_group = re.findall(
                "<CommentsCorrections (.+?)</CommentsCorrections>", xml, re.DOTALL
            )
            if len(comments_corrections_group) > 0:
                data_dict["commentsCorrections"] = {}
                for comcor_xml in comments_corrections_group:
                    ref_type = ""
                    other_pmid = ""
                    ref_type_re_output = re.search('RefType="(.*?)"', comcor_xml)
                    if ref_type_re_output is not None:
                        ref_type = ref_type_re_output.group(1)
                    other_pmid_re_output = re.search(
                        "<PMID[^>]*?>(.+?)</PMID>", comcor_xml
                    )
                    if other_pmid_re_output is not None:
                        other_pmid = other_pmid_re_output.group(1)
                    if (other_pmid != "") and (ref_type != "") and (ref_type != "CommentIn") \
                            and (ref_type != "CommentOn"):
                        if ref_type in data_dict["commentsCorrections"]:
                            if other_pmid not in data_dict["commentsCorrections"][ref_type]:
                                data_dict["commentsCorrections"][ref_type].append(other_pmid)
                        else:
                            data_dict["commentsCorrections"][ref_type] = [other_pmid]
                        # print(pmid + " COMCOR " + ref_type + " " + other_pmid)
                        ref_types_set.add(ref_type)
                        if other_pmid not in pmids and other_pmid not in previous_pmids:
                            new_pmids_set.add(other_pmid)

            # this will need to be restructured to match schema
            authors_group = re.findall("<Author.*?>(.+?)</Author>", xml, re.DOTALL)
            if len(authors_group) > 0:
                authors_list = []
                authors_rank = 0
                for author_xml in authors_group:
                    authors_rank = authors_rank + 1
                    lastname = ""
                    firstname = ""
                    firstinit = ""
                    collective_name = ""
                    fullname = ""
                    orcid = ""
                    affiliation = []
                    author_cross_references = []
                    lastname_re_output = re.search(
                        "<LastName>(.+?)</LastName>", author_xml
                    )
                    if lastname_re_output is not None:
                        lastname = lastname_re_output.group(1)
                    firstname_re_output = re.search(
                        "<ForeName>(.+?)</ForeName>", author_xml
                    )
                    if firstname_re_output is not None:
                        firstname = firstname_re_output.group(1)
                    firstinit_re_output = re.search(
                        "<Initials>(.+?)</Initials>", author_xml
                    )
                    if firstinit_re_output is not None:
                        firstinit = firstinit_re_output.group(1)
                    if firstinit and not firstname:
                        firstname = firstinit

                    # e.g. 27899353 30979869
                    collective_re_output = re.search(
                        "<CollectiveName>(.+?)</CollectiveName>", author_xml, re.DOTALL
                    )
                    if collective_re_output is not None:
                        collective_name = collective_re_output.group(1).replace("\n", " ").replace("\r", "")
                        collective_name = re.sub(r"\s+", " ", collective_name)

                    # e.g. 30003105   <Identifier Source="ORCID">0000-0002-9948-4783</Identifier>
                    # e.g. 30002370   <Identifier Source="ORCID">http://orcid.org/0000-0003-0416-374X</Identifier>
                    # orcid_re_output = re.search("<Identifier Source=\"ORCID\">(.+?)</Identifier>", author_xml)
                    orcid_re_output = re.search(
                        '<Identifier Source="ORCID">.*?([0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]).*?</Identifier>',
                        author_xml,
                    )
                    if orcid_re_output is not None:
                        orcid = orcid_re_output.group(1)
                        orcid_dict = {"id": "ORCID:" + orcid_re_output.group(1), "pages": ["person/orcid"]}
                        author_cross_references.append(orcid_dict)

                    # e.g. 30003105 30002370
                    # <AffiliationInfo>
                    #     <Affiliation>Department of Animal Medical Sciences, Faculty of Life Sciences, Kyoto Sangyo University , Kyoto , Japan.</Affiliation>
                    # </AffiliationInfo>
                    affiliation_list = []
                    affiliation_info_group = re.findall("<AffiliationInfo>(.*?)</AffiliationInfo>", author_xml, re.DOTALL)
                    for affiliation_info in affiliation_info_group:
                        # print(pmid + " AIDL " + affiliation_info)
                        affiliation_group = re.findall("<Affiliation>(.+?)</Affiliation>", affiliation_info, re.DOTALL)
                        for affiliation in affiliation_group:
                            # print(pmid + " subset " + affiliation)
                            if affiliation not in affiliation_list:
                                affiliation_list.append(affiliation)

                    author_dict = {}
                    # if (firstname and firstinit):
                    #     print "GOOD\t" + pmid
                    # elif firstname:
                    #     print "FN\t" + pmid + "\t" + firstname
                    # elif firstinit:
                    #     print "FI\t" + pmid + "\t" + firstinit
                    # else:
                    #     print "NO\t" + pmid
                    if firstname != "":
                        author_dict["firstname"] = firstname
                    if firstinit != "":
                        author_dict["firstinit"] = firstinit
                    if lastname != "":
                        author_dict["lastname"] = lastname
                    if collective_name != "":
                        author_dict["collectivename"] = collective_name
                    if (firstname != "") and (lastname != ""):
                        fullname = firstname + " " + lastname
                    elif collective_name != "":
                        fullname = collective_name
                    elif lastname != "":
                        fullname = lastname
                    else:
                        logger.info("%s has no name match %s", pmid, author_xml)
                    if orcid != "":
                        author_dict["orcid"] = orcid
                    author_dict["name"] = fullname
                    author_dict["authorRank"] = authors_rank
                    if len(affiliation_list) > 0:
                        author_dict["affiliation"] = affiliation_list
                    if len(author_cross_references) > 0:
                        author_dict["crossReferences"] = author_cross_references
                    # print fullname
                    authors_list.append(author_dict)
                data_dict["authors"] = authors_list

            pub_date_re_output = re.search("<PubDate>(.+?)</PubDate>", xml, re.DOTALL)
            if pub_date_re_output is not None:
                pub_date = pub_date_re_output.group(1)
                date_list = get_year_month_day_from_xml_date(pub_date)
                if date_list[0]:
                    date_string = '-'.join(date_list)
                    date_dict = {"date_string": date_string, "year": date_list[0], "month": date_list[1],
                                 "day": date_list[2]}
                    # datePublished is a string, not a date-time
                    data_dict["datePublished"] = date_string
                    data_dict["issueDate"] = date_dict
                else:
                    # 1524678 2993907 have MedlineDate instead of Year Month Day
                    medline_date = get_medline_date_from_xml_date(pub_date)
                    if medline_date:
                        data_dict["date_string"] = medline_date
                        data_dict["datePublished"] = medline_date

            date_revised_re_output = re.search(
                "<DateRevised>(.+?)</DateRevised>", xml, re.DOTALL
            )
            if date_revised_re_output is not None:
                date_revised = date_revised_re_output.group(1)
                date_list = get_year_month_day_from_xml_date(date_revised)
                if date_list[0]:
                    date_string = "-".join(date_list)
                    date_dict = {"date_string": date_string, "year": date_list[0],
                                 "month": date_list[1], "day": date_list[2]}
                    data_dict["dateLastModified"] = date_dict

            date_received_re_output = re.search("<PubMedPubDate PubStatus=\"received\">(.+?)</PubMedPubDate>", xml, re.DOTALL)
            if date_received_re_output is not None:
                date_received = date_received_re_output.group(1)
                date_list = get_year_month_day_from_xml_date(date_received)
                if date_list[0]:
                    date_string = "-".join(date_list)
                    date_dict = {"date_string": date_string, "year": date_list[0], "month": date_list[1], "day": date_list[2]}
                    data_dict["dateArrivedInPubmed"] = date_dict

            cross_references = []
            has_self_pmid = False  # e.g. 20301347, 21413225 do not have the PMID itself in the ArticleIdList, so must be appended to the cross_references
            article_id_list_re_output = re.search("<ArticleIdList>(.*?)</ArticleIdList>", xml, re.DOTALL)
            if article_id_list_re_output is not None:
                article_id_list = article_id_list_re_output.group(1)
                article_id_group = re.findall('<ArticleId IdType="(.*?)">(.+?)</ArticleId>', article_id_list)
                if len(article_id_group) > 0:
                    type_has_value = set()
                    for type_value in article_id_group:
                        type = type_value[0]
                        value = type_value[1]
                        # convert the only html entities found in DOIs  &lt; &gt; &amp;#60; &amp;#62;
                        # e.g. PMID:8824556 PMID:10092111
                        value = value.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;#60;", "<").replace("&amp;#62;", ">")
                        # print pmid + " type " + type + " value " + value
                        if type in known_article_id_types:
                            if value == pmid:
                                has_self_pmid = True
                            if type in type_has_value:
                                logger.info("%s has multiple for type %s", pmid, type)
                            type_has_value.add(type)
                            # cross_references.append({'id': known_article_id_types[type]['prefix'] + value, 'pages': [known_article_id_types[type]['pages']]})
                            cross_references.append({"id": known_article_id_types[type]["prefix"] + value})
                            data_dict[type] = value  # for cleaning up crossReferences when reading dqm data
                        else:
                            if type not in ignore_article_id_types:
                                logger.info("%s has unexpected type %s", pmid, type)
                                unknown_article_id_types.add(type)
            if not has_self_pmid:
                cross_references.append({"id": "PMID:" + pmid})

            medline_journal_info_re_output = re.search("<MedlineJournalInfo>(.*?)</MedlineJournalInfo>", xml, re.DOTALL)
            if medline_journal_info_re_output is not None:
                medline_journal_info = medline_journal_info_re_output.group(1)
                # print(pmid + " medline_journal_info " + medline_journal_info)
                nlm = ""
                issn = ""
                journal_abbrev = ""
                nlm_re_output = re.search("<NlmUniqueID>(.+?)</NlmUniqueID>", medline_journal_info)
                if nlm_re_output is not None:
                    nlm = nlm_re_output.group(1)
                    cross_references.append({"id": "NLM:" + nlm})
                    # cross_references.append({'id': 'NLM:' + nlm, 'pages': ['NLM']})
                issn_re_output = re.search("<ISSNLinking>(.+?)</ISSNLinking>", medline_journal_info)
                if issn_re_output is not None:
                    issn = issn_re_output.group(1)
                    cross_references.append({"id": "ISSN:" + issn})
                    # cross_references.append({'id': 'ISSN:' + issn, 'pages': ['ISSN']})
                journal_abbrev_re_output = re.search("<MedlineTA>(.+?)</MedlineTA>", medline_journal_info)
                if journal_abbrev_re_output is not None:
                    journal_abbrev = journal_abbrev_re_output.group(1)
                data_dict["nlm"] = nlm  # for mapping to resource
                data_dict["issn"] = issn  # for mapping to MOD data to resource
                data_dict["resourceAbbreviation"] = journal_abbrev
                # check whether all xml has an nlm or issn, for WB set, they all do
                # if (nlm and issn):
                #     print "GOOD\t" + pmid
                # elif nlm:
                #     print "NLM\t" + pmid + "\t" + nlm
                # elif issn:
                #     print "ISSN\t" + pmid + "\t" + issn
                # else:
                #     print "NO\t" + pmid

            if len(cross_references) > 0:
                data_dict["crossReferences"] = cross_references

            publisher_re_output = re.search("<PublisherName>(.+?)</PublisherName>", xml)
            if publisher_re_output is not None:
                publisher = publisher_re_output.group(1)
                # print publisher
                data_dict["publisher"] = publisher

            # previously was only getting all abstract text together, but this was causing different types of abstracts to be concatenated
            # regex_abstract_output = re.findall("<AbstractText.*?>(.+?)</AbstractText>", xml, re.DOTALL)
            # if len(regex_abstract_output) > 0:
            #     abstract = " ".join(regex_abstract_output)
            #     data_dict['abstract'] = re.sub(r'\s+', ' ', abstract)

            main_abstract_list = []
            regex_abstract_output = re.findall(
                "<Abstract>(.+?)</Abstract>", xml, re.DOTALL
            )
            if len(regex_abstract_output) > 0:
                for abs in regex_abstract_output:
                    regex_abstract_text_output = re.findall("<AbstractText.*?>(.+?)</AbstractText>", abs, re.DOTALL)
                    if len(regex_abstract_text_output) > 0:
                        for abstext in regex_abstract_text_output:
                            main_abstract_list.append(abstext)
            main_abstract = " ".join(main_abstract_list)
            if main_abstract != "":
                main_abstract = re.sub(r"\s+", " ", main_abstract)

            pip_abstract_list = []
            plain_abstract_list = []
            lang_abstract_list = []
            regex_other_abstract_output = re.findall("<OtherAbstract (.+?)</OtherAbstract>", xml, re.DOTALL)
            if len(regex_other_abstract_output) > 0:
                for other_abstract in regex_other_abstract_output:
                    abs_type = ""
                    abs_lang = ""
                    abs_type_re_output = re.search('Type="(.*?)"', other_abstract)
                    if abs_type_re_output is not None:
                        abs_type = abs_type_re_output.group(1)
                    abs_lang_re_output = re.search('Language="(.*?)"', other_abstract)
                    if abs_lang_re_output is not None:
                        abs_lang = abs_lang_re_output.group(1)
                    if abs_type == "Publisher":
                        lang_abstract_list.append(abs_lang)
                    else:
                        regex_abstract_text_output = re.findall('<AbstractText.*?>(.+?)</AbstractText>', other_abstract, re.DOTALL)
                        if len(regex_abstract_text_output) > 0:
                            for abstext in regex_abstract_text_output:
                                if abs_type == "plain-language-summary":
                                    plain_abstract_list.append(abstext)
                                elif abs_type == "PIP":
                                    pip_abstract_list.append(abstext)
            pip_abstract = " ".join(pip_abstract_list)  # e.g. 9643811 has pip but not main
            if pip_abstract != "":
                pip_abstract = re.sub(r"\s+", " ", pip_abstract)
            plain_abstract = " ".join(plain_abstract_list)
            if plain_abstract != "":  # e.g. 32338603 has plain abstract
                data_dict["plainLanguageAbstract"] = re.sub(r"\s+", " ", plain_abstract)
            if len(lang_abstract_list) > 0:  # e.g. 30160698 has fre and spa
                data_dict["pubmedAbstractLanguages"] = lang_abstract_list
            if main_abstract != "":
                data_dict["abstract"] = main_abstract
            elif pip_abstract != "":  # e.g. 9643811 has pip but not main abstract
                data_dict["abstract"] = pip_abstract

            # some xml has keywords spanning multiple lines e.g. 30110134
            # others get captured inside other keywords e.g. 31188077
            regex_keyword_output = re.findall("<Keyword .*?>(.+?)</Keyword>", xml, re.DOTALL)
            if len(regex_keyword_output) > 0:
                keywords = []
                for keyword in regex_keyword_output:
                    keyword = re.sub("<[^>]+?>", "", keyword)
                    keyword = keyword.replace("\n", " ").replace("\r", "")
                    keyword = re.sub(r"\s+", " ", keyword)
                    keyword = keyword.lstrip()
                    keywords.append(keyword)
                data_dict["keywords"] = keywords

            meshs_group = re.findall("<MeshHeading>(.+?)</MeshHeading>", xml, re.DOTALL)
            if len(meshs_group) > 0:
                meshs_list = []
                for mesh_xml in meshs_group:
                    descriptor_re_output = re.search("<DescriptorName.*?>(.+?)</DescriptorName>", mesh_xml, re.DOTALL)
                    if descriptor_re_output is not None:
                        mesh_heading_term = descriptor_re_output.group(1)
                        qualifier_group = re.findall("<QualifierName.*?>(.+?)</QualifierName>", mesh_xml, re.DOTALL)
                        if len(qualifier_group) > 0:
                            for mesh_qualifier_term in qualifier_group:
                                mesh_dict = {"referenceId": "PMID:" + pmid, "meshHeadingTerm": mesh_heading_term,
                                             "meshQualifierTerm": mesh_qualifier_term}
                                meshs_list.append(mesh_dict)
                        else:
                            mesh_dict = {"referenceId": "PMID:" + pmid, "meshHeadingTerm": mesh_heading_term}
                            meshs_list.append(mesh_dict)
                # for mesh_xml in meshs_group:
                #     descriptor_group = re.findall("<DescriptorName.*?UI=\"(.+?)\".*?>(.+?)</DescriptorName>",
                #                                  mesh_xml, re.DOTALL)
                #     if len(descriptor_group) > 0:
                #         for id_name in descriptor_group:
                #             mesh_dict = {}
                #             mesh_dict["referenceId"] = id_name[0]
                #             mesh_dict["meshHeadingTerm"] = id_name[1]
                #             meshs_list.append(mesh_dict)
                #     qualifier_group = re.findall("<QualifierName.*?UI=\"(.+?)\".*?>(.+?)</QualifierName>",
                #                                 mesh_xml, re.DOTALL)
                #     if len(qualifier_group) > 0:
                #         for id_name in qualifier_group:
                #             mesh_dict = {}
                #             mesh_dict["referenceId"] = id_name[0]
                #             mesh_dict["meshQualifierTerm"] = id_name[1]
                #             meshs_list.append(mesh_dict)
                data_dict["meshTerms"] = meshs_list

            # generate the object using json.dumps()
            # corresponding to json data

            # minified
            # json_data = json.dumps(data_dict)

            # pretty-print
            json_data = json.dumps(data_dict, indent=4, sort_keys=True)

            # Write the json data to output json file
            # UNCOMMENT TO write to json directory
            json_filename = json_storage_path + pmid + ".json"
            # if getting pmids from directories split into multiple sub-subdirectories
            # json_filename = get_path_from_pmid(pmid, 'json')
            with open(json_filename, "w") as json_file:
                json_file.write(json_data)
                json_file.close()
            md5sum = hashlib.md5(json_data.encode("utf-8")).hexdigest()
            md5data += pmid + "\t" + md5sum + "\n"

    md5file = json_storage_path + "md5sum"
    logger.info("Writing md5sum mappings to %s", md5file)
    with open(md5file, "a") as md5file_fh:
        md5file_fh.write(md5data)

    for unknown_article_id_type in unknown_article_id_types:
        logger.warning("unknown_article_id_type %s", unknown_article_id_type)

    for ref_type in ref_types_set:
        logger.info("ref_type %s", ref_type)

    new_pmids = sorted(new_pmids_set)
    for pmid in new_pmids:
        logger.info("new_pmid %s", pmid)

    return new_pmids


@click.command()
@click.option("-c", "--commandline", "cli", multiple=True, help="take input from command line flag", required=False)
@click.option("-d", "--database", "db", help="take input from database query", required=False)
@click.option("-f", "--file", "ffile", help="take input from entries in file with full path", required=False)
@click.option("-r", "--restapi", "api", help="take input from rest api", required=False)
@click.option("-s", "--sample", "sample", help="test sample input from hardcoded entries", required=False, default=False, is_flag=True)
@click.option("-u", "--url", "url", help="take input from entries in file at url", required=False)
def process_tasks(cli, db, ffile, api, sample, url):
    """

    :param cli:
    :param db:
    :param ffile:
    :param api:
    :param sample:
    :param url:
    :return:
    """

    # set storage location
    # todo: see if environment variable check works
    # base_path = '/home/azurebrd/git/agr_literature_service_demo/src/xml_processing/'
    if len(os.environ.get("XML_PATH")) == 0:
        sys.exit()
    else:
        base_path = os.environ.get("XML_PATH")

    storage_path = base_path + "pubmed_xml/"
    logger.info("Base path is at " + base_path)
    logger.info("XMLs will be saved on " + storage_path)

    pmids = []  # list that will contain the PMIDs to be converted

    # checking parameters
    if db:
        # python xml_to_json.py -d
        logger.info("Processing database entries")
    elif api:
        # python xml_to_json.py -r
        logger.info("Processing rest api entries")
    elif ffile:
        # python xml_to_json.py -f /home/azurebrd/git/agr_literature_
        # service_demo/src/xml_processing/inputs/pmid_file.txt
        logger.info("Processing file input from " + ffile)
        # this requires a well structured input
        pmids = open(ffile).read().splitlines()
    elif url:
        # python xml_to_json.py -u http://tazendra.caltech.edu/~azurebrd/var/work/pmid_sample
        logger.info("Processing url input from %s", url)
        req = urllib.request.urlopen(url)
        data = req.read()
        lines = data.splitlines()
        for pmid in lines:
            pmids.append(str(int(pmid)))
    elif cli:
        # python xml_to_json.py -c 1234 4576 1828
        logger.info("Processing commandline input")
        for pmid in cli:
            pmids.append(pmid)
    elif sample:
        # python xml_to_json.py -s
        logger.info("Processing hardcoded sample input")
        pmids = ["12345678", "12345679", "12345680"]
    # else:
    #     logger.info("Processing database entries")

    # when iterating manually through list of PMIDs from PubMed XML CommentsCorrections,
    # and wanting to exclude PMIDs that have already been looked at from original alliance DQM input, or previous iterations.
    previous_pmids = []
    previous_pmids_files = []
    # previous_pmids_files = ['inputs/alliance_pmids', 'inputs/comcor_add1', 'inputs/comcor_add2', 'inputs/comcor_add3']
    # previous_pmids_files = ['inputs/alliance_pmids', 'inputs/comcor_add1', 'inputs/comcor_add2',
    #                        'inputs/comcor_add3', 'inputs/comcor_add4', 'inputs/comcor_add5', 'inputs/comcor_add6',
    #                        'inputs/comcor_add7', 'inputs/comcor_add8', 'inputs/comcor_add9', 'inputs/comcor_add10',
    #                        'inputs/comcor_add11']
    for previous_pmids_file in previous_pmids_files:
        with open(previous_pmids_file, "r") as fp:
            pmid = fp.readline()
            while pmid:
                previous_pmids.append(pmid.rstrip())
                pmid = fp.readline()

    generate_json(pmids, previous_pmids, base_path)

    logger.info("Done converting XML to JSON")


if __name__ == "__main__":
    """
    call main start function
    """

    process_tasks()
