from bs4 import BeautifulSoup
from datetime import date
from dotenv import load_dotenv
from glob import glob
from pyexcel_ods import get_data
from shutil import copyfile
from botocore.exceptions import NoCredentialsError
import boto3
import csv
import json
import os
import re
import sys
import requests

from classes.document_code import DocumentCode
import classes.functions as func

load_dotenv(".env")


class Application(object):
    def __init__(self):
        self.resources_folder = os.path.join(os.getcwd(), "resources")
        self.source_folder = os.path.join(self.resources_folder, "01. source")
        self.dest_folder = os.path.join(self.resources_folder, "03. dest")
        self.codes_folder = os.path.join(self.resources_folder, "04. codes")
        self.missing_folder = os.path.join(self.resources_folder, "05. missing")
        self.config_folder = os.path.join(self.resources_folder, "06. config")
        self.csv_status_codes = os.path.join(self.config_folder, "status_codes.csv")

        func.make_folder(self.resources_folder)
        func.make_folder(self.source_folder)
        func.make_folder(self.dest_folder)
        func.make_folder(self.codes_folder)
        func.make_folder(self.missing_folder)

        d = self.get_today_string()
        self.json_output = os.path.join(self.dest_folder, "cds_guidance.json")
        self.dated_folder = os.path.join(self.dest_folder, d)
        try:
            os.mkdir(self.dated_folder)
        except Exception:
            pass

        self.json_output2 = os.path.join(
            self.dated_folder, "chief_cds_guidance_{d}.json".format(d=d)
        )

        # URLs
        self.url_union = os.getenv("URL_UNION")
        self.url_national = os.getenv("URL_NATIONAL")

        # Dest files
        self.DEST_FILE = os.getenv("DEST_FILE")

        # Bucket configuration
        self.AWS_BUCKET_NAME = (
            os.getenv("AWS_BUCKET_NAME") or "trade-tariff-persistence-development"
        )
        self.CDS_SYNONYM_OBJECT_PATH = "config/cds_guidance.json"

        self.codes_on_govuk = []

    def get_status_codes(self):
        print("Getting status codes")
        self.status_codes = {}
        with open(self.csv_status_codes) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=",")
            for row in csv_reader:
                status_code = row[0]
                description = self.cleanse_generic(row[1])
                self.status_codes[status_code] = description

    def get_data(self):
        self.document_codes_national = {}
        self.document_codes_union = {}

        self.get_file("cds_union")
        self.get_file("cds_national")
        self.codes_on_govuk.sort()

    def write_json(self):
        self.combine_files()
        self.write_file()

    def get_file(self, file):
        print("Getting data from source:", file)
        filename = os.path.join(self.source_folder, self.filenames[file])
        data = get_data(filename)

        for row in next(iter(data.values()))[1:]:
            code = self.check(row, 0).strip()
            direction = self.check(row, 1)
            description = self.check(row, 2)
            guidance = self.check(row, 3)
            status_codes_cds = self.check(row, 4)
            level = ""

            if code != "":
                document_code = DocumentCode(
                    file,
                    code,
                    direction,
                    level,
                    description,
                    guidance,
                    status_codes_cds,
                )

                if file == "cds_union":
                    self.document_codes_union[
                        document_code.code
                    ] = document_code.as_dict()
                elif file == "cds_national":
                    self.document_codes_national[
                        document_code.code
                    ] = document_code.as_dict()

                if code not in self.codes_on_govuk:
                    self.codes_on_govuk.append(code)

    def combine_files(self):
        print("Combining all data sources")
        print(len(self.document_codes_union), "Union codes")
        print(len(self.document_codes_national), "National codes")

        self.document_codes_all = (
            self.document_codes_union | self.document_codes_national
        )

        print(len(self.document_codes_all), "Total document codes")

    def write_file(self):
        print("Writing output")
        out_file = open(self.json_output, "w")
        self.out = self.document_codes_all
        json.dump(self.out, out_file, indent=4)
        out_file.close()

        # Copy to the OTT prototype
        copyfile(self.json_output, self.DEST_FILE)

        # Copy to the dated folder
        copyfile(self.json_output, self.json_output2)

    def check(self, array, index):
        if len(array) > index:
            return str(array[index])
        else:
            return ""

    def get_today_string(self):
        return date.today().strftime("%Y-%m-%d")

    def setup_replacements_and_abbreviations(self):
        path = os.path.join(self.config_folder, "replacements.json")
        with open(path, "r") as f:
            self.replacements = json.load(f)

        path = os.path.join(self.config_folder, "abbreviations.json")
        with open(path, "r") as f:
            self.abbreviations = json.load(f)

    def cleanse_generic(self, s):
        s = re.sub(" +", " ", s)
        for replacement in self.replacements:
            s = re.sub(replacement["from"], replacement["to"], s)
        s = re.sub(" +", " ", s)
        return s.strip()

    def get_ods_files(self):
        self.cds_national = self.get_ods_file(self.url_national, "national.ods")
        self.cds_union = self.get_ods_file(self.url_union, "union.ods")

        self.filenames = {
            "cds_national": self.cds_national,
            "cds_union": self.cds_union,
        }

    def get_ods_file(self, url, dest):
        dated_folder = os.path.join(self.source_folder, self.get_today_string())
        if not os.path.exists(dated_folder):
            os.mkdir(dated_folder)
        request = requests.get(url)
        soup = BeautifulSoup(request.text, "lxml")
        href_tags = ["a"]
        filename2 = ""

        for tag in soup.find_all(href_tags):
            href = tag.attrs["href"]
            if ".ods" in href:
                r = requests.get(href)
                filename = os.path.join(self.source_folder, "latest", dest)
                with open(filename, "wb") as f:
                    f.write(r.content)
                filename2 = os.path.join(dated_folder, dest)
                copyfile(filename, filename2)
                break

        return filename2

    def upload_file_to_s3(self):
        try:
            s3_client = boto3.client("s3")

            s3_client.upload_file(
                self.DEST_FILE,
                self.AWS_BUCKET_NAME,
                self.CDS_SYNONYM_OBJECT_PATH,
            )
        except NoCredentialsError:
            print("No AWS credentials found")
            sys.exit(1)
