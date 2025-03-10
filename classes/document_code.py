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

        self.format_attributes()
        self.expand_status_codes()
        self.expand_guidance()
        self.set_guidance_cds()

    def format_attributes(self):
        self.code = self.code.strip()
        self.direction = self.apply_replacements(self.direction)
        self.description = self.apply_replacements(self.description)
        self.guidance = "- " + self.apply_replacements(self.guidance)
        self.status_codes_cds = self.apply_replacements(self.status_codes_cds)

        self.apply_abbreviations()

    def expand_status_codes(self):
        for status_code in g.app.status_codes:
            replacement = "\\1<abbr title='{title}'>{status_code}</abbr>\\3".format(
                title=g.app.status_codes[status_code], status_code=status_code
            )
            self.guidance = re.sub(r"(\W)(" + status_code + r")(\W|$)", replacement, self.guidance)

    def set_guidance_cds(self):
        self.guidance_cds = "No additional information is available." if self.guidance == "" else self.guidance

    def as_dict(self):
        return { "guidance_cds": self.guidance_cds }

    def expand_guidance(self):
        addendum = ""

        if (
            "No status code is required" in self.status_codes_cds
            or "No document status code is required" in self.status_codes_cds
        ):
            self.status_codes_cds = []
            addendum = "\n- No document status code is required."

        else:
            splitter = "*Please note"
            if splitter in self.status_codes_cds:
                tmp = self.status_codes_cds.split(splitter)
                self.status_codes_cds = tmp[0]
                addendum = splitter + tmp[1]

            if len(self.status_codes_cds) == 1 and self.status_codes_cds[0] == "":
                self.status_codes_cds = []

            else:
                addendum = (
                    "\n- Use one of the following [document status codes]("
                    + self.url_5b
                    + "): "
                )
        self.guidance += addendum

    def apply_replacements(self, s):
        for replacement in g.app.replacements:
            s = s.replace(replacement["from"], replacement["to"])
        return " ".join(s.split())

    def apply_abbreviations(self):
        for item in g.app.abbreviations:
            self.guidance = self.guidance.replace(
                item["from"],
                "<abbr title='" + item["to"] + "'>" + item["from"] + "</abbr>",
            )
