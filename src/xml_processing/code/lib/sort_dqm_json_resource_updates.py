"""
pipenv run python sort_dqm_json_resource_updates.py

first run  get_datatypes_cross_references.py  to generate mappings from references to xrefs and resources to xrefs
and  generate_pubmed_nlm_resource.py  to generate pubmed_resource_json/resource_pubmed_all.json

Attention Paulo: This is still in progress, need to test it against a newly populated database after hearing back about oddly high-numbered NLMs

rename this to sort_dqm_json_resource_updates
work off of sanitized_resource_json  mod + NLM files
should it also update NLM resources ?  yes, 13.5 minutes is not long
test time to get all resources 0000042513 - 13.5 minutes.
keep working off of lit-4003, comparing data from 20211025 files (loaded at lit-4005)
"""


import argparse
import json
import logging
import logging.config
import warnings
from os import environ, makedirs, path

import requests
from dotenv import load_dotenv

from helper_file_processing import (
    compare_authors_or_editors,
    load_ref_xref,
    save_resource_file,
    split_identifier,
)
from helper_post_to_api import (
    generate_headers,
    get_authentication_token,
    process_api_request,
)

warnings.filterwarnings("ignore", category=UserWarning, module="bs4")

load_dotenv()

api_server = environ.get("API_SERVER", "localhost")


log_file_path = path.join(path.dirname(path.abspath(__file__)), "../logging.conf")
logging.config.fileConfig(log_file_path)
logger = logging.getLogger("literature logger")

parser = argparse.ArgumentParser()

args = vars(parser.parse_args())


def load_sanitized_resource(datatype):
    """
    Load sanitized resource data generated by parse_dqm_json_resource.py

    :param datatype:
    :return:
    """

    base_path = environ.get("XML_PATH")
    filename = base_path + "sanitized_resource_json/RESOURCE_" + datatype + ".json"
    sanitized_resources = {}
    try:
        with open(filename) as f:
            whole_dict = json.load(f)
            if "data" in whole_dict:
                sanitized_resources = whole_dict["data"]
    except IOError:
        pass

    return sanitized_resources


def update_sanitized_resources(datatype):
    """
    datatype is a MOD or NLM.  sort against resource_curie_to_xref from get_datatypes_cross_references.py query of
    database.  sort into resources to update, or to create: saving those to sanitized_resource_json_updates/
    to post to db with post_resource_to_api.py

    :param datatype:
    :return:
    """

    logger.info("update_sanitized_resources for %s", datatype)

    base_path = environ.get("XML_PATH")
    api_port = environ.get("API_PORT")  # noqa: F841

    json_storage_path = base_path + "sanitized_resource_json_updates/"
    if not path.exists(json_storage_path):
        makedirs(json_storage_path)

    token = get_authentication_token()
    headers = generate_headers(token)

    xref_ref, ref_xref_valid, ref_xref_obsolete = load_ref_xref("resource")
    # xref_ref, ref_xref_valid, ref_xref_obsolete = load_ref_xref('resource2')  # to test against older database mappings
    sanitized_resources = load_sanitized_resource(datatype)
    resources_to_update = {}
    resources_to_create = {}

    # e.g. create ZFIN:ZDB-JRNL-210824-1
    # counter = 0
    # make this True for live changes
    # live_changes = False
    live_changes = True
    for resource_dict in sanitized_resources:
        # counter = counter + 1
        # if counter > 2:
        #     break
        found = False
        primary_id = resource_dict["primaryId"]
        prefix, identifier, separator = split_identifier(primary_id)
        # logger.info("primary_id %s pubmed %s", primary_id, resource_dict)
        if prefix in xref_ref:
            if identifier in xref_ref[prefix]:
                agr = xref_ref[prefix][identifier]
                if agr in resources_to_update:
                    logger.info("ERROR agr %s has multiple values to update %s %s", agr, primary_id, resources_to_update[agr]["primaryId"])
                else:
                    resources_to_update[agr] = resource_dict
                # logger.info("update primary_id %s db %s", primary_id, agr)
                found = True
        if not found:
            # logger.info("create primary_id %s", primary_id)
            resources_to_create[primary_id] = resource_dict

    if resources_to_create:
        # this needs to post_resource_to_api, figure out appending to resource_primary_id_to_curie
        save_resource_file(json_storage_path, resources_to_create, datatype)

    update_resources(live_changes, headers, resources_to_update)


