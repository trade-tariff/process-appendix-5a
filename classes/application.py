from shutil import copyfile
import os
import re
import json
import csv
from pyexcel_ods import get_data

from classes.document_code import DocumentCode
from classes.database import Database
from dotenv import load_dotenv


class Application(object):
    def __init__(self):
        folder = os.getcwd()
        self.source_folder = os.path.join(folder, "resources", "source")
        self.dest_folder = os.path.join(folder, "resources", "dest")
        self.csv_status_codes = os.path.join(
            self.source_folder, "status_codes.csv")
        self.json_output = os.path.join(
            self.dest_folder, "chief_cds_guidance.json")

        load_dotenv('.env')
        self.cds_national = os.getenv('CDS_NATIONAL_FILE')
        self.cds_union = os.getenv('CDS_UNION_FILE')
        self.chief = os.getenv('CHIEF_FILE')

        self.filenames = {
            "cds_national": self.cds_national,
            "cds_union": self.cds_union,
            "chief": self.chief
        }
        self.setup_replacements_and_abbreviations()
        self.get_used_document_codes()
        self.get_status_codes()

    def get_status_codes(self):
        print("Getting status codes")
        self.status_codes = {}
        with open(self.csv_status_codes) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=',')
            line_count = 0
            for row in csv_reader:
                status_code = row[0]
                description = self.cleanse_generic(row[1])
                self.status_codes[status_code] = description
        a = 1

    def get_data(self):
        self.document_codes_national = []
        self.document_codes_union = []
        self.document_codes_chief = []

        self.document_codes_national = {}
        self.document_codes_union = {}
        self.document_codes_chief = {}

        self.get_file("cds_union")
        self.get_file("cds_national")
        self.get_file("chief")

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
                    row_index += 1

    def combine_files(self):
        print("Combining all data sources")
        self.document_codes_all = self.document_codes_union | self.document_codes_national
        for document_code_cds in self.document_codes_all:
            try:
                self.document_codes_all[document_code_cds]["guidance_chief"] = self.document_codes_chief[document_code_cds]["guidance_chief"]
                a = 1
            except:
                self.document_codes_all[document_code_cds]["guidance_chief"] = "No additional information is available."
                a = 1
        a = 1

    def write_file(self):
        print("Writing output")
        out_file = open(self.json_output, "w")
        # self.out = {}
        # self.out["document_codes"] = self.document_codes_all
        # self.out["status_codes"] = self.status_codes
        self.out = self.document_codes_all
        # json.dump(self.document_codes_all, out_file, indent=4)
        json.dump(self.out, out_file, indent=4)
        out_file.close()

        # Copy to the OTT prototype
        dest = "/Users/mattlavis/sites and projects/1. Online Tariff/ott prototype/app/data/appendix-5a/chief_cds_guidance.json"
        copyfile(self.json_output, dest)

        # Copy to the conditions UI location
        dest = "/Users/mattlavis/sites and projects/1. Online Tariff/commodity_periods_flask/chief_cds_guidance.json"
        copyfile(self.json_output, dest)

    def check(self, array, index):
        if len(array) > index:
            return str(array[index])
        else:
            return ""

    def get_used_document_codes(self):
        # We only want to bring in the document codes that are in use

        print("Determining which document codes are used")
        codes = []
        sql = """
        select distinct (mc.certificate_type_code || mc.certificate_code) as code
        from utils.materialized_measures_real_end_dates m, measure_conditions mc 
        where (m.validity_end_date is null or m.validity_end_date::date > current_date)
        and m.measure_sid = mc.measure_sid 
        and mc.certificate_code is not null
        order by 1;
        """

        # Bring back data from the EU first
        d = Database("eu")
        rows_eu = d.run_query(sql)
        for row in rows_eu:
            codes.append(row[0])

        # Then bring back data from the UK first
        d = Database("uk")
        rows_uk = d.run_query(sql)
        for row in rows_uk:
            codes.append(row[0])

        # Then combine and de-duplicate them
        codes = list(set(codes))
        self.used_document_codes = sorted(codes)

    def setup_replacements_and_abbreviations(self):
        self.replacements = [
            {
                "from": '"',
                "to": "'"
            },
            {
                "from": '\u2019',
                "to": "'"
            },
            {
                "from": '\u2013',
                "to": "-"
            },
            {
                "from": '\u2014',
                "to": "-"
            },
            {
                "from": '\u2018',
                "to": "'"
            },
            {
                "from": '\u2022',
                "to": "\n-"
            },
            {
                "from": '\u00a0',
                "to": " "
            },
            {
                "from": '\u00fc',
                "to": "&uuml;"
            },
            {
                "from": '\u201d',
                "to": "'"
            },
            {
                "from": '\u201c',
                "to": "'"
            },
            {
                "from": '\u20ac',
                "to": "&euro;"
            },
            {
                "from": '\u00e7',
                "to": "&ccedil;"
            },
            {
                "from": '\u00f3',
                "to": "&oacute;"
            },
            {
                "from": '\u00e8',
                "to": "&egrave;"
            },
            {
                "from": '\u00e9',
                "to": "&eacute;"
            },
            {
                "from": '\u00e0',
                "to": "&agrave;"
            },
            {
                "from": '\u00e6',
                "to": "&aelig;"
            },
            {
                "from": '\u00f8',
                "to": "&oslash;"
            },
            {
                "from": 'Reg ',
                "to": "regulation "
            },
            {
                "from": 'Where certificates are not sequentially numbered ',
                "to": "Where certificates are not sequentially numbered, "
            },
            {
                "from": ' then ',
                "to": ", then "
            },
            {
                "from": ', ,',
                "to": ","
            },
            {
                "from": ',,',
                "to": ","
            },
            {
                "from": ' Where',
                "to": "\nWhere"
            },
            {
                "from": 'Complete statement',
                "to": "Complete the statement"
            },
            {
                "from": 'posts Sufficient',
                "to": "posts.\nSufficient"
            },
            {
                "from": 'Registered Export Number',
                "to": "Registered Exporter Number"
            },
            {
                "from": 'equivlant',
                "to": "equivalent"
            },
            {
                "from": ' formerly referred to as;',
                "to": ", formerly referred to as"
            },
            {
                "from": 'Imports: ICP',
                "to": "\nFor imports: ICP"
            },
            {
                "from": 'Exports: ECP',
                "to": "For exports: ECP"
            },
            {
                "from": 'temp_dot',
                "to": "."
            },
            {
                "from": '\(see document status codes for harmonised declarations for definitions\):',
                "to": ""
            },
            {
                "from": '\(see document status codes for harmonised declarations for definitions\)',
                "to": ""
            },
            {
                "from": ' \.',
                "to": "."
            },
            {
                "from": 'Use either status code',
                "to": "Use status code"
            },
            {
                "from": 'e\.g\.,',
                "to": "e.g."
            },
            {
                "from": 'i\.e\.,',
                "to": "i.e."
            },
            {
                "from": 'in\\ndocument',
                "to": "in document"
            },
            {
                "from": 'see\ndocument',
                "to": "see document"
            },
            {
                "from": 'in. Document',
                "to": "in Document"
            },
            {
                "from": '- \\n\\n',
                "to": ""
            },
            {
                "from": "products' Use",
                "to": "products'. Use"
            },
            {
                "from": ".If",
                "to": ". If"
            }
        ]

        self.abbreviations = [
            {
                "from": 'MRN',
                "to": "Movement Reference Number"
            },
            {
                "from": 'RGR',
                "to": "Returned Goods Relief"
            },
            {
                "from": 'IMA',
                "to": "Inward-Monitoring Arrangement"
            },
            {
                "from": 'ICCAT',
                "to": "International Commission For The Conservation Of Atlantic Tunas"
            },
            {
                "from": 'IOTC',
                "to": "Indian Ocean Tuna Commission"
            },
            {
                "from": 'REACH',
                "to": "Registration, Evaluation, Authorisation and Restriction of Chemicals"
            }
        ]

    def cleanse_generic(self, s):
        s = re.sub(" +", " ", s)
        for replacement in self.replacements:
            s = re.sub(replacement["from"], replacement["to"], s)
        s = re.sub(" +", " ", s)
        return s.strip()
