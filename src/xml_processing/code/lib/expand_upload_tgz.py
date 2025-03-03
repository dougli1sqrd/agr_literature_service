"""
pipenv run python expand_upload_tgz.py > log_expand_upload_tgz

take list of tgz files from  chunking_pmids/20210426_01.txt (or other file),
get tgz files from  chunking_pmids/pubmed_tgz_20210426_01/<pmid>.tar.gz
expand files to  chunking_pmids/expand_tgz/<pmid>/
copy tgz to  chunking_pmids/expand_tgz/<pmid>/
get md5sum of each file into  chunking_pmids/expand_tgz/<pmid>/md5sum
upload each file to s3 at s3://agr-literature/develop/reference/documents/pubmed/pmid/<pmid>/
output log of all uploaded files and md5sums to  chunking_pmids/md5sum_20210426_01
"""


import hashlib
import logging
import logging.config

# import re
import tarfile
from os import environ, listdir, makedirs, path, rename, walk
from shutil import copy2

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# from datetime import datetime


load_dotenv()

log_file_path = path.join(path.dirname(path.abspath(__file__)), "../logging.conf")
logging.config.fileConfig(log_file_path)
logger = logging.getLogger("literature logger")
logging.getLogger("s3transfer.utils").setLevel(logging.WARNING)
logging.getLogger("s3transfer.tasks").setLevel(logging.WARNING)
logging.getLogger("s3transfer.futures").setLevel(logging.WARNING)

# base_path = '/home/azurebrd/git/agr_literature_service_demo/src/xml_processing/'
base_path = environ.get("XML_PATH", "")
process_path = base_path + "chunking_pmids/"

base_expand_dir = process_path + "expand_tgz/"
if not path.exists(base_expand_dir):
    makedirs(base_expand_dir)
temp_expand_dir = process_path + "expand_tgz/temp_expand/"
if not path.exists(temp_expand_dir):
    makedirs(temp_expand_dir)

s3_client = boto3.client("s3")


def expand_tgz(tgz_file, expand_dir):
    """

    :param tgz_file:
    :param expand_dir:
    :return:
    """

    this_tarfile = tarfile.open(tgz_file)
    this_tarfile.extractall(temp_expand_dir)
    this_tarfile.close()
    dir_list = listdir(temp_expand_dir)
    dir_to_move = temp_expand_dir + dir_list[0]
    if len(dir_list) > 1:
        logger.info("WARNING %s has %s directories", tgz_file, len(dir_list))
    rename(dir_to_move, expand_dir)


def generate_md5sum(expand_dir, pmid):
    output_md5file = expand_dir + "/md5sum"
    md5_info = ""
    with open(output_md5file, "w") as output_fh:
        dir_list = listdir(expand_dir)
        for filename in dir_list:
            if filename == "md5sum":
                continue
            file = expand_dir + "/" + filename
            md5sum = hashlib.md5(open(file, "rb").read()).hexdigest()
            output_fh.write("%s\t%s\n" % (filename, md5sum))
            md5_info += "%s/%s\t%s\n" % (pmid, filename, md5sum)
        output_fh.close()

    return md5_info


def upload_s3_dir(expand_dir, pmid):
    """

    :param expand_dir:
    :param pmid:
    :return:
    """

    # bucket is 's3://agr-literature/develop/reference/documents/pubmed/pmid/' + pmid
    bucketname = "agr-literature"
    for root, _dirs, files in walk(expand_dir):
        for filename in files:
            file = "develop/reference/documents/pubmed/pmid/" + pmid + "/" + filename
            # logger.info("%s : %s : %s", path.join(root, file), bucketname, file)
            upload_file_to_s3(path.join(root, filename), bucketname, file)


def upload_file_to_s3(filepath, bucketname, s3_file_location):
    """

    :param filepath:
    :param bucketname:
    :param s3_file_location:
    :return:
    """

    try:
        response = s3_client.upload_file(filepath, bucketname, s3_file_location)
        if response is not None:
            logger.info("boto 3 uploaded response: %s", response)
        # else:
        #     logger.info('uploaded to s3 %s %s', bucketname, filepath)
    except ClientError as e:
        logging.error(e)
        return False

    return True


def process_tgz():
    """

    :return:
    """

    date_file = "20210426_02"
    list_file = process_path + date_file + ".txt"
    count = 0
    md5_summary = ""
    with open(list_file) as list_fh:
        line = list_fh.readline()
        while line:
            count += 1
            # if count > 3:
            if count > 333333:
                break
            tabs_split = line.split("\t")
            pmid = tabs_split[0]
            tgz_file = process_path + "pubmed_tgz_" + date_file + "/" + pmid + ".tar.gz"
            expand_dir = process_path + "expand_tgz/" + pmid
            # if this script has not already run on this pmid, expand the tar gz file into a directory for the pmid
            if not path.exists(expand_dir):
                expand_tgz(tgz_file, expand_dir)
            copy2(tgz_file, expand_dir)
            md5_info = generate_md5sum(expand_dir, pmid)
            md5_summary += md5_info
            upload_s3_dir(expand_dir, pmid)
            logger.info("pmid %s", pmid)
            line = list_fh.readline()
        list_fh.close()
    summary_md5file_filename = date_file + "_md5sum.txt"
    output_md5file = process_path + "/" + summary_md5file_filename
    with open(output_md5file, "w") as output_fh:
        output_fh.write(md5_summary)
        output_fh.close()
    s3_file_location = (
        "develop/reference/documents/pubmed/tarball_chunks/pubmed_tgz_"
        + summary_md5file_filename
    )

    upload_file_to_s3(output_md5file, "agr-literature", s3_file_location)


if __name__ == "__main__":
    """
    call main start function
    """

    process_tgz()
