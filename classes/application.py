import requests
from bs4 import BeautifulSoup
from shutil import copyfile
from datetime import date
import os
import re
import json
import csv
from pyexcel_ods import get_data
import os
from glob import glob
from dotenv import load_dotenv

from classes.document_code import DocumentCode
from classes.database import Database
from classes.excel import Excel
import classes.functions as func
import boto3

class Application(object):
    def __init__(self):
        self.resources_folder = os.path.join(os.getcwd(), "resources")
        self.source_folder = os.path.join(self.resources_folder, "01. source")
        self.overlay_folder = os.path.join(self.resources_folder, "02. overlays")
        self.dest_folder = os.path.join(self.resources_folder, "03. dest")
        self.codes_folder = os.path.join(self.resources_folder, "04. codes")
        self.missing_folder = os.path.join(self.resources_folder, "05. missing")
        self.config_folder = os.path.join(self.resources_folder, "06. config")
        self.csv_status_codes = os.path.join(self.config_folder, "status_codes.csv")

        func.make_folder(self.resources_folder)
        func.make_folder(self.source_folder)
        func.make_folder(self.overlay_folder)
        func.make_folder(self.dest_folder)
        func.make_folder(self.codes_folder)
        func.make_folder(self.missing_folder)

        self.overlay_folder_cds = os.path.join(self.overlay_folder, "cds")
        self.overlay_folder_chief = os.path.join(self.overlay_folder, "chief")

        d = self.get_today_string()
        self.json_output = os.path.join(self.dest_folder, "chief_cds_guidance.json")
        self.dated_folder = os.path.join(self.dest_folder, d)
        try:
            os.mkdir(self.dated_folder)
        except Exception as e:
            pass
        self.json_output2 = os.path.join(self.dated_folder, "chief_cds_guidance_{d}.json".format(d=d))

        load_dotenv('.env')

        # URLs
        self.url_union = os.getenv('URL_UNION')
        self.url_national = os.getenv('URL_NATIONAL')
        self.url_chief = os.getenv('URL_CHIEF')

        # Dest files
        self.DEST_FILE = os.getenv('DEST_FILE')
        self.PROTOTYPE_DEST_FILE = os.getenv('PROTOTYPE_DEST_FILE')

        self.AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
        self.AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.AWS_BUCKET_NAME = os.getenv('AWS_BUCKET_NAME')
        self.AWS_REGION_NAME = os.getenv('AWS_REGION_NAME')
        self.AWS_BUCKET_KEY = os.getenv('AWS_BUCKET_KEY')

        # Features
        self.write_used_codes = func.do_boolean(os.getenv('WRITE_USED_CODES'))
        self.compare_data = func.do_boolean(os.getenv('COMPARE_DATA'))

        self.codes_on_govuk = []

    def get_status_codes(self):
        print("Getting status codes")
        self.status_codes = {}
        with open(self.csv_status_codes) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            for row in csv_reader:
                status_code = row[0]
                description = self.cleanse_generic(row[1])
                self.status_codes[status_code] = description

    def get_data(self):
        self.document_codes_national = {}
        self.document_codes_union = {}
        self.document_codes_chief = {}

        self.get_file("cds_union")
        self.get_file("cds_national")
        self.get_file("chief")
        self.codes_on_govuk.sort()

    def compare_govuk_with_database(self):
        if self.compare_data:
            print("Comparing data")
            self.missing = []
            self.missing_codes = []
            for code in self.used_document_codes:
                if code not in self.codes_on_govuk:
                    self.missing.append({code: self.code_dict[code]})
                    self.missing_codes.append(code)

            self.get_codes_related_to_missing_document_codes()

            filename = "missing-{date}.json".format(date=self.get_today_string())
            filename = os.path.join(self.missing_folder, filename)
            with open(filename, 'w') as f:
                json.dump(self.missing, f, indent=4)

    def get_codes_related_to_missing_document_codes(self):
        if self.compare_data:
            print("\nGetting examples of where missing certificates apply\n")
            codes = ",".join(self.missing_codes)
            t = tuple(self.missing_codes)
            sql = "select 'xi' as scope, c.code, m.goods_nomenclature_item_id, \
            m.geographical_area_id, ga.description as geographical_area_description, \
            m.measure_type_id, mt.description as measure_type_description, mt.direction \
            from utils.measures_real_end_dates m, measure_conditions mc, utils.materialized_certificates c, \
            utils.measure_types mt, utils.geographical_areas ga \
            where m.measure_sid = mc.measure_sid \
            and mc.certificate_type_code = c.certificate_type_code \
            and m.measure_type_id = mt.measure_type_id \
            and m.geographical_area_sid = ga.geographical_area_sid \
            and mc.certificate_code = c.certificate_code \
            and c.code in {codes} \
            and (m.validity_end_date is null or m.validity_end_date::date > current_date) \
            order by 2, 3, 6, 4;"
            sql = sql.format(codes=t)

            # Get EU matching commodities
            print("- Checking XI database")
            d = Database("eu")
            rows_eu = d.run_query(sql)

            # Get UK matching commodities
            sql = sql.replace("xi", "uk")
            print("- Checking UK database\n")
            d = Database("uk")
            rows_uk = d.run_query(sql)
            rows = rows_eu + rows_uk
            excel = Excel()
            filename = "missing_document_codes-{date}.xlsx".format(date=self.get_today_string())
            excel.create_excel(self.missing_folder, filename)
            sheet = excel.add_worksheet("document codes")
            data = ('Document code', 'Description')
            sheet.write_row('A1', data, excel.format_bold)
            sheet.set_column(0, 0, 20)
            sheet.set_column(1, 1, 100)
            sheet.freeze_panes(1, 0)

            row_count = 1
            for code in self.missing:
                sheet.write(row_count, 0, list(iter(code))[0], excel.format_wrap)
                sheet.write(row_count, 1, code.get(list(iter(code))[0]), excel.format_wrap)
                row_count += 1
            sheet.autofilter('A1:B' + str(row_count))

            # Write commodity examples
            sheet = excel.add_worksheet("commodities")
            data = ('Scope', 'Document code', 'Commodity', 'Geo area ID', 'Geo area description', 'Measure type ID', 'Measure type description', 'Trade direction')
            sheet.write_row('A1', data, excel.format_bold)
            sheet.set_column(0, 3, 20)
            sheet.set_column(4, 4, 50)
            sheet.set_column(5, 5, 20)
            sheet.set_column(6, 6, 40)
            sheet.set_column(7, 7, 20)
            sheet.freeze_panes(1, 0)
            
            row_count = 1
            for row in rows:
                for i in range(0, 8):
                    sheet.write(row_count, i, row[i], excel.format_wrap)
                row_count += 1

            sheet.autofilter('A1:H' + str(row_count))
            excel.close_excel()

    def write_json(self):
        self.combine_files()
        self.write_file()

    def get_file(self, file):
        print("Getting data from source:", file)
        filename = os.path.join(self.source_folder, self.filenames[file])
        data = get_data(filename)
        for key in data:
            if key == "Sheet1":
                data = data[key]
                row_index = 1
                for row in data:
                    if row_index > 1:
                        if file == "chief":
                            code = self.check(row, 0).strip()
                            direction = self.check(row, 1)
                            level = self.check(row, 2)
                            description = self.check(row, 3)
                            guidance = self.check(row, 4)
                            status_codes_cds = ""
                        else:
                            code = self.check(row, 0).strip()
                            direction = self.check(row, 1)
                            description = self.check(row, 2)
                            guidance = self.check(row, 3)
                            status_codes_cds = self.check(row, 4)
                            level = ""

                        if code != "":
                            document_code = DocumentCode(file, code, direction, level, description, guidance, status_codes_cds)

                            if file == "cds_union":
                                self.document_codes_union[document_code.code] = document_code.as_dict()
                            elif file == "cds_national":
                                self.document_codes_national[document_code.code] = document_code.as_dict()
                            elif file == "chief":
                                self.document_codes_chief[document_code.code] = document_code.as_dict()

                            if code not in self.codes_on_govuk:
                                self.codes_on_govuk.append(code)
                    row_index += 1

    def combine_files(self):
        print("Combining all data sources")
        self.document_codes_all = self.document_codes_union | self.document_codes_national
        for document_code_cds in self.document_codes_all:
            try:
                self.document_codes_all[document_code_cds]["guidance_chief"] = self.document_codes_chief[document_code_cds]["guidance_chief"]
            except:
                self.document_codes_all[document_code_cds]["guidance_chief"] = "This document code is available on CDS only."
                pass

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

    def get_overlays(self):
        path = os.path.join(self.overlay_folder_cds, "*.md")
        md_files = []
        for file in glob(path):
            md_files.append(file)

        md_files.sort()
        self.overlays = {}
        for file in md_files:
            document_code = file.replace(".md", "")
            document_code = document_code.replace(self.overlay_folder_cds, "")
            document_code = document_code.replace("/", "")
            f = open(file, "r")
            contents = f.read()
            self.overlays[document_code] = contents

    def get_ods_files(self):
        self.cds_national = self.get_ods_file(self.url_national, "national.ods")
        self.cds_union = self.get_ods_file(self.url_union, "union.ods")
        self.chief = self.get_ods_file(self.url_chief, "chief.ods")

        self.filenames = {
            "cds_national": self.cds_national,
            "cds_union": self.cds_union,
            "chief": self.chief
        }

    def get_ods_file(self, url, dest):
        dated_folder = os.path.join(self.source_folder, self.get_today_string())
        if not os.path.exists(dated_folder):
            os.mkdir(dated_folder)
        request = requests.get(url)
        soup = BeautifulSoup(request.text, 'lxml')
        href_tags = ["a"]
        for tag in soup.find_all(href_tags):
            href = tag.attrs["href"]
            if ".ods" in href:
                r = requests.get(href)
                filename = os.path.join(self.source_folder, "latest", dest)
                with open(filename, 'wb') as f:
                    f.write(r.content)
                filename2 = os.path.join(dated_folder, dest)
                copyfile(filename, filename2)
                break

        return filename2

    def upload_file_to_s3(self):
        session = boto3.Session(
            aws_access_key_id=self.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY,
            region_name=self.AWS_REGION_NAME
        )
        s3 = session.resource('s3')
        s3.meta.client.upload_file(Filename=self.DEST_FILE, Bucket=self.AWS_BUCKET_NAME, Key=self.AWS_BUCKET_KEY)
