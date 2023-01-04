from shutil import copyfile
import os
import re
import json
import csv
from pyexcel_ods import get_data
import os
from glob import glob

from classes.document_code import DocumentCode
from classes.database import Database
from dotenv import load_dotenv


class Application(object):
    def __init__(self):
        folder = os.getcwd()
        self.source_folder = os.path.join(folder, "resources", "source")
        self.dest_folder = os.path.join(folder, "resources", "dest")
        self.csv_status_codes = os.path.join(self.source_folder, "status_codes.csv")
        self.overlay_folder = os.path.join(folder, "resources", "overlays")
        self.overlay_folder_cds = os.path.join(folder, self.overlay_folder, "cds")
        self.overlay_folder_chief = os.path.join(folder, self.overlay_folder, "chief")

        self.json_output = os.path.join(self.dest_folder, "chief_cds_guidance.json")

        load_dotenv('.env')

        # Source files
        self.cds_national = os.getenv('CDS_NATIONAL_FILE')
        self.cds_union = os.getenv('CDS_UNION_FILE')
        self.chief = os.getenv('CHIEF_FILE')
        
        # Dest files
        self.DEST_FILE = os.getenv('DEST_FILE')
        self.PROTOTYPE_DEST_FILE = os.getenv('PROTOTYPE_DEST_FILE')

        self.filenames = {
            "cds_national": self.cds_national,
            "cds_union": self.cds_union,
            "chief": self.chief
        }
        # self.setup_replacements_and_abbreviations()
        # self.get_used_document_codes()
        # self.get_status_codes()

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
        # self.document_codes_national = []
        # self.document_codes_union = []
        # self.document_codes_chief = []

        self.document_codes_national = {}
        self.document_codes_union = {}
        self.document_codes_chief = {}

        self.get_file("cds_union")
        self.get_file("cds_national")
        self.get_file("chief")

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
                    row_index += 1

    def combine_files(self):
        print("Combining all data sources")
        self.document_codes_all = self.document_codes_union | self.document_codes_national
        for document_code_cds in self.document_codes_all:
            try:
                self.document_codes_all[document_code_cds]["guidance_chief"] = self.document_codes_chief[document_code_cds]["guidance_chief"]
                # self.document_codes_all[document_code_cds]["applies_to_chief"] = True
            except:
                self.document_codes_all[document_code_cds]["guidance_chief"] = "This document code is available on CDS only."
                pass
        a = 1

    def write_file(self):
        print("Writing output")
        out_file = open(self.json_output, "w")
        self.out = self.document_codes_all
        json.dump(self.out, out_file, indent=4)
        out_file.close()

        # Copy to the OTT prototype
        copyfile(self.json_output, self.DEST_FILE)

        # Copy to the conditions UI location
        copyfile(self.json_output, self.PROTOTYPE_DEST_FILE)

    def check(self, array, index):
        if len(array) > index:
            return str(array[index])
        else:
            return ""

    def get_used_document_codes(self):
        # We only want to bring in the document codes that are in use

        print("Determining which document codes are used")
        codes = []

        # Bring back data from the EU first
        d = Database("eu")
        sql = """
        select distinct (mc.certificate_type_code || mc.certificate_code) as code
        from utils.materialized_measures_real_end_dates m, measure_conditions mc 
        where (m.validity_end_date is null or m.validity_end_date::date > (current_date - 365))
        and m.measure_sid = mc.measure_sid 
        and mc.certificate_code is not null
        order by 1;
        """
        rows_eu = d.run_query(sql)
        for row in rows_eu:
            codes.append(row[0])

        # Then bring back data from the UK first
        d = Database("uk")
        sql = """
        select distinct (mc.certificate_type_code || mc.certificate_code) as code
        from utils.materialized_measures_real_end_dates m, measure_conditions mc 
        where (m.validity_start_date >= '2021-01-01')
        and m.measure_sid = mc.measure_sid 
        and mc.certificate_code is not null
        order by 1;
        """
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
                "from": "\.If",
                "to": "\. If"
            },
            {
                "from": "not held enter",
                "to": "not held, enter"
            },
            {
                "from": "goods enter",
                "to": "goods, enter"
            },
            {
                "from": "Ukranian",
                "to": "Ukrainian"
            },
            {
                "from": "letterss",
                "to": "letters"
            },
            {
                "from": "Enter:'",
                "to": "Enter: '"
            },
            {
                "from": "identifers",
                "to": "identifiers"
            },
            {
                "from": "Identifer",
                "to": "Identifier"
            },
            {
                "from": "approriate",
                "to": "appropriate"
            },
            {
                "from": "3 digit",
                "to": "3-digit"
            },
            {
                "from": "advance.Sufficient",
                "to": "advance. Sufficient"
            },
            {
                "from": "byt ",
                "to": "by "
            },
            {
                "from": "constitues",
                "to": "constitutes"
            },
            {
                "from": "numbered range of document cover ",
                "to": "numbered range of documents covers "
            },
            {
                "from": "exemption'as",
                "to": "exemption' as"
            },
            {
                "from": "numbered enter the",
                "to": "numbered, enter the"
            },
            {
                "from": "‘Complete statement",
                "to": "Complete statement"
            },
            {
                "from": "n - \rComplete",
                "to": "n - \nComplete"
            },
            {
                "from": "declarations use",
                "to": "declarations, use"
            },
            {
                "from": "\(see Appendix C10 for definitions\)",
                "to": ""
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

    def check_article_references(self):
        missing = []
        okay_words = [
            "tolerances.md",
            "originating_import.md",
            "originating_export.md"
        ]
        folder = "/Users/mattlavis/sites and projects/1. Online Tariff/ott prototype/app/data/roo/uk/articles"
        results = [y for x in os.walk(folder) for y in glob(os.path.join(x[0], '*.md'))]
        results.sort()
        a = 1
        for result in results:
            tmp = result.split("/")
            filename = tmp[len(tmp) - 1]
            if filename not in okay_words and "common" not in result:
                # if filename not in okay_words and "common" not in result and "gsp" not in result and "oct" not in result:
                f = open(result, "r")
                content = f.read()
                if "{{ Article" not in content:
                    missing.append(result)
                    a = 1

        missing_text = "\n".join(missing)
        file = "missing.txt"
        f = open(file, "w")
        f.write(missing_text)
        f.close()

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
        a = 1
