
import json
import urllib.request

import argparse
import re

from os import path
import logging
import logging.config

# pipenv run python parse_dqm_json.py -p  takes about 90 seconds to run
# pipenv run python parse_dqm_json.py -f dqm_data/ -m all > dqm_cross_references  takes 3.5 minutes without looking at pubmed json
# pipenv run python parse_dqm_json.py -f dqm_data/ -m all > dqm_cross_references  takes 12 minutes with comparing to pubmed json, but dying at MGI

#  pipenv run python parse_dqm_json.py -f /home/azurebrd/git/agr_literature_service_demo/src/xml_processing/dqm_data/ -m MGI > log_mgi
# Loading .env environment variables...
# Killed
# in 4.5 minutes, logs show it read the last pmid




log_file_path = path.join(path.dirname(path.abspath(__file__)), '../logging.conf')
logging.config.fileConfig(log_file_path)
logger = logging.getLogger('literature logger')

parser = argparse.ArgumentParser()
parser.add_argument('-p', '--generate-pmid-data', action='store_true', help='generate pmid outputs')
parser.add_argument('-f', '--file', action='store', help='take input from REFERENCE files in full path')
parser.add_argument('-m', '--mod', action='store', help='which mod, use all or leave blank for all')
# parser.add_argument('-d', '--database', action='store_true', help='take input from database query')
# parser.add_argument('-r', '--restapi', action='store', help='take input from rest api')
# parser.add_argument('-s', '--sample', action='store_true', help='test sample input from hardcoded entries')
# parser.add_argument('-u', '--url', action='store', help='take input from entries in file at url')

args = vars(parser.parse_args())

base_path = '/home/azurebrd/git/agr_literature_service_demo/src/xml_processing/'


def split_identifier(identifier, ignore_error=False):
    """Split Identifier.

    Does not throw exception anymore. Check return, if None returned, there was an error
    """
    prefix = None
    identifier_processed = None
    separator = None

    if ':' in identifier:
        prefix, identifier_processed = identifier.split(':', 1)  # Split on the first occurrence
        separator = ':'
    elif '-' in identifier:
        prefix, identifier_processed = identifier.split('-', 1)  # Split on the first occurrence
        separator = '-'
    else:
        if not ignore_error:
            self.logger.critical('Identifier does not contain \':\' or \'-\' characters.')
            self.logger.critical('Splitting identifier is not possible.')
            self.logger.critical('Identifier: %s', identifier)
            self.missing_keys[key] = 1
        prefix = identifier_processed = separator = None

    return prefix, identifier_processed, separator


# output set of PMID identifiers that will need XML downloaded
# output pmids and the mods that have them
def generate_pmid_data():
    mods = ['SGD', 'RGD', 'FB', 'WB', 'MGI', 'ZFIN']
#     mods = ['SGD']

    pmid_stats = dict()
    unknown_prefix = set()
    pmid_references = dict()
    for mod in mods:
        pmid_references[mod] = []
    non_pmid_references = dict()
    for mod in mods:
        non_pmid_references[mod] = []

    check_primary_id_is_unique = True
    check_pmid_is_unique = True

    for mod in mods:
#         filename = 'dqm_data/1.0.1.4_REFERENCE_WB_0.json'
       filename = base_path + 'dqm_data/REFERENCE_' + mod + '.json'
       f = open(filename)
       dqm_data = json.load(f)

       primary_id_unique = dict()
       pmid_unique = dict()

#        wb_papers = dict()
       mod_papers = dict()
       pmid_papers = dict()
       for entry in dqm_data['data']:

           if check_primary_id_is_unique:
               try:
                   primary_id_unique[entry['primaryId']] = primary_id_unique[entry['primaryId']] + 1
               except KeyError:
                   primary_id_unique[entry['primaryId']] = 1

           pmid = '0'
           prefix, identifier, separator = split_identifier(entry['primaryId'])