def update_resources(live_changes, headers, resources_to_update):
    """
    Get the resource from the API, compare to the new resource data.  Patch simple and list fields.  Add new cross_references and track other cases until curators tell us what reports they want.
    This takes 11 minutes to query 34284 resources one by one through the API

    :param live_changes:
    :param headers:
    :param resources_to_update:
    :return:
    """

    # pubmed_fields = ['isoAbbreviation', 'crossReferences', 'onlineISSN', 'medlineAbbreviation', 'printISSN', 'title', 'primaryId', 'nlm']
    # keys_to_remove = {'nlm', 'primaryId', 'crossReferences'}   # these are all the nlm, which is the key to find this, so it cannot change
    remap_keys = {
        "isoAbbreviation": "iso_abbreviation",
        "medlineAbbreviation": "medline_abbreviation",
        "printISSN": "print_issn",
        "onlineISSN": "online_issn",
        "abbreviationSynonyms": "abbreviation_synonyms",
        "titleSynonyms": "title_synonyms",
        "crossReferences": "cross_references",
        "editorsOrAuthors": "editors",
    }

    # to account for editors and xrefs later
    # editor_keys_to_remove = {'referenceId'}
    # remap_editor_keys = {}
    # remap_editor_keys['authorRank'] = 'order'
    # remap_editor_keys['firstName'] = 'first_name'
    # remap_editor_keys['lastName'] = 'last_name'
    # remap_editor_keys['middleNames'] = 'middle_names'
    # cross_references_keys_to_remove = {}
    # remap_cross_references_keys = {}
    # remap_cross_references_keys['id'] = 'curie'

    # no one is sending abstractOrSummary / 'abstract', 'summary' ; titleSynonyms ; copyrightDate data
    simple_fields = [
        "title",
        "isoAbbreviation",
        "medlineAbbreviation",
        "printISSN",
        "onlineISSN",
        "publisher",
        "pages",
    ]
    list_fields = ["abbreviationSynonyms", "titleSynonyms", "volumes"]
    # complex_fields = ['crossReferences', 'editorsOrAuthors']
    # TODO deal with editors, example AGR:AGR-Resource-0000034288     FB:FBmultipub_7448

    xref_ref, ref_xref_valid, ref_xref_obsolete = load_ref_xref("resource")
    # xref_ref, ref_xref_valid, ref_xref_obsolete = load_ref_xref('resource2')  # to test against older database mappings

    api_port = environ.get("API_PORT")

    counter = 0
    max_counter = 10000000
    # max_counter = 1

    for agr in resources_to_update:
        counter = counter + 1
        if counter > max_counter:
            break

        # to test only on something that gets a new online_issn
        # if agr != 'AGR:AGR-Resource-0000015274':
        #     continue

        dqm_entry = resources_to_update[agr]
        # logger.info("pm title %s", dqm_entry['title'])   # for debugging which reference was found
        # logger.info("%s", dqm_entry)
        #         live_changes = True

        url = "http://" + api_server + ":" + api_port + "/resource/" + agr
        logger.info("get AGR resource info from database %s", url)
        get_return = requests.get(url)
        db_entry = json.loads(get_return.text)
        # logger.info("db title %s", db_entry['title'])   # for debugging which reference was found

        update_json = {}
        for field_camel in simple_fields:
            field_snake = camel_to_snake(field_camel, remap_keys)
            dqm_value = None
            db_value = None
            if field_camel in dqm_entry:
                dqm_value = dqm_entry[field_camel]
            if field_snake in db_entry:
                db_value = db_entry[field_snake]
            if dqm_value != db_value:
                logger.info("patch %s field %s from db %s to pm %s", agr, field_snake, db_value, dqm_value)
                update_json[field_snake] = dqm_value
        for field_camel in list_fields:
            list_changed = compare_list(db_entry, dqm_entry, field_camel, remap_keys)
            if list_changed[0]:
                logger.info("patch %s field %s from db %s to dqm %s", agr, list_changed[3], list_changed[2], list_changed[1])
                update_json[list_changed[3]] = list_changed[1]
        if 'crossReferences' in dqm_entry:
            headers = compare_xref(agr, dqm_entry, xref_ref, ref_xref_valid, ref_xref_obsolete, headers, live_changes)
        editors_changed = compare_authors_or_editors(db_entry, dqm_entry, 'editors')
        # editor API needs updates.  reference_curie required to post reference authors but for some reason resource_curie not allowed here, cannot connect new editor to resource if resource_curie is not passed in
        if editors_changed[0]:
            pass
        #    # live_changes = True
        #    # e.g. FB:FBmultipub_7448
        #    for patch_data in editors_changed[1]:
        #        patch_dict = patch_data['patch_dict']
        #        # patch_dict['resource_curie'] = agr   # reference_curie required to patch reference authors but for some reason not allowed here
        #        logger.info("patch %s editor_id %s patch_dict %s", agr, patch_data['editor_id'], patch_dict)
        #        editor_patch_url = 'http://localhost:' + api_port + '/editor/' + str(patch_data['editor_id'])
        #        headers = generic_api_patch(live_changes, editor_patch_url, headers, patch_dict, str(patch_data['editor_id']), None, None)
        #    for create_dict in editors_changed[2]:
        #        create_dict['resource_curie'] = agr   # reference_curie required to post reference authors but for some reason not allowed here
        #        logger.info("add to %s create_dict %s", agr, create_dict)
        #        editor_post_url = 'http://localhost:' + api_port + '/editor/'
        #        headers = generic_api_post(live_changes, editor_post_url, headers, create_dict, agr, None, None)
        if update_json:
            # for debugging changes
            # update_text = json.dumps(update_json, indent=4)
            # print('update ' + update_text)
            headers = generic_api_patch(
                live_changes, url, headers, update_json, agr, None, None
            )


