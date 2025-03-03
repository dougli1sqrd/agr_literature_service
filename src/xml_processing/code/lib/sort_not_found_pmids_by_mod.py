"""
takes pmids_not_found from get_pubmed_xml.py, and pmids_by_mods from parse_dqm_json.py, and
generates a set sorted by MODs of pmids that were not found in pubmed.

pipenv run python sort_not_found_pmids_by_mod.py
"""


import logging.config
from os import environ, path

from dotenv import load_dotenv

load_dotenv()

log_file_path = path.join(path.dirname(path.abspath(__file__)), "../logging.conf")
logging.config.fileConfig(log_file_path)
logger = logging.getLogger("literature logger")


base_path = environ.get("XML_PATH")


def sort_not_found_pmids_by_mod():
    """

    :return:
    """

    mod_to_pmids = {}

    pmids_by_mods_file = base_path + "pmids_by_mods"
    pmid_to_mod = {}
    with open(pmids_by_mods_file) as mods_file:
        mods_data = mods_file.read()
        mods_split = mods_data.split("\n")
        for line in mods_split:
            if line == "":
                continue
            tabs = line.split("\t")
            pmid = tabs[0]
            if len(tabs) < 2:
                print("line %s short" % line)
            mods = tabs[2].split(", ")
            for mod in mods:
                try:
                    pmid_to_mod[pmid].append(mod)
                except KeyError:
                    pmid_to_mod[pmid] = [mod]
        mods_file.close()

    pmids_not_found_file = base_path + "pmids_not_found"
    not_found_split = open(pmids_not_found_file).read().splitlines()
    for pmid in not_found_split:
        if pmid == "":
            continue
        for mod in pmid_to_mod[pmid]:
            # print("%s\t%s" % (mod, pmid))
            try:
                mod_to_pmids[mod].append(pmid)
            except KeyError:
                mod_to_pmids[mod] = [pmid]

    output_pmids_not_found_by_mod_file = base_path + "pmids_not_found_by_mod"
    with open(output_pmids_not_found_by_mod_file, "w") as pmids_not_found_by_mod_file:
        for mod in mod_to_pmids:
            count = len(mod_to_pmids[mod])
            pmids = ", ".join(mod_to_pmids[mod])
            logger.info("mod %s has %s pmids not in PubMed %s" % (mod, count, pmids))
            pmids_not_found_by_mod_file.write("mod %s has %s pmids not in PubMed %s\n" % (mod, count, pmids))
        pmids_not_found_by_mod_file.close()


#     for pmid in pmid_to_mod:
#         for mod in pmid_to_mod[pmid]:
#             print("mod %s pmid %s" % (mod, pmid))


if __name__ == "__main__":
    """
    call main start function
    """

    sort_not_found_pmids_by_mod()
