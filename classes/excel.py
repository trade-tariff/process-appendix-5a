import os
import xlsxwriter


class Excel(object):
    def __init__(self):
        pass

    def create_excel(self, path, filename):
        self.path = path
        self.filename = filename
        self.excel_filename = os.path.join(self.path, self.filename)

        # Open the workbook
        self.workbook = xlsxwriter.Workbook(self.excel_filename)

        # Create the formats that will be used in all sheets
        self.format_bold = self.workbook.add_format({"bold": True})
        self.format_bold.set_align("top")
        self.format_bold.set_align("left")
        self.format_bold.set_bg_color("#f0f0f0")

        self.format_wrap = self.workbook.add_format({"text_wrap": True})
        self.format_wrap.set_align("top")
        self.format_wrap.set_align("left")

        self.format_force_text = self.workbook.add_format({"text_wrap": True})
        self.format_force_text.set_align("top")
        self.format_force_text.set_align("left")
        self.format_force_text.set_num_format("@")

    def close_excel(self):
        self.workbook.close()

    def add_worksheet(self, sheet_name):
        ret = self.workbook.add_worksheet(sheet_name)
        return ret
