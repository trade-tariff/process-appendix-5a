import re
import classes.globals as g
import os


class DocumentCode(object):
    def __init__(
        self, file, code, direction, description, guidance, status_codes_cds, level = ''
    ):
        self.file = file
        self.code = code
        self.direction = direction
        self.description = description
        self.guidance = guidance
        self.status_codes_cds = str(status_codes_cds)
        self.level = level

        self.guidance_cds = ""
        self.url_5b = os.getenv("URL_5B")

        self.format_guidance()
        self.format_all()
        self.format_status_codes()
        self.splice_cds()

    def apply_replacements(self, s):
        for replacement in g.app.replacements:
            s = s.replace(replacement["from"], replacement["to"])
        return " ".join(s.split())

    def format_all(self):
        self.code = self.apply_replacements(self.code)
        self.direction = self.apply_replacements(self.direction)
        self.description = self.apply_replacements(self.description)
        self.guidance = "- " + self.apply_replacements(self.guidance)
        self.status_codes_cds = self.apply_replacements(self.status_codes_cds)

        self.status_codes_cds = self.status_codes_cds.rstrip(".")

    def format_guidance(self):

        # Abbreviations
        self.replace_abbreviations()
        self.expand_status_codes()

    def expand_status_codes(self):
        for status_code in g.app.status_codes:
            replacement = "\\1<abbr title='{title}'>{status_code}</abbr>\\3".format(
                title=g.app.status_codes[status_code], status_code=status_code
            )
            self.guidance = re.sub(r"(\W)(" + status_code + r")(\W|$)", replacement, self.guidance)

    def splice_cds(self):
        if self.guidance == "":
            self.guidance = "No additional information is available."

        self.guidance_cds = self.guidance

        del self.guidance

    def replace_abbreviations(self):
        for item in g.app.abbreviations:
            self.guidance = self.guidance.replace(
                item["from"],
                "<abbr title='" + item["to"] + "'>" + item["from"] + "</abbr>",
            )

    def as_dict(self):
        ret = {
            "guidance_cds": self.guidance_cds,
        }

        return ret

    def format_status_codes(self):
        self.status_codes_cds = self.status_codes_cds.replace("*", " *")
        self.status_codes_cds = self.status_codes_cds.replace("or ", ", ")
        addendum = ""
        if (
            "No status code is required" in self.status_codes_cds
            or "No document status code is required" in self.status_codes_cds
        ):
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
                if self.status_codes_cds[0] == "":
                    self.status_codes_cds = []

            if len(self.status_codes_cds) == 1:
                self.guidance += (
                    "\n- Use the following [document status code]("
                    + self.url_5b
                    + "): "
                )
            elif len(self.status_codes_cds) == 0:
                pass
            else:
                self.guidance += (
                    "\n- Use one of the following [document status codes]("
                    + self.url_5b
                    + "): "
                )

            for c in self.status_codes_cds:
                c = c.strip()
                self.guidance += c + ", "

        self.guidance = self.guidance.strip()
        self.guidance = self.guidance.strip(",")
        self.guidance += addendum
        self.guidance = self.guidance.replace("\n\n\n", "\n\n")