# these are the same as in  sort_dqm_json_reference_updates.py  but not sure I'll want different logging or response handling later
def generic_api_post(live_changes, url, headers, new_entry, agr, mapping_fh, error_fh):
    if live_changes:
        api_response_tuple = process_api_request(
            "POST", url, headers, new_entry, agr, mapping_fh, error_fh
        )
        headers = api_response_tuple[0]
        response_text = api_response_tuple[1]
        response_status_code = api_response_tuple[2]
        log_info = api_response_tuple[3]
        if log_info:
            logger.info(log_info)
        if response_status_code == 201:
            response_dict = json.loads(response_text)
            response_dict = str(response_dict).replace('"', "")
            logger.info("%s\t%s", agr, response_dict)
    return headers


def generic_api_patch(live_changes, url, headers, update_json, agr, mapping_fh, error_fh):
    """

    :param live_changes:
    :param url:
    :param headers:
    :param update_json:
    :param agr:
    :param mapping_fh:
    :param error_fh:
    :return:
    """

    if live_changes:
        api_response_tuple = process_api_request("PATCH", url, headers, update_json, agr, mapping_fh, error_fh)
        headers = api_response_tuple[0]
        response_text = api_response_tuple[1]
        response_status_code = api_response_tuple[2]
        log_info = api_response_tuple[3]
        if log_info:
            logger.info(log_info)
        if response_status_code == 202:
            response_dict = json.loads(response_text)
            response_dict = str(response_dict).replace('"', "")
            logger.info("%s\t%s", agr, response_dict)

    return headers


def camel_to_snake(field_camel, remap_keys):
    """

    :param field_camel:
    :param remap_keys:
    :return:
    """

    field_snake = field_camel
    if field_camel in remap_keys:
        field_snake = remap_keys[field_camel]

    return field_snake


