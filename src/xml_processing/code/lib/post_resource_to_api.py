# import requests
import argparse
import json
import logging
import logging.config
from os import environ, path

from dotenv import load_dotenv

from helper_file_processing import (generate_cross_references_file,
                                    load_ref_xref, split_identifier)
from helper_post_to_api import (generate_headers, get_authentication_token,
                                process_api_request)

# from datetime import datetime

load_dotenv()

# pipenv run python3 post_resource_to_api.py > log_post_resource_to_api

# base_path = '/home/azurebrd/git/agr_literature_service_demo/src/xml_processing/'
base_path = environ.get('XML_PATH', "")

# resource_fields = ['primaryId', 'nlm', 'title', 'isoAbbreviation', 'medlineAbbreviation', 'printISSN', 'onlineISSN']
# resource_fields_from_pubmed = ['title', 'isoAbbreviation', 'medlineAbbreviation', 'printISSN', 'onlineISSN']
resource_fields_not_in_pubmed = ['titleSynonyms', 'abbreviationSynonyms', 'isoAbbreviation', 'copyrightDate',
                                 'publisher', 'editorsOrAuthors', 'volumes', 'pages', 'abstractOrSummary']

# keys that exist in data
# 2021-05-24 23:06:27,844 - literature logger - INFO - key publisher
# 2021-05-24 23:06:27,844 - literature logger - INFO - key isoAbbreviation
# 2021-05-24 23:06:27,844 - literature logger - INFO - key title
# 2021-05-24 23:06:27,844 - literature logger - INFO - key primaryId
# 2021-05-24 23:06:27,844 - literature logger - INFO - key medlineAbbreviation
# 2021-05-24 23:06:27,844 - literature logger - INFO - key onlineISSN
# 2021-05-24 23:06:27,844 - literature logger - INFO - key abbreviationSynonyms
# 2021-05-24 23:06:27,844 - literature logger - INFO - key volumes
# 2021-05-24 23:06:27,844 - literature logger - INFO - key crossReferences
# 2021-05-24 23:06:27,844 - literature logger - INFO - key editorsOrAuthors
# 2021-05-24 23:06:27,844 - literature logger - INFO - key nlm
# 2021-05-24 23:06:27,845 - literature logger - INFO - key pages
# 2021-05-24 23:06:27,845 - literature logger - INFO - key printISSN


log_file_path = path.join(path.dirname(path.abspath(__file__)), '../logging.conf')
logging.config.fileConfig(log_file_path)
logger = logging.getLogger('literature logger')

parser = argparse.ArgumentParser()
parser.add_argument('-f', '--file', action='store', help='take input from RESOURCE files in full path')

args = vars(parser.parse_args())


def post_resources(input_path):      # noqa: C901
    """

    :param input_path:
    :return:
    """

    api_port = environ.get('API_PORT')
    json_storage_path = base_path + input_path + '/'
    filesets = ['NLM', 'FB', 'ZFIN']
    keys_to_remove = {'nlm', 'primaryId'}
    remap_keys = {}
    remap_keys['isoAbbreviation'] = 'iso_abbreviation'
    remap_keys['medlineAbbreviation'] = 'medline_abbreviation'
    remap_keys['abbreviationSynonyms'] = 'abbreviation_synonyms'
    remap_keys['crossReferences'] = 'cross_references'
    remap_keys['editorsOrAuthors'] = 'editors'
    remap_keys['printISSN'] = 'print_issn'
    remap_keys['onlineISSN'] = 'online_issn'
    editor_keys_to_remove = {'referenceId'}
    remap_editor_keys = {}
    remap_editor_keys['authorRank'] = 'order'
    remap_editor_keys['firstName'] = 'first_name'
    remap_editor_keys['lastName'] = 'last_name'
    remap_editor_keys['middleNames'] = 'middle_names'
    cross_references_keys_to_remove = {}
    remap_cross_references_keys = {}
    remap_cross_references_keys['id'] = 'curie'
    keys_found = set()

    api_server = environ.get('API_SERVER', 'localhost')
    url = 'http://' + api_server + ':' + api_port + '/resource/'
