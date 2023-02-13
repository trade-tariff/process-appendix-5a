# Process Appendix 5a data

## Implementation steps

- Create and activate a virtual environment, e.g.

  - `python3 -m venv venv/`
  - `source venv/bin/activate`

- Install necessary Python modules via `pip3 install -r requirements.txt`

## Usage

### To pull the necessary data from gov.uk:
`python3 process.py`

## How it works

### Overview steps

- Get hold of the latest Excel files from gov.uk

- Get local overlays (if required) - this will be discussed below

- Set up the replacements and abbreviations - a lot of replacing of poorly formatted text gets done

- Get a list of the document codes that are used

- Get a list of the status codes

- Write the JSON file

### Step 1  - get the latest files

In theory, there are four files that we are interested in, as follows:

- A list of the EU’s document codes and instructions on how to enter them on CDS (CDS Union data)

- A list of the UK’s document codes and instructions on how to enter them on CDS (CDS National data)

- A list of CHIEF’s codes (UK and EU) and how to enter them (CHIEF data)

- A list of status codes

However, the list of these never changes, so there is little point in automating these - it’s just a flat HTML page on gov.uk

#### Where the files can be found

The first three files are located as downloadable .ods files on the following URLs.

**Union file**

https://www.gov.uk/government/publications/data-element-23-documents-and-other-reference-codes-union-of-the-customs-declaration-service-cds

**National file**

https://www.gov.uk/guidance/data-element-23-documents-and-other-reference-codes-national-of-the-customs-declaration-service-cds

**CHIEF data**

https://www.gov.uk/government/publications/uk-trade-tariff-document-certificate-and-authorisation-codes-for-harmonised-declarations

The current Python process, in turn for each of the files above:

- goes to the page in question

- scrapes the page using BeautifulSoup to find all “a” (hyperlink) tags

- it then looks within those “a” tags to find the first tag that has a href that contains .ods

- it then downloads the ODS file from the URL referenced

- saves a local copy

### Step 2 - Getting overlays

There are times when the CUPID team, whose job it is to manage this data, are not able to get there quickly enough, and we need to act to put in alternative content

Right now, this is easy when it’s an offline process - if we were to move this to being online and auto-generating, then we would need to ensure that this process is relatively simple

Currently, there are no overlays in use, but … there may need to be overlays in the future

The way that the current app works is:

- there is a subfolder containing overlays

- one sub-subfolder for CHIEF overlays

- one sub-subfolder for CDS overlays

if either of these folders contains any files, then these files are used to provide data for the destination JSON file instead of what comes from the ODS files

#### The content of overlays files

Overlay files are just markdown files - the content can be used as-is (with newlines replace by \n characters).

### Step 3 - Setting up replacements and abbreviation expansions

Two stages, both designed to make the data that is in the ODS files more readable to humans - the content is squished in to save space, abbreviations are used and there is little deference to layout. These two functions resolve that, as well as making the content JSON ready.

#### Stage 1 - get a list of replacements

This is a big list of terms to replace and their replacements - here is a sample- it’s much longer than this, it uses regex for replacement :

```
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
    }
]
```

When the data is generated, it does a find and replace on these terms.

#### Stage 2 - get a list of abbreviations

This is pretty much the same as above, and could just be managed using the same data in all honesty, but these replacements are done using simple string replace, not regex

They look like this …

```
[
    {
        "from": "MRN",
        "to": "Movement Reference Number"
    },
    {
        "from": "RGR",
        "to": "Returned Goods Relief"
    },
    {
        "from": "IMA",
        "to": "Inward-Monitoring Arrangement"
    }
]
```

#### Step 4 - Getting a list of document codes that have been used on the tariff

The data that is in the Union, National and CHIEF files extends above and beyond what is in the tariff: there are apparently other document codes that are used on CDS that are not attached to measures.

While older versions of this code used to look at current codes only, this in practice is no longer needed, as the ODS documents have been trimmed back a bit to remove some of the older chaff.

#### Step 5 - Getting the status codes

Status codes are fixed and live in a CSV in the config folder

#### Step 6 - Write the JSON files

As per the code, taking all the content from the ODS files, performing whatever the abbreviations and replacements dictate, then writing the JSON
