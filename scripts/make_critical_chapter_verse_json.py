"""
This script makes three files.
The input data is the collation editor output in the collation directories of the main edition repositories.

The first two have the same data but a slightly different structure. They are both used by the estoria-admin django app
to generate the views required to create new versions of the critical edition data.

One is a json object.
This file is saved to data/collations.json

The other is a javascript file containing a variable called COLLATION_LIST
which contains the same json object as the file above.
This file is saved to data/collations.js

The final file is a list of all of the critical text pages avilable which is used for the
VPE dropdown and is stored in data/critical_pages.js

"""
import sys
import argparse
import os
import json

DATA_DIR = '../data'
COLLATIONS_DIR = '../../../../collation/approved'

def make_critical_text_files(data_path=DATA_DIR):
    blobs = [filename.strip('.json') for filename in os.listdir(COLLATIONS_DIR)]
    blobs.sort()
    data = {}

    for blob in blobs:
        if blob == 'DS_Store':
            continue
        if 'S' in blob:
            something = blob.split('S')

            verse = something[1]
            chapter = something[0].upper().lstrip('D')
            if verse == "400>":
                print(something)
                verse = 400.1
            elif verse == "659.1":
                print(something)
                verse = 659.1

            try:
                chapter = int(chapter)
            except ValueError:
                print("Choked on", chapter)
                pass
            if not chapter in data:
                data[chapter] = []
            try:
                verse = int(verse)
            except ValueError:
                pass

            if verse == 'RUBRIC':
                verse = 'Rubric'
            if verse == 'rubric':
                verse = 'Rubric'

            if verse == 'Rubric':
                data[chapter].insert(0, verse)
            else:
                data[chapter].append(verse)
                rubric = False
                if 'Rubric' in data[chapter]:
                    data[chapter].remove('Rubric')
                    rubric = True

                try:
                    data[chapter].sort()
                except TypeError:
                    print(chapter, verse, data[chapter])

                if rubric:
                    data[chapter].insert(0, 'Rubric')

        else:
            continue

    chapters = list(data.keys())
    chapters.sort(key = lambda x: int(x))
    with open(os.path.join(data_path, 'critical_pages.js'), 'w') as js_file:
        int_chapters = [int(x) for x in chapters]
        js_file.write('CRITICAL_PAGES = ')
        json.dump(int_chapters, js_file, indent=4)

    #if we add to a new dictionary in order the order will be preserved
    new_data = {}
    for chapter in chapters:
        new_data[chapter] = data[chapter]
    with open(os.path.join(data_path, 'collations.json'), 'w') as fp:
        json.dump(new_data, fp, indent=4)
    with open(os.path.join(data_path, 'collations.js'), 'w') as js_file:
        js_file.write('COLLATION_LIST = ')
        json.dump(new_data, js_file, indent=4)


def main(argv):

    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--data_path',
                        help='the path to the data directory'
                             '(only used by the django app, use default for '
                             'webpack build)')

    args = parser.parse_args()

    if args.data_path:
        make_critical_text_files(data_path=args.data_path)
    else:
        make_critical_text_files()


if __name__ == '__main__':
    main(sys.argv[1:])