#     headers = {
#         'Authorization': 'Bearer <token_goes_here>',
#         'Content-Type': 'application/json',
#         'Accept': 'application/json'
#     }

    token = get_authentication_token()
    headers = generate_headers(token)

    resource_primary_id_to_curie_file = base_path + 'resource_primary_id_to_curie'
    errors_in_posting_resource_file = base_path + 'errors_in_posting_resource'

    # this updates from resources in the database, and takes 4 seconds. if updating this script,
    # comment it out after running it once
    generate_cross_references_file('resource')
    xref_ref, ref_xref_valid, ref_xref_obsolete = load_ref_xref('resource')

    # populating already_processed_primary_id from file generated by this script to log created agr resource curies and identifiers, obsoleted by xref_ref
    # already_processed_primary_id = set()
    # if path.isfile(resource_primary_id_to_curie_file):
    #     with open(resource_primary_id_to_curie_file, 'r') as read_fh:
    #         for line in read_fh:
    #             line_data = line.split("\t")
    #             if line_data[0]:
    #                 already_processed_primary_id.add(line_data[0].rstrip())

    # counter = 0
    with open(resource_primary_id_to_curie_file, 'a') as mapping_fh, open(errors_in_posting_resource_file, 'a') as error_fh:
        for fileset in filesets:
            logger.info("processing %s", fileset)
            # if fileset != 'NLM':
            #     continue

            filename = json_storage_path + 'RESOURCE_' + fileset + '.json'
            f = open(filename)
            resource_data = json.load(f)
            for entry in resource_data['data']:
                primary_id = entry['primaryId']
                prefix, identifier, separator = split_identifier(primary_id)
                if prefix in xref_ref:
                    if identifier in xref_ref[prefix]:
                        logger.info("%s\talready in", primary_id)
                        continue
                # if primary_id in already_processed_primary_id:
                #     # logger.info("%s\talready in", primary_id)
                #     continue
                # if primary_id != 'NLM:8404639':
                #     continue

                # counter += 1
                # if counter > 1:
                #     break

                # to debug json from data file before changes
                # json_object = json.dumps(entry, indent=4)
                # print("before " + json_object)

                new_entry = {}

                identifiers = set([])
                identifiers.add(primary_id)

                for key in entry:
                    keys_found.add(key)
                    # logger.info("key found\t%s\t%s", key, entry[key])
                    if key in remap_keys:
                        # logger.info("remap\t%s\t%s", key, remap_keys[key])
                        # this renames a key, but it can be accessed again in the for key loop, so sometimes a key is
                        # visited twice while another is skipped, so have to create a new dict to populate instead
                        # entry[remap_keys[key]] = entry.pop(key)
                        new_entry[remap_keys[key]] = entry[key]
                    elif key not in keys_to_remove:
                        new_entry[key] = entry[key]

                if 'cross_references' in new_entry:
                    new_list = []
                    for xref in new_entry['cross_references']:
                        new_xref = {}
                        for subkey in xref:
                            if subkey in remap_cross_references_keys:
                                new_xref[remap_cross_references_keys[subkey]] = xref[subkey]
                            elif subkey not in cross_references_keys_to_remove:
                                new_xref[subkey] = xref[subkey]
                        new_list.append(new_xref)
                    new_entry['cross_references'] = new_list
                if 'editors' in new_entry:
                    new_list = []
                    for editor in new_entry['editors']:
                        new_editor = {}
                        for subkey in editor:
                            if subkey in remap_editor_keys:
                                new_editor[remap_editor_keys[subkey]] = editor[subkey]
                            elif subkey not in editor_keys_to_remove:
                                new_editor[subkey] = editor[subkey]
                        new_list.append(new_editor)
                    new_entry['editors'] = new_list

                # UNCOMMENT to test data by replacing unique data with a timestamp
                #             xref['curie'] = str(datetime.now())
                # new_entry['iso_abbreviation'] = str(datetime.now())

                api_response_tuple = process_api_request('POST', url, headers, new_entry, primary_id, None, None)
                headers = api_response_tuple[0]
                response_text = api_response_tuple[1]
                response_status_code = api_response_tuple[2]
                log_info = api_response_tuple[3]
                response_dict = json.loads(response_text)

                # print(primary_id + "\ttext " + str(response_text))
                # print(primary_id + "\tstatus_code " + str(response_status_code))
                if log_info:
                    logger.info(log_info)

                if response_status_code == 201:
                    response_dict = response_dict.replace('"', '')
                    for identifier in identifiers:
                        logger.info("%s\t%s", identifier, response_dict)
                        mapping_fh.write("%s\t%s\n" % (identifier, response_dict))
                else:
                    logger.info("api error %s primaryId %s message %s", str(response_status_code), primary_id, response_dict['detail'])
                    error_fh.write("api error %s primaryId %s message %s\n" % (str(response_status_code), primary_id, response_dict['detail']))

                # to debug json after changes that was sent to api
                # json_object = json.dumps(new_entry, indent=4)
                # print(json_object)

        # if wanting to output keys in data for figuring out mapping
        # for key in keys_found:
        #     logger.info("key %s", key)

        mapping_fh.close
        error_fh.close


if __name__ == "__main__":
    """
    call main start function
    """

    logger.info("starting post_resource_to_api.py")

    if args['file']:
        post_resources(args['file'])

    else:
        logger.info("No flag passed in.  Use -h for help.")

    logger.info("ending post_resource_to_api.py")

# pipenv run python3 post_resource_to_api.py
