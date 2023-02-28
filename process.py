import classes.globals as g


g.app.get_ods_files()
g.app.get_overlays()
g.app.setup_replacements_and_abbreviations()
#g.app.get_used_document_codes()
g.app.get_status_codes()
g.app.get_data()
g.app.compare_govuk_with_database()
g.app.write_json()
g.app.upload_file_to_s3()
