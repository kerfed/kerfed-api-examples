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
        upload_response = s.post(f'{API_ROOT}/uploads', json={
            "filename": FILENAME,
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
        print('file transferred; blocking until analysis completes')

        # Create a new analysis of this uploaded assembly.
        analyze_response = s.post(
            f'{API_ROOT}/tools/analyze',
            params={"timeout": 15000},
            json={'uploadIds': [upload['id']],
                  'shopId': 'kerfed'})

        if analyze_response.status_code != 200:
            raise ValueError(analyze_response.text)
        analysis = analyze_response.json()
        print('analysis succeeded!')

    # Print the result of the analysis operation
    print(json.dumps(analysis, indent=2))

    # show the SVG preview of the first part
    # note that these signed links expire so you will need to either
    # download immediately or re-fetch the same quote later
    # for new signed URLS
    if '-t' not in sys.argv:
        import webbrowser
        webbrowser.open(analysis['parts']['items'][0]
                        ['methods']['flat']['drawings']['svg'])