#            if prefix == 'WB':
#                wb_papers[identifier] = entry
           if prefix == 'PMID':
               pmid = identifier
#                pmid_papers[identifier] = entry
#                try:
#                    pmid_stats[identifier].append(mod)
#                except KeyError:
#                    pmid_stats[identifier] = [mod]
           elif prefix in mods:
#                mod_papers[identifier] = entry
               if 'crossReferences' in entry:
                   for cross_reference in entry['crossReferences']:
                       prefix_xref, identifier_xref, separator_xref = split_identifier(cross_reference['id'])
                       if prefix_xref == 'PMID':
                           pmid = identifier_xref
           else:
               unknown_prefix.add(prefix)

           if pmid is not '0':
               try:
                   pmid_stats[pmid].append(mod)
               except KeyError:
                   pmid_stats[pmid] = [mod]
               if check_pmid_is_unique:
                   try:
                       pmid_unique[pmid] = pmid_unique[pmid] + 1
                   except KeyError:
                       pmid_unique[pmid] = 1
               pmid_references[mod].append(pmid)
           else:
               non_pmid_references[mod].append(entry['primaryId'])

# output check of a mod's non-unique primaryIds
       if check_primary_id_is_unique:
           for primary_id in primary_id_unique:
               if primary_id_unique[primary_id] > 1:
                    print("%s primary_id %s has %s mentions" % (mod, primary_id, primary_id_unique[primary_id]))
# output check of a mod's non-unique pmids (different from above because could be crossReferences
       if check_pmid_is_unique:
           for pmid in pmid_unique:
               if pmid_unique[pmid] > 1:
                    print("%s pmid %s has %s mentions" % (mod, pmid, pmid_unique[pmid]))


#         for identifier in pmid_papers:
#             entry = pmid_papers[identifier]
#             print(identifier)
#         #     print(identifier + ' ' + entry['allianceCategory'])

# TODO create a sample of 100 entries per MOD to play with

# output each mod's count of pmid references
    for mod in pmid_references:
        count = len(pmid_references[mod])
        print("%s has %s pmid references" % (mod, count))
#         logger.info("%s has %s pmid references", mod, count)

# output each mod's count of non-pmid references
    for mod in non_pmid_references:
        count = len(non_pmid_references[mod])
        print("%s has %s non-pmid references" % (mod, count))
#         logger.info("%s has %s non-pmid references", mod, count)

# output actual reference identifiers that are not pmid
#     for mod in non_pmid_references:
#         for primary_id in non_pmid_references[mod]:
#             print("%s non-pmid %s" % (mod, primary_id))
# #             logger.info("%s non-pmid %s", mod, primary_id)

# if a reference has an unexpected prefix, give a warning
    for prefix in unknown_prefix:
        logger.info("WARNING: unknown prefix %s", prefix)

# output set of identifiers that will need XML downloaded
    output_pmid_file = base_path + 'inputs/alliance_pmids'
    with open(output_pmid_file, "w") as pmid_file:
#         for pmid in sorted(pmid_stats.iterkeys(), key=int):	# python 2
        for pmid in sorted(pmid_stats, key=int):
            pmid_file.write("%s\n" % (pmid))
        pmid_file.close()

# output pmids and the mods that have them
    output_pmid_mods_file = base_path + 'pmids_by_mods'
    with open(output_pmid_mods_file, "w") as pmid_mods_file:
        for identifier in pmid_stats:
            ref_mods_list = pmid_stats[identifier]
            count = len(ref_mods_list)
            ref_mods_str = ", ".join(ref_mods_list)
            pmid_mods_file.write("%s\t%s\t%s\n" % (identifier, count, ref_mods_str))
#             logger.info("pmid %s\t%s\t%s", identifier, count, ref_mods_str)
        pmid_mods_file.close()

    # for primary_id in primary_ids:
    #     logger.info("primary_id %s", primary_id)


