import re
import classes.globals as g


class DocumentCode(object):
    def __init__(self, file, code, direction, level, description, guidance, status_codes_cds):
        self.file = file
        self.code = code
        self.direction = direction
        self.level = level
        self.description = description
        self.guidance = guidance
        self.status_codes_cds = str(status_codes_cds)

        self.guidance_cds = ""
        self.guidance_chief = ""
        self.url_5b = "https://www.gov.uk/government/publications/uk-trade-tariff-document-status-codes-for-harmonised-declarations/uk-trade-tariff-document-status-codes-for-harmonised-declarations"

        self.protect()
        self.format_guidance()
        self.format_all()
        self.check_if_used()
        self.format_status_codes()
        self.unprotect()
        self.splice_cds_chief()

    def check_if_used(self):
        self.used = "Yes" if self.code in g.app.used_document_codes else "No"

    def format_all(self):
        self.code = g.app.cleanse_generic(self.code)
        self.direction = g.app.cleanse_generic(self.direction)
        self.description = g.app.cleanse_generic(self.description)
        self.guidance = g.app.cleanse_generic(self.guidance)
        
        self.guidance = "- " + self.guidance.replace("\n", "\n\n- ") + "\n\n"
        self.guidance = self.guidance.replace("- - ", "\t- ")
        self.guidance = self.guidance.replace("-  - ", "\t- ")

        self.status_codes_cds = g.app.cleanse_generic(self.status_codes_cds)
        self.status_codes_cds = self.status_codes_cds.rstrip(".")

    def protect(self):
        self.guidance = re.sub(r"Note yyyy.", 'Note yyyytemp_dot', self.guidance)
        self.guidance = re.sub(r"consignment.", 'consignment', self.guidance)
        self.guidance = re.sub(r'GBCHDyyyy.', 'GBCHDyyyytemp_dot', self.guidance)
        self.guidance = re.sub(r'personal consumption or use ', 'personal consumption or use). ', self.guidance)
        self.guidance = re.sub(r'\nCUSTOMS SCHEMES', ' customs schemes', self.guidance)
        self.guidance = self.guidance.replace('ATT', 'A-T-T')
        self.guidance = self.guidance.replace('Reg.', 'Regulation')
        self.guidance = self.guidance.replace('reg.', 'regulation')

    def unprotect(self):
        self.guidance = self.guidance.replace('A-T-T', 'ATT')
        self.guidance = self.guidance.replace('- \n\n', '')

    def format_guidance(self):
        # This runs before all the replacements
        self.guidance = re.sub(r'i\.e\. ', ', e.g. ', self.guidance)
        self.guidance = re.sub(r', , e\.g\. ', ', e.g. ', self.guidance)
        self.guidance = re.sub('\. ', '.\n', self.guidance)
        self.guidance = re.sub(r'\n ', '\n', self.guidance)
        self.guidance = re.sub(r'\n\n', '\n', self.guidance)
        self.guidance = re.sub(r'e\.g\.\n', 'e.g. ', self.guidance)
        self.guidance = re.sub(r'No\.\n', 'No. ', self.guidance)
        self.guidance = re.sub(r' ,', ',', self.guidance)

        # Grammar issues
        self.guidance = re.sub(r'range of certificates cover the goods',
                               'range of certificates covers the goods,', self.guidance)
        self.guidance = re.sub(r'range of documents cover the goods',
                               'range of documents covers the goods,', self.guidance)
        self.guidance = re.sub(r'goods insert', 'goods, insert', self.guidance)
        
        # Chief only data replacements
        if self.file == "chief":
            self.guidance = self.guidance.replace("following status codes", "[status codes](" + self.url_5b + ")")
            self.guidance = self.guidance.replace("Use either status code", "Use [status code](" + self.url_5b + ")")
        # Abbreviations
        self.replace_abbreviations()

    def splice_cds_chief(self):
        if self.guidance == "":
            self.guidance = "No additional information is available."
            
        if self.file == "chief":
            self.guidance_chief = self.guidance
        else:
            self.guidance_cds = self.guidance

        del self.guidance

    def replace_abbreviations(self):
        for item in g.app.abbreviations:
            self.guidance = self.guidance.replace(
                item["from"], "<abbr title='" + item["to"] + "'>" + item["from"] + "</abbr>")

    def as_dict(self):
        ret = {
            "code": self.code,
            "direction": self.direction,
            "description": self.description,
            "guidance_cds": self.guidance_cds,
            "guidance_chief": self.guidance_chief,
            "status_codes_cds": self.status_codes_cds,
            "used": self.used
        }

        return ret

    def format_status_codes(self):
        self.status_codes_cds = self.status_codes_cds.replace("*", " *")
        self.status_codes_cds = self.status_codes_cds.replace("or ", ", ")
        if self.code == "C046":
            if self.file == "cds_union":
                a = 1
        addendum = ""
        if self.file != "chief":
            if "No status code is required" in self.status_codes_cds or "No document status code is required" in self.status_codes_cds:
                self.status_codes_cds = []
                self.guidance += "\n- No document status code is required."
            else:
                splitter = "*Please note"
                if splitter in self.status_codes_cds:
                    tmp = self.status_codes_cds.split(splitter)
                    self.status_codes_cds = tmp[0]
                    addendum = splitter + tmp[1]
                self.status_codes_cds = self.status_codes_cds.replace(" ", "")
                self.status_codes_cds = self.status_codes_cds.split(",")
                if len(self.status_codes_cds) == 1:
                    self.guidance += "\n- Use the following [document status code](" + self.url_5b + "): "
                else:
                    self.guidance += "\n- Use one of the following [document status codes](" + self.url_5b + "): "
                
                for c in self.status_codes_cds:
                    c = c.strip()
                    self.guidance += c + ", "
                
            self.guidance = self.guidance.strip()
            self.guidance = self.guidance.strip(",")
            self.guidance += addendum
            self.guidance = self.guidance.replace("\n\n\n", "\n\n")
