# broadcom-bulk-download

Download firmwares and such from Broadcom's website as bulk.

# Requirements

* Python 3

# How to use

* First go to [broadcom's](https://www.broadcom.com/) [search page](https://www.broadcom.com/support/download-search)
* Open browser's *developer toolbar* (`CTRL + SHIFT + I`)
* Open **Network** tab in *developer tools*
* Search for your product's firmwares, drivers and so on in the page
* Find the **POST**ed URL location
* Save that file as JSON to your machine

You can list possible file types with [jq](https://stedolan.github.io/jq/) for `--type` parameter.

Example:

```
% jq -r '.[].DocType' your_saved_file.json | sort | uniq
BIOS
Case Study
Compatibility Document
Driver
EFI
FAQs
Firmware
Management Software and Tools
Product Brief
Quick Installation Guide
Solution Brief
User Guide
```

## Example for LSI 9211-8i

* Go to https://www.broadcom.com/support/download-search?pg=Legacy+Products&pf=Legacy+Host+Bus+Adapters&pn=SAS+9211-8i+Host+Bus+Adapter&pa=&po=&dk=&pl=
* Look for **POST** request
  * Example: https://www.broadcom.com/api/dnd/getdocuments?lastpubdate=2020-07-06-22%3A30%3A29&updateddate=2020-06-25-10%3A34%3A28 (⚠️ You can't open this directly because it's not **POST**ed from the search page and it's not in correct JSON format)
* Open the link and save it to your machine as a JSON file
* Finally bulk download firmware:
  * `python main.py -t Firmware BIOS EFI 'Management Software and Tools' -f your_saved_file.json`
* Download archived stuff also:
  * `python main.py -a -t Firmware BIOS EFI 'Management Software and Tools' -f your_saved_file.json`

# Usage

```
usage: 
------------------------------------------------------------
  main.py -t Firmware -f files.json
  main.py -t Firmware BIOS Driver UEFI EFI -f files.json
  main.py -t Firmware -d 9211 -f files.json
------------------------------------------------------------

Download firmware, etc files from Broadcom web site

optional arguments:
  -h, --help            show this help message and exit
  --verbose, -v         Be verbose. -vvv..v Be more verbose.
  --file FILE, -f FILE  JSON source file from website
  --directory DIRNAME, -d DIRNAME
                        Directory name
  --archive, -a         Download archived (Doc_Status in json file)
  --type [TYPES [TYPES ...]], -t [TYPES [TYPES ...]]
                        Type(s) (see: DocType in source json file)

main.py v0.9.0 (c) Pekka Järvinen 2020-
```