# reads agr_schemas's reference.json to check for dqm data that's not accounted for there.
# outputs sanitized json to sanitized_reference_json/
# does checks on dqm crossReferences.  if primaryId is not PMID, and a crossReference is PubMed, assigns PMID to primaryId and to authors's referenceId.
# if any reference's author doesn't have author Rank, assign authorRank based on array order.
def aggregate_dqm_with_pubmed(input_path, input_mod):
    mods = ['SGD', 'RGD', 'FB', 'WB', 'MGI', 'ZFIN']
    if input_mod in mods:
        mods = [ input_mod ]
    logger.info("Aggregating DQM and PubMed data from %s using mods %s", input_path, mods)
    agr_schemas_reference_json_url = 'https://raw.githubusercontent.com/alliance-genome/agr_schemas/master/ingest/resourcesAndReferences/reference.json'
    schema_data = dict()
    with urllib.request.urlopen(agr_schemas_reference_json_url) as url:
        schema_data = json.loads(url.read().decode())
#         print(schema_data)
    for mod in mods:
        filename = args['file'] + '/REFERENCE_' + mod + '.json'
        logger.info("Processing %s", filename)
        unexpected_mod_properties = set()
        dqm_data = dict()
        with open(filename, 'r') as f:
            dqm_data = json.load(f)
            f.close()
        json_storage_path = base_path + 'sanitized_reference_json/'
        json_filename = json_storage_path + 'REFERENCE_' + mod + '.json'
        with open(json_filename, "w") as json_file:
            entries = dqm_data['data']
            sanitized_data = []
            for entry in entries:
                primary_id = entry['primaryId']
                update_primary_id = False
                orig_primary_id = entry['primaryId']
#                 print("primaryId %s" % (entry['primaryId']))
                for entry_property in entry:
                    if entry_property not in schema_data['properties']:
                        unexpected_mod_properties.add(entry_property)
                if 'crossReferences' in entry:
                    for cross_reference in entry['crossReferences']:
                        if 'pages' in cross_reference:
                            if len(cross_reference["pages"]) > 1:
                                logger.info("mod %s primaryId %s has cross reference %s with pages %s", mod, primary_id, cross_reference["id"], cross_reference["pages"])
                            else:
                                if not re.match(r"^PMID:[0-9]+", orig_primary_id):
                                    if cross_reference["pages"][0] == 'PubMed':
                                        xref_id = cross_reference["id"]
                                        if re.match(r"^PMID:[0-9]+", xref_id):
                                            update_primary_id = True
                                            primary_id = xref_id
                                            entry['primaryId'] = xref_id
                        else:
                            logger.debug("mod %s primaryId %s has cross reference %s without pages", mod, primary_id, cross_reference["id"])
                else:
                    logger.info("mod %s primaryId %s has no cross references", mod, primary_id)
                pmid_group = re.search(r"^PMID:([0-9]+)", primary_id)
                if pmid_group is None:
#                     print("primaryKey %s is None" % (primary_id))
                    if 'authors' in entry:
                        all_authors_have_rank = True
                        for author in entry['authors']:
                            if 'authorRank' not in entry:
                                all_authors_have_rank = False
                        if all_authors_have_rank == False:
                            authors_with_rank = []
                            for i in range(len(entry['authors'])):
                                author = entry['authors'][i]
                                author['authorRank'] = i + 1
                                authors_with_rank.append(author)
                            entry['authors'] = authors_with_rank
                        if update_primary_id:
                            authors_updated = []
                            for author in entry['authors']:
                                author['referenceId'] = primary_id
                                authors_updated.append(author)
                            entry['authors'] = authors_updated
                else:
                    pmid = pmid_group[1]
                    print(pmid)
                    filename = base_path + 'pubmed_json/' + pmid + '.json'
#                     print("primary_id %s is None reading %s" % (primary_id, filename))
                    pubmed_data = dict()
                    try:
                        with open(filename, 'r') as f:
                            pubmed_data = json.load(f)
                            f.close()
                    except IOError:
                        logger.info("Warning: PMID %s does not have PubMed xml, from Mod %s primary_id %s", pmid, mod, orig_primary_id)
