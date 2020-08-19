#!/usr/bin/env python3
"""
analyze_rest.py
-----------

Example of uploading a CAD assembly file and fetching the processed
result using only generic dependencies (requests).

Note that we plan to release a helper libraries for both
 Typescript/Javascript and Python to reduce the boilerplate.

The most recent generated API documentation is available at:
https://docs.kerfed.com
"""

import os
import sys
import json
import time

# requests is the only non-stdlib dependency
import requests

# The root URL of the Kerfed V1 API.
API_ROOT = 'https://kerfed.com/api/v1'

# your API key
API_KEY = os.environ['KERFED_API_KEY']

# which file are we analyzing
DEMO_FILE = '../models/bent.stl'

if __name__ == '__main__':
    # get the demo model as raw bytes
    with open(DEMO_FILE, 'rb') as f:
        FILE_DATA = f.read()

    # the name to store our file remotely as
    # this is just using the filename without path
    FILENAME = os.path.split(DEMO_FILE)[-1]
    CONTENT_TYPE = 'application/octet-stream'

    # Create a Kerfed API session using our API key
    with requests.Session() as s:
        s.headers.update({
            'Content-Type': 'application/json',
            'x-api-key': API_KEY})

        # Request a signed URL to upload the file.
        # We specify our desired filename here.
        upload_response = s.post(
            '{}/uploads'.format(API_ROOT),
            json={"filename": FILENAME,
                  "contentType": CONTENT_TYPE})

        if upload_response.status_code != 201:
            raise ValueError(upload_response.text)
        upload = upload_response.json()

        print('authentication successful; received signed URL')

        # Transfer file date to the remote bucket using the signed URL
        # we generated from the first step
        with open(DEMO_FILE, 'rb') as f:
            s3_transfer_response = requests.put(
                upload['url'],
                data=f.read(),
                headers={
                    # this header must EXACTLY match the
                    # originally provided filename.
                    'x-goog-meta-filename': FILENAME,
                    'Content-Type': CONTENT_TYPE})

        if s3_transfer_response.status_code != 200:
            raise ValueError(s3_transfer_response.text)
        print('file uploaded!')

        quote_response = s.post('{}/quotes'.format(API_ROOT),
                                params={"timeout": 15000},
                                json={'uploadIds': [upload['id']],
                                      'shopId': 'kerfed'})
        if quote_response.status_code != 201:
            raise ValueError('unable to create quote!')
        quoteInfo = quote_response.json()

        for _ in range(10):
            # get the detailed information on the file we uploaded
            fileInfo = s.get('{API}/quotes/{QID}/files/{FID}'.format(
                API=API_ROOT,
                QID=quoteInfo['id'],
                FID=upload['id'])).json()

            # if the remote processing is done exit
            if fileInfo['status']['isDone']:
                break
            print('blocking until analysis completes...')
            time.sleep(2.0)

        # get the detailed information on parts in this quote
        partsInfo = s.get('{API}/quotes/{QID}/parts'.format(
            API=API_ROOT,
            QID=quoteInfo['id'])).json()
        print('analysis succeeded!')

    # Print the result of the analysis operation
    print(json.dumps(partsInfo, indent=2))

    # show the SVG preview of the first part
    # note that these signed links expire so you will need to either
    # download immediately or re-fetch the same quote later
    # for new signed URLS
    if '-t' not in sys.argv:
        import webbrowser
        webbrowser.open(partsInfo['items'][0]
                        ['methods']['flat']['drawings']['svg'])
