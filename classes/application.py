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
        self.source_folder = os.path.join(self.resources_folder, "source")
        self.config_folder = os.path.join(self.resources_folder, "config")
        self.csv_status_codes = os.path.join(self.config_folder, "status_codes.csv")

        func.make_folder(self.resources_folder)
        func.make_folder(self.source_folder)

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

    def get_status_codes(self):
        print("Getting status codes")
        self.status_codes = {}
        with open(self.csv_status_codes) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=",")
            for row in csv_reader:
                status_code = row[0]
                description = row[1]
                self.status_codes[status_code] = description

    def get_data(self):
        self.document_codes = {}

        self.get_file("cds_union")
        self.get_file("cds_national")
        print(len(self.document_codes), "Document codes")

    def get_file(self, file):
        print("Getting data from source:", file)

        filename = os.path.join(self.source_folder, self.filenames[file])
        data = get_data(filename)

        if not data:
            raise ValueError("Data dictionary is empty.")

        for row in next(iter(data.values()))[1:]:
            if len(row) > 0:
                code = str(row[0]).strip()
            else:
                break

            if len(row) > 4:
                try:
                    document_code = DocumentCode(
                        file,
                        code,
                        direction=row[1] or '',
                        description=row[2] or '',
                        guidance=row[3] or '',
                        status_codes_cds=row[4] or ''
                    )

                    self.document_codes[document_code.code] = document_code.as_dict()

                except Exception as e:
                    print(f"Error processing row #{code}: {e}")
                    continue
            else:
                print(f"No data for code: {code}, missing values are defaulted to empty strings")

    def write_file(self):
        print("Writing output")
        out_file = open(self.DEST_FILE, "w")
        json.dump(self.document_codes, out_file, indent=4)
        out_file.close()

    def get_today_string(self):
        return date.today().strftime("%Y-%m-%d")

    def setup_replacements_and_abbreviations(self):
        path = os.path.join(self.config_folder, "replacements.json")
        with open(path, "r") as f:
            self.replacements = json.load(f)

        path = os.path.join(self.config_folder, "abbreviations.json")
        with open(path, "r") as f:
            self.abbreviations = json.load(f)

    def get_ods_files(self):
        try:
            self.cds_national = self.get_ods_file(self.url_national, "national.ods")
            self.cds_union = self.get_ods_file(self.url_union, "union.ods")
        except Exception as e:
            print(f"Error getting files: {e}")
            sys.exit(1)

        self.filenames = {
            "cds_national": self.cds_national,
            "cds_union": self.cds_union,
        }

    def get_ods_file(self, url, dest):
        filename = os.path.join(self.source_folder, dest)
        request = requests.get(url)
        soup = BeautifulSoup(request.text, "lxml")

        for tag in soup.find_all("a", href=True):
            href = tag["href"]
            if ".ods" in href:
                r = requests.get(href)
                with open(filename, "wb") as f:
                    f.write(r.content)

                print("Extracting and saving file:", dest, os.path.getsize(filename)/1024,"kB")
                return filename

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
