#!/usr/bin/python3

"""
This needs to be run in the preparation for baking (first phase critical).
It establishes the page numbers used for the links from the critical apparatus
to the trancriptions.These links become 'baked' into the critical edition html
as the critical text is constructed.


"""
import sys
import argparse
import os
import json
from lxml import etree

DATA_DIR = '../data'

index = {}

def make_verse_page_index(data_path=DATA_DIR):
    page_path = os.path.join(data_path, 'transcription')
    for ms in os.listdir(page_path):
        dir_path = os.path.join(page_path, ms)
        print(ms)
        index[ms] = {}
        for page in os.listdir(dir_path):
            if page.endswith('.json'):
                filename = os.path.join(page_path, ms, page)
                with open(filename) as file_p:
                    data = json.load(file_p)
                    get_verses(data['text'], ms, page.replace('.json', ''))
    # write out the results
    with open(os.path.join(data_path, 'page_chapter_index.js'), 'w') as output:
        output.write('PAGE_CHAPTER_INDEX = ')
        json.dump(index, output, indent=4)


def get_verses(xml, ms, page_num):
    tree = etree.fromstring(xml)
    for chapter in tree.findall('.//div'):
        chapter_num = chapter.get('n')
        for verse in chapter.findall('.//ab'):
            if verse.get('continued'):
                pass
            else:
                verse_num = verse.get('n')
                index[ms]['D%sS%s' % (chapter_num, verse_num)] = page_num


def main(argv):

    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--data_path',
                        help='the path to the data directory'
                             '(only used by the django app, use default for '
                             'webpack build)')

    args = parser.parse_args()

    if args.data_path:
        make_verse_page_index(data_path=args.data_path)
    else:
        make_verse_page_index()


if __name__ == '__main__':
    main(sys.argv[1:])