def compare_xref(agr, dqm_entry, xref_ref, ref_xref_valid, ref_xref_obsolete, headers, live_changes):
    """
    We're running dqm resource updates mod by mod instead of aggregating all their data into one entry
    and comparing that to the database.  Since we cannot track which mod submission an xref went into
    the database with, we cannot tell which ones should be removed.  For example, if for a given resource
    FB sends an ISSN and ZFIN sends an ISBN, when running the ZFIN update it will see that the database
    has an ISSN that ZFIN doesn't have, so it will create notification about things that ZFIN doesn't
    necessarily care about.  For that reason we're only doing addition of xrefs, and removals will have
    to be done at ABC through the UI.

    :param agr:
    :param dqm_entry:
    :param xref_ref:
    :param ref_xref_valid:
    :param ref_xref_obsolete:
    :param headers:
    :param live_changes:
    :return:
    """

    api_port = environ.get("API_PORT")
    url = "http://" + api_server + ":" + api_port + "/cross_reference/"

    for xref in dqm_entry["crossReferences"]:
        curie = xref["id"]
        prefix, identifier, separator = split_identifier(curie)
        agr_db_from_xref = ""
        if prefix in xref_ref:
            if identifier in xref_ref[prefix]:
                agr_db_from_xref = xref_ref[prefix][identifier]
        # depending on what curators want for reports, these commented out logger.info should go into reports
        if agr_db_from_xref == agr:
            pass
            # logger.info("GOOD1: cross_reference %s good in %s", curie, agr)
        elif agr_db_from_xref != "":
            pass
            # these are probably useful to curators, have conflicts of xref mapping to different agr resources before and after
            # logger.info("REMAP: cross_reference %s already exists in %s", curie, agr_db_from_xref)
        else:
            dqm_xref_obsolete_found = False
            dqm_xref_valid_found = False  # noqa: F841
            if agr in ref_xref_obsolete:
                if prefix in ref_xref_obsolete[agr]:
                    if identifier.lower() in ref_xref_obsolete[agr][prefix]:
                        dqm_xref_obsolete_found = True  # noqa: F841
                        # logger.info("OBSOLETE: cross_reference %s obsolete in %s", curie, agr)
            elif agr in ref_xref_valid:
                if prefix in ref_xref_valid[agr]:
                    if identifier.lower() == ref_xref_valid[agr][prefix].lower():
                        # this should never happen, equivalent to GOOD1 unless something went wrong somewhere
                        pass
                        # logger.info("GOOD2: cross_reference %s good in %s", curie, agr)
                    else:
                        pass
                        # logger.info("RENAMED: cross_reference %s prefix %s was %s new dqm value %s in %s", curie, prefix, ref_xref_valid[agr][prefix], identifier, agr)
                else:
                    logger.info("CREATE: add cross_reference %s to %s", curie, agr)
                    new_entry = {"curie": curie, "resource_curie": agr}
                    if "pages" in xref:
                        new_entry["pages"] = xref["pages"]
                    # live_changes = True
                    if live_changes:
                        # logger.info("CREATE: %s %s", url, new_entry)
                        api_response_tuple = process_api_request("POST", url, headers, new_entry, curie, None, None)
                        headers = api_response_tuple[0]
                        response_text = api_response_tuple[1]
                        response_status_code = api_response_tuple[2]
                        log_info = api_response_tuple[3]
                        if log_info:
                            logger.info(log_info)
                        if response_status_code == 201:
                            response_dict = json.loads(response_text)
                            response_dict = str(response_dict).replace('"', "")
                            logger.info("%s\t%s", agr, response_dict)

    return headers


def compare_list(db_entry, dqm_entry, field_camel, remap_keys):
    """
    compare case-insensitive if two lists contain the same values from db and dqm dicts

    :param db_entry:
    :param dqm_entry:
    :param field_camel:
    :param remap_keys:
    :return:
    """

    field_snake = camel_to_snake(field_camel, remap_keys)
    db_values = []
    dqm_values = []
    if field_snake in db_entry:
        if db_entry[field_snake] is not None:
            db_values = db_entry[field_snake]
    lower_db_values = [i.lower() for i in db_values]
    if field_camel in dqm_entry:
        if dqm_entry[field_camel] is not None:
            dqm_values = dqm_entry[field_camel]
    lower_dqm_values = [i.lower() for i in dqm_values]
    if set(lower_db_values) == set(lower_dqm_values):
        return False, None, None
    else:
        return True, dqm_values, db_values, field_snake


def test_get_from_list():
    """
    To test making a GET on :4005 to get multiple references at once vs one-by-one.
    It's just as slow, but leaving it in to test future different methods for getting data from database
    20 seconds for 1000 resources
    13.5 minutes for all 42513 resources

    :return:
    """

    print("json_data")
    method = "GET"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    json_data = []
    # for i in range(1, 1001):
    for i in range(1, 42514):
        agr_id = "AGR:AGR-Resource-" + str(i).zfill(10)
        url = "http://dev.alliancegenome.org:4005/resource/" + agr_id
        print(url)
        request_return = requests.request(
            method, url=url, headers=headers, json=json_data
        )
        process_text = str(request_return.text)
        print(process_text)
    # print(json_data)


if __name__ == "__main__":
    """
    call main start function
    """

    logger.info("starting sort_dqm_json_resource_updates.py")

    # test_get_from_list()
    mods = ["RGD", "MGI", "SGD", "FB", "ZFIN", "WB"]
    for mod in mods:
        update_sanitized_resources(mod)
    update_sanitized_resources("NLM")
    # update_sanitized_resources('ZFIN')
    # update_sanitized_resources('FB')

    logger.info("ending sort_dqm_json_resource_updates.py")
