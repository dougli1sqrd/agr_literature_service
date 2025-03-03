"""
pipenv run python generate_dqm_json_test_set.py -i inputs/sample_dqm_load.json -d dqm_load_sample/
pipenv run python generate_dqm_json_test_set.py -i inputs/sample_dqm_update.json -d dqm_update_sample/
Take large dqm json data and generate a smaller subset to test with
This takes about 90 seconds to run
"""
import argparse
import itertools
import json
import logging
import sys
from os import environ, makedirs, path

from dotenv import load_dotenv

from helper_file_processing import split_identifier

load_dotenv()


logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s - %(levelname)s - {%(module)s %(funcName)s:%(lineno)d} - %(message)s",  # noqa E251
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

parser = argparse.ArgumentParser()
parser.add_argument("-i", "--input", action="store", help="input json file to use")
parser.add_argument(
    "-d", "--directory", action="store", help="output directory to generate into"
)
args = vars(parser.parse_args())


def load_sample_json(input_file):
    base_path = environ.get("XML_PATH")
    sample_file = base_path + input_file
    print("LOADING file {}".format(sample_file))
    sample_json = {}
    try:
        with open(sample_file) as f:
            sample_json = json.load(f)
    except IOError:
        logger.info("No sample.json file at %s", sample_file)
    if not sample_json:
        return
    if "data" not in sample_json:
        logger.info('No "data" in sample.json file at %s', sample_file)
        return
    return sample_json


def generate_dqm_json_test_set_from_sample_json(input_file, output_directory):  # noqa C901
    """
    generate <output_directory>/ files based on manually chosen entries in <input_file>
    """

    base_path = environ.get("XML_PATH")
    sample_json = load_sample_json(input_file)
    if sample_json:
        sample_path = base_path + output_directory
        if not path.exists(sample_path):
            makedirs(sample_path)
        pmids_wanted = set()
        mod_ids_wanted = {}
        ids_wanted = set()
        ids_wanted_replace = {}
        for entry in sample_json["data"]:
            if "pmid" in entry:
                prefix, identifier, separator = split_identifier(entry["pmid"])
                pmids_wanted.add(identifier)
                ids_wanted.add(entry["pmid"])
                if "update_replace" in entry:
                    if entry["pmid"] not in ids_wanted_replace:
                        ids_wanted_replace[entry["pmid"]] = {}
                    for field in entry["update_replace"]:
                        ids_wanted_replace[entry["pmid"]][field] = entry["update_replace"][field]
            if "modId" in entry:
                for mod_id in entry["modId"]:
                    prefix, identifier, separator = split_identifier(mod_id)
                    if prefix not in mod_ids_wanted:
                        mod_ids_wanted[prefix] = set()
                    mod_ids_wanted[prefix].add(identifier)
                    ids_wanted.add(mod_id)
                    if "update_replace" in entry:
                        if mod_id not in ids_wanted_replace:
                            ids_wanted_replace[mod_id] = {}
                        for field in entry["update_replace"]:
                            ids_wanted_replace[mod_id][field] = entry["update_replace"][field]
        for mod in mod_ids_wanted:
            logger.info("generating sample set for %s", mod)
            input_filename = base_path + "dqm_data/REFERENCE_" + mod + ".json"
            logger.info("reading file %s", input_filename)
            dqm_data = {}
            try:
                with open(input_filename) as f:
                    dqm_data = json.load(f)
            except IOError:
                logger.info("No %s file at %s", mod, input_filename)
            if "data" not in dqm_data:
                logger.info('No "data" in %s file at %s', mod, input_filename)
                continue
            dqm_wanted = []
            for entry in dqm_data["data"]:
                if "primaryId" in entry and entry["primaryId"] in ids_wanted:
                    xref_id = entry["primaryId"]
                    if xref_id in ids_wanted_replace:
                        for field in ids_wanted_replace[xref_id]:
                            entry[field] = ids_wanted_replace[xref_id][field]
                    dqm_wanted.append(entry)
                    logger.info("Found primaryId %s in %s", entry["primaryId"], mod)
            dqm_data["data"] = dqm_wanted
            output_json_file = sample_path + "REFERENCE_" + mod + ".json"
            with open(output_json_file, "w") as json_file:
                json_data = json.dumps(dqm_data, indent=4, sort_keys=True)
                json_file.write(json_data)
                json_file.close()


def generate_dqm_json_test_set_from_start_mid_end():
    """
    generate dqm_sample/ files based on sampling from beginning, middle, and end of dqm files.

    generate half-as-big set
    sample_amount = int(len(dqm_data['data']) / 2)
    dqm_data['data'] = dqm_data['data'][:sample_amount]	# half one
    dqm_data['data'] = dqm_data['data'][-sample_amount:]	# half two

    """

    # base_path = '/home/azurebrd/git/agr_literature_service_demo/src/xml_processing/'
    base_path = environ.get("XML_PATH")
    sample_path = base_path + "dqm_sample/"
    if not path.exists(sample_path):
        makedirs(sample_path)
    sample_amount = 10
    mods = ["SGD", "RGD", "FB", "WB", "MGI", "ZFIN"]
    # mods = ['MGI']
    for mod in mods:
        logger.info("generating sample set for %s", mod)
        input_filename = base_path + "dqm_data/REFERENCE_" + mod + ".json"
        logger.info("reading file %s", input_filename)
        f = open(input_filename)
        dqm_data = json.load(f)

        reference_amount = len(dqm_data["data"])
        if reference_amount > 3 * sample_amount:
            sample1 = dqm_data["data"][:sample_amount]
            start = int(reference_amount / 2) - 1
            sample2 = dqm_data["data"][start : start + sample_amount]
            sample3 = dqm_data["data"][-sample_amount:]
            dqm_data["data"] = list(itertools.chain(sample1, sample2, sample3))
        output_json_file = sample_path + "REFERENCE_" + mod + ".json"
        with open(output_json_file, "w") as json_file:
            json_data = json.dumps(dqm_data, indent=4, sort_keys=True)
            json_file.write(json_data)
            json_file.close()


if __name__ == "__main__":
    """
    call main start function
    """

    logger.info("Starting generate_dqm_json_test_set.py")

    # generate_dqm_json_test_set_from_start_mid_end()
    if args["input"] and args["directory"]:
        generate_dqm_json_test_set_from_sample_json(args["input"], args["directory"])
    else:
        logger.info("Must pass a -i input file and a -d output directory")

    logger.info("ending generate_dqm_json_test_set.py")
