import classes.globals as g


g.app.get_ods_files()
g.app.setup_replacements_and_abbreviations()
g.app.get_status_codes()
g.app.get_data()
g.app.write_json()
g.app.upload_file_to_s3()
