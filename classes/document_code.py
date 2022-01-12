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
        self.status_codes_cds = status_codes_cds

        self.guidance_cds = ""
        self.guidance_chief = ""

        self.format_guidance()
        self.format_all()
        self.check_if_used()
        self.splice_cds_chief()
        self.format_status_codes()

    def check_if_used(self):
        self.used = "Yes" if self.code in g.app.used_document_codes else "No"

    def format_all(self):
        self.code = g.app.cleanse_generic(self.code)
        self.direction = g.app.cleanse_generic(self.direction)
        self.description = g.app.cleanse_generic(self.description)
        self.guidance = g.app.cleanse_generic(self.guidance)
        self.status_codes_cds = g.app.cleanse_generic(self.status_codes_cds)
        self.status_codes_cds = self.status_codes_cds.rstrip(".")

    def format_guidance(self):
        self.guidance = re.sub(r'i\.e\. ', ', e.g. ', self.guidance)
        self.guidance = re.sub(r', , e\.g\. ', ', e.g. ', self.guidance)
        self.guidance = re.sub(r'\. ', '.\n', self.guidance)
        self.guidance = re.sub(r'\n ', '\n', self.guidance)
        self.guidance = re.sub(r'\n\n', '\n', self.guidance)
        self.guidance = re.sub(r'e\.g\.\n', 'e.g. ', self.guidance)
        self.guidance = re.sub(r'No\.\n', 'No. ', self.guidance)
        self.guidance = re.sub(
            r'GBCHDyyyy.', 'GBCHDyyyytemp_dot', self.guidance)
        self.guidance = re.sub(r' ,', ',', self.guidance)

        # Grammar issues
        self.guidance = re.sub(r'range of certificates cover the goods',
                               'range of certificates covers the goods,', self.guidance)
        self.guidance = re.sub(r'range of documents cover the goods',
                               'range of documents covers the goods,', self.guidance)
        self.guidance = re.sub(r'goods insert', 'goods, insert', self.guidance)

        # Abbreviations
        self.replace_abbreviations()

    def splice_cds_chief(self):
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
        if self.file == "chief":
            for status_code in g.app.status_codes.keys():
                self.guidance_chief = self.guidance_chief.replace(status_code, "[" + status_code + "]")
        else:
            for status_code in g.app.status_codes.keys():
                self.status_codes_cds = self.status_codes_cds.replace(status_code, "[" + status_code + "]")
