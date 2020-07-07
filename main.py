#!/bin/env/python
# -*- encoding: utf8 -*-

import argparse
import json
import logging
import os
import pathlib
import sys
from http.client import HTTPSConnection
import time
from shutil import move
from tempfile import NamedTemporaryFile
from urllib.parse import urlsplit
from pprint import pprint

__VERSION__ = "0.9.0"
__AUTHOR__ = u"Pekka Järvinen"
__YEAR__ = 2020

__DESCRIPTION__ = u"Download firmware, etc files from Broadcom web site"

__EPILOG__ = u"%(prog)s v{0} (c) {1} {2}-".format(__VERSION__, __AUTHOR__, __YEAR__)

__EXAMPLES__ = [
    u'',
    u'-' * 60,
    u'  %(prog)s -t Firmware -f files.json',
    u'  %(prog)s -t Firmware BIOS Driver UEFI EFI -f files.json',
    u'  %(prog)s -t Firmware -d 9211 -f files.json',
    u'-' * 60,
]


def dl(conn: HTTPSConnection, q: str, okresponsetype: str = None, headers: dict = {}) -> bytes:
    conn.request("GET", q, headers=headers)
    resp = conn.getresponse()

    log = logging.getLogger()
    log.info(f"HTTP: {resp.status} {resp.reason} https://{conn.host}{q}")

    if resp.status != 200:
        raise ValueError(f"url couldn't be loaded:\n{resp.read()}")
    if okresponsetype is not None and resp.headers.get_content_type().lower().find(okresponsetype.lower()) == -1:
        raise ValueError("invalid content type: {}".format(resp.headers.get_content_type()))

    readBytes = 0
    lenBytes = resp.length
    data = b''

    while chunk := resp.read(1 << 20):
        if not chunk:
            continue
        readBytes += len(chunk)
        print("  Read", readBytes, "B", end='')
        if lenBytes > 0:
            print(" /", lenBytes, "B (", resp.length, "B left)", end='')
        print()
        data += chunk

    print()

    return data


if __name__ == "__main__":

    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO,
        format='%(asctime)s %(levelname)s: %(message)s',
        datefmt="%H:%M:%S",
    )

    log = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(
        description=__DESCRIPTION__,
        epilog=__EPILOG__,
        usage=os.linesep.join(__EXAMPLES__),
    )

    # More information
    parser.add_argument('--verbose', '-v', action='count', required=False, default=0, dest='verbose',
                        help="Be verbose. -vvv..v Be more verbose.")

    # Source JSON file
    parser.add_argument('--file', '-f', type=argparse.FileType('r+', encoding='utf8'), dest='file',
                        required=True, help='JSON source file from website')

    # Destination download directory
    parser.add_argument('--directory', '-d', type=str, dest='dirname', default="dl",
                        required=False, help='Directory name')

    # Also download older archived stuff
    parser.add_argument('--archive', '-a', action='store_true', default=False, dest='archive', required=False,
                        help='Download archived (Doc_Status in json file)')

    # Only limit to these kinds of files (Firmware, BIOS, UEFI, EFI, Driver, ..)
    parser.add_argument('--type', '-t', action='store', dest='types', default='Firmware', type=str, nargs='*',
                        required=False,
                        help='Type(s) (see: DocType in source json file)')

    args = parser.parse_args()

    if int(args.verbose) > 0:
        logging.getLogger().setLevel(logging.DEBUG)
        log.info("Being verbose")

    dlitems = []

    statusfilter = "Current"
    if args.archive:
        statusfilter = "Archive"

    log.info(f"""Downloading all files that has: status '{statusfilter}' and type is one of {args.types}""")

    for item in json.load(args.file):
        if 'Downloads' not in item['contenttype']:
            continue
        del item['contenttype']

        if 'Downloads' not in item['Content_Type']:
            continue
        del item['Content_Type']

        if 'Downloads' not in item['TypeName']:
            continue
        del item['TypeName']

        # Archive or current
        if statusfilter is not None and statusfilter not in item['Doc_Status']:
            log.info(f"Skipping file {item['Doc_Status']} (wrong status) - {item['Title']}")
            continue
        del item['Doc_Status']

        # Firmware, BIOS, Driver, etc
        if item['DocType'] not in args.types:
            log.info(f"Skipping file {item['DocType']} (wrong type) - {item['Title']}")
            continue

        opsys = item['OS']
        if opsys is None:
            opsys = ""
        opsys = opsys.strip()
        opsys = opsys.replace("/", "_")

        ver = item['AssetVersion']
        if ver is None:
            ver = ""
        ver = ver.strip()

        dtype = item['DocType']
        if dtype is None:
            dtype = ""
        dtype = dtype.strip()

        dlitems.append({
            "q": "/api/document/download/" + item['PublicationNumber'],
            "fpath": os.path.join(args.dirname, ver, dtype, opsys),
        })

    headers = {
        'Accept': 'application/json;charset=UTF-8',
        'Content-Type': 'application/json',
    }

    httpconn = HTTPSConnection("docs.broadcom.com", timeout=60.0)

    for item in dlitems:
        data = json.loads(dl(httpconn, item['q'], "application/json", headers))
        urlpath = pathlib.Path(urlsplit(data['URL']).path)
        fpath = os.path.join(item['fpath'], urlpath.name)

        if os.path.isfile(fpath):
            log.info(f"{fpath} exists, skipping")
            continue
        time.sleep(1.0)

        data = dl(httpconn, data['URL'], "application/octet-stream", {})

        # Save to temporary file
        tmpf = NamedTemporaryFile("wb", prefix="dl-", suffix=urlpath.suffix, delete=False)
        with tmpf as f:
            f.write(data)
            f.flush()

        pathlib.Path(item['fpath']).mkdir(parents=True, exist_ok=True)
        newpath = move(tmpf.name, fpath)
        log.info(f"Renamed {tmpf.name} to {newpath}")
