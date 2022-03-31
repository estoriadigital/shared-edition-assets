#!/usr/bin/python3
"""
This script is the first stage for ingesting the XML transcriptions. It splits
the XML into pages and stores a json object for each page in a file in the
data/transcription directory (further subdivided by Manuscript)
with the page number used as the name of the file. The script clears the
transcription directory before starting to make sure that any no longer wanted
pages are deleted.

The resulting JSON contains the following keys

* name - the current page number
* next - the next page number or None if there isn't one
* previous - the previous page number of None if there isn't one
* document - the manuscript siglum
* text - the XML for the page (wrapped in a 'root' element)

No arguments needed unless being run by the admin app in which case
the path to the data directory must be supplied.
Following this run add_html_to_paginated_json.py to add the html data to the json files

"""
import sys
import os
import shutil
import argparse
import json
from lxml import etree

XML_DIR = '../../../../transcriptions/manuscripts'
DATA_DIR = '../data'

class PageSplitter(object):
    """Generate pages for display"""
    def __init__(self, directory=XML_DIR, debug=False, data_path=DATA_DIR):
        self.directory = directory
        self.debug = debug
        self.page_lists = {}
        self.ns_map = {'tei': 'http://www.tei-c.org/ns/1.0'}
        self.data_path = data_path
        self.page_path = os.path.join(data_path, 'transcription')

    def separate_pages(self):
        """Go through file system to find the transcriptions and call splitting functions """
        for root, dirs, files in os.walk(self.directory):
            for file in files:
                self.filename = file
                filename = os.path.join(root, file)
                if filename.endswith('.xml'):
                    self.open_elems = []
                    self.page_count = 1
                    self.node_stack = []
                    self.waiting_for_page = []
                    self.header_done = False
                    self.original_filename = filename
                    self.siglum = file.replace('.xml', '').split('-')[0]
                    # create the subdirectory in ../transcription
                    if not os.path.exists(os.path.join(self.page_path, self.siglum)):
                        os.mkdir(os.path.join(self.page_path, self.siglum))
                    self.page_lists[self.siglum] = []

                    print(self.siglum)
                    parser = etree.iterparse(filename, events=("start", "end"), encoding="utf-8")
                    pages = self.flatten_pages(parser)
                    with open('temp_%s.xml' % self.siglum, 'w', encoding="utf-8") as output_file:
                        output_file.write('<?xml version="1.0" encoding="UTF-8"?>\n%s' % ''.join(pages).replace('{http://www.w3.org/XML/1998/namespace}', '').replace('&', '&amp;'))
                    self.split_pages()
        # print out the index for the drop down menus
        with open(os.path.join(self.data_path, 'menu_data.js'), 'w', encoding="utf-8") as list_fo:
            list_fo.write('MENU_DATA = ')
            json.dump(self.page_lists, list_fo, indent=4)

    def process_start_TEI(self, elem):
        return '<div type="root">'

    def process_end_TEI(self, elem):
        return '</div>'

    def process_start_teiHeader(self, elem):
        #self.ignore_children_of = elem.tag.replace('{http://www.tei-c.org/ns/1.0}', '')
        return '<header>'

    def process_end_teiHeader(self, elem):
        #self.ignore_children_of = None
        self.header_done = True
        return '</header>'

    def process_start_text(self, elem):
        pass

    def process_end_text(self, elem):
        pass

    def process_start_body(self, elem):
        pass

    def process_end_body(self, elem):
        pass



    def flatten_pages(self, parser):
        """this function separates the XML for the pages but leaves them in a single XML file"""
        output_text = []
        for event, elem in parser:
            try:
                new_text = getattr(self, "process_%s_%s" % (event, elem.tag.replace('{http://www.tei-c.org/ns/1.0}', '')))(elem)
            except AttributeError:
                new_text = getattr(self, "process_%s_tag" % event)(elem)
            finally:
                if new_text is not None:
                    output_text.append(new_text)
                if event == 'start' and elem.text != None:
                    if self.page_count == 1 and self.header_done == True:
                        self.waiting_for_page.append(elem.text)
                    else:
                        output_text.append(elem.text)

                if event == 'end' and elem.tail != None:
                    if self.page_count == 1 and self.header_done == True:
                        self.waiting_for_page.append(elem.tail)
                    else:
                        output_text.append(elem.tail)

        return ''.join(output_text)

    #this is used to through number folios that have not been numbered in the XML
    #they should really be numbered in the XML but T is not
    def increment_folio(self, folio):
        if folio == None:
            return '1r'
        if folio[-1] == 'r':
            return folio.replace('r', 'v')
        number = int(folio.replace('v', '')) + 1
        return '%dr' % number

    def split_pages(self):
        parser = etree.XMLParser(resolve_entities=False, encoding='utf-8')
        tree = etree.parse('temp_%s.xml' % self.siglum, parser)
        pages = tree.xpath('.//root')
        page_numbers = []

        #first get all the page numbers
        folio = None
        for page in pages:
            try:
                page_number = page.xpath('.//pb')[0].attrib['n']
                folio = page_number #should never be used but just in case some numbers are missing
            except:
                folio = self.increment_folio(folio)
                page_number = folio
            page_numbers.append(page_number)

        # now split the pages into separate files
        pages = tree.xpath('.//root')
        for i, page in enumerate(pages):
            page_json = {'document': self.siglum}
            try:
                page_json['name'] = page_numbers[i]
            except:
                print(i)
                input()
            try:
                page_json['previous'] = page_numbers[i-1]
            except IndexError:
                page_json['previous'] = None
            try:
                page_json['next'] = page_numbers[i+1]
            except IndexError:
                page_json['next'] = None
            page_json['text'] = etree.tounicode(page)
            with open(os.path.join(self.page_path, self.siglum, '%s.json' % page_json['name']), 'w', encoding="utf-8") as output_file:
                json.dump(page_json, output_file, ensure_ascii=False, indent=4)
        # clean up
        self.page_lists[self.siglum] = page_numbers

        os.remove('temp_%s.xml' % self.siglum)


    def process_start_div(self, elem):
        # this test ensures we don't include the wrapper div for the full transcription
        if 'n' in elem.attrib and elem.attrib['n'] == self.siglum:
            return '<pages>'
        else:
            return self.process_start_tag(elem)

    def process_end_div(self, elem):
        #this test ensures we don't include the wrapper div for the full transcription
        if 'n' in elem.attrib and elem.attrib['n'] == self.siglum:
            return '</root></pages>'
        else:
            return self.process_end_tag(elem)

    def process_start_tag(self, elem):
        self.node_stack.append(elem)
        tag = '<%s%s%s>' % (elem.tag.replace('{http://www.tei-c.org/ns/1.0}', ''), ' ' if len(elem.attrib) > 0 else '', ' '.join(['%s="%s"' % (name, elem.attrib[name]) for name in elem.attrib]))
        if self.page_count == 1 and self.header_done == True:
            self.waiting_for_page.append(tag)
            return ''
        return tag

    def process_end_tag(self, elem):
        self.node_stack.pop()
        tag = '</%s>' % (elem.tag.replace('{http://www.tei-c.org/ns/1.0}', ''))
        if self.page_count == 1 and self.header_done == True:
            self.waiting_for_page.append(tag)
            return ''
        return tag

    def process_start_pb(self, elem):
        if self.page_count == 1:
            self.page_count += 1
            return '<root n="%s"><pb %s/>%s' % (self.siglum, ' '.join(['%s="%s"' % (name, elem.attrib[name]) for name in elem.attrib]), ''.join(self.waiting_for_page))
        self.page_count += 1
        closures = []
        for i in reversed(self.node_stack):
            closures.append('</%s>' % i.tag.replace('{http://www.tei-c.org/ns/1.0}', ''))
        openings = []
        for i in self.node_stack:
            openings.append('<%s continued="true"%s%s>' % (i.tag.replace('{http://www.tei-c.org/ns/1.0}', ''), ' ' if len(i.attrib) > 0 else '', ' '.join(['%s="%s"' % (name, i.attrib[name]) for name in i.attrib])))
        return '%s</root><root n="%s" continued="true"><pb %s/>%s' % (''.join(closures), self.siglum, ' '.join(['%s="%s"' % (name, elem.attrib[name]) for name in elem.attrib]), ''.join(openings))

    def process_end_pb(self, elem):
        pass

    def process_start_cb(self, elem):
        tag = '<cb %s/>' % ' '.join(['%s="%s"' % (name, elem.attrib[name]) for name in elem.attrib])
        return tag

    def process_end_cb(self, elem):
        pass

    def process_start_lb(self, elem):
        tag = '<lb %s/>' % ' '.join(['%s="%s"' % (name, elem.attrib[name]) for name in elem.attrib])
        return tag

    def process_end_lb(self, elem):
        pass

    def clear_transcription_directory(self):
        try:
            shutil.rmtree(self.page_path)
        except:
            pass
        try:
            os.makedirs(self.page_path)
        except FileExistsError:
            pass
        print('old pages deleted')


def main(argv):
    """Run when module called."""

    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--data_path',
                        help='the path to the data directory for output'
                             '(only used by the estoria-admin app, use default for '
                             'webpack build)')

    args = parser.parse_args()

    if args.data_path:
        ps = PageSplitter(debug=True, data_path=args.data_path)
    else:
        ps = PageSplitter(debug=True)

    ps.clear_transcription_directory()
    ps.separate_pages()


if __name__ == '__main__':
    main(sys.argv[1:])
