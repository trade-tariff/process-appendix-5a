# Process Appendix 5a data

This Python tool downloads the union and national Appendix 5a spreadsheets from
GOV.UK. It converts document codes, status codes and guidance into JSON for the
Trade Tariff service, then uploads the result to S3.

## Set up locally

Use Python 3 and an isolated virtual environment:

```sh
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt
```

The application loads `.env`. Set `URL_UNION` and `URL_NATIONAL` to the GOV.UK
pages containing the ODS downloads, and `DEST_FILE` to the local output path.
Set `AWS_BUCKET_NAME` explicitly to the approved destination. Keep credentials
outside Git.

See [classes/application.py](classes/application.py) for the input processing
and [resources/config/](resources/config/) for status codes and abbreviations.

## Run the processor

After confirming the source URLs, output path, AWS account and destination:

```sh
python3 process.py
```

This is not a read-only preview. The command downloads files, writes JSON and
uploads it as `config/cds_guidance.json` in the selected bucket. It has no
command-line dry-run mode. Do not run it against a shared bucket without approval.

## Check changes

CI runs `flake8 .` and an integration run that publishes to the development
bucket. That integration needs approved AWS access; it is not an offline unit
test. See [CI configuration](.github/workflows/ci.yml). A non-main branch push
can trigger that integration.

## Contribute

Read [CONTRIBUTING.md](CONTRIBUTING.md) for the fork workflow, checks and private
security reporting.

## Licence

The code and associated documentation use the [MIT licence](LICENCE.md), with
Crown copyright (HM Revenue & Customs). Source spreadsheets and other data
retain their own terms.