#                     print("primary_id %s is None data %s" % (primary_id, pubmed_data['authors']))
                    if 'authors' in pubmed_data:
                        entry['authors'] = pubmed_data['authors']
                    if 'volume' in pubmed_data:
                        entry['volume'] = pubmed_data['volume']
                    if 'title' in pubmed_data:
                        entry['title'] = pubmed_data['title']
                    if 'pages' in pubmed_data:
                        entry['pages'] = pubmed_data['pages']
                    if 'issueName' in pubmed_data:
                        entry['issueName'] = pubmed_data['issueName']
                    if 'issueDate' in pubmed_data:
                        entry['issueDate'] = pubmed_data['issueDate']['date_string']
                    if 'datePublished' in pubmed_data:
                        entry['datePublished'] = pubmed_data['datePublished']['date_string']
                    if 'dateArrivedInPubmed' in pubmed_data:
                        entry['dateArrivedInPubmed'] = pubmed_data['dateArrivedInPubmed']['date_string']
                    if 'dateLastModified' in pubmed_data:
                        entry['dateLastModified'] = pubmed_data['dateLastModified']['date_string']
                    if 'abstract' in pubmed_data:
                        entry['abstract'] = pubmed_data['abstract']
                    if 'pubMedType' in pubmed_data:
                        entry['pubMedType'] = pubmed_data['pubMedType']
                    if 'publisher' in pubmed_data:
                        entry['publisher'] = pubmed_data['publisher']
                    if 'meshTerms' in pubmed_data:
                        entry['meshTerms'] = pubmed_data['meshTerms']
# some papers, like 8805 don't have keyword data, but have data from WB, aggregate from mods ?
                    if 'keywords' in pubmed_data:
                        entry['keywords'] = pubmed_data['keywords']
# these probably need to be aggregated
#                     if 'crossReferences' in pubmed_data:
#                         entry['crossReferences'] = pubmed_data['crossReferences']
                sanitized_data.append(entry)
# UNCOMMENT TO generate json
            json_data = json.dumps(sanitized_data, indent=4, sort_keys=True)
            json_file.write(json_data)
            json_file.close()

        for unexpected_mod_property in unexpected_mod_properties:
            logger.info("Warning: Unexpected Mod %s Property %s", mod, unexpected_mod_property)

# hash sanitized entries per mod into %sanitized{pmid}{mod} = data
# go through those to aggregate data that should be aggregated
# check for single fields that have different values across mods

# allianceCategory - single value, check they aren't different for entries with same PMID
# MODReferenceTypes - array of hashes, aggregate the hashes
# tags - array of hashes, aggregate the hashes
# resourceAbbreviation - single value, keep for mod data, try to resolve to journal from PMID


if __name__ == "__main__":
    """ call main start function """
    logger.info("starting parse_dqm_json.py")

# pipenv run python parse_dqm_json.py -p
    if args['generate_pmid_data']:
        logger.info("Generating PMID files from DQM data")
        generate_pmid_data()

# pipenv run python parse_dqm_json.py -f /home/azurebrd/git/agr_literature_service_demo/src/xml_processing/dqm_sample/ -m SGD
# pipenv run python parse_dqm_json.py -f /home/azurebrd/git/agr_literature_service_demo/src/xml_processing/dqm_sample/ -m WB
# pipenv run python parse_dqm_json.py -f /home/azurebrd/git/agr_literature_service_demo/src/xml_processing/dqm_sample/ -m all
    elif args['file']:
        if args['mod']:
            aggregate_dqm_with_pubmed(args['file'], args['mod'])
        else:
            aggregate_dqm_with_pubmed(args['file'], 'all')

    else:
        logger.info("No flag passed in.  Use -h for help.")

    logger.info("ending parse_dqm_json.py")

