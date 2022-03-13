"""
This script makes the critical text for Polly's thesis which is stored as html file
in the data/critical directory. Resulting file names are
[chapter_number].html

Note this text is different from the edited text which is known as 'collation'
in the cpsf edition.

The critical.xml file should be put in transcriptions/criticalXML

"""
import sys
import argparse
import os
import shutil
import json
from lxml import etree

DATA_DIR = '../data'
CRITICAL_DIR = '../../../../transcriptions/criticalXML'
RUBRIC_TEMPLATE = '<span class="rubric">%s</span><br />\n'

class Critical(object):
    """Make critical pages."""
    def __init__(self, data_path=DATA_DIR):
        self.data_path = data_path
        parser = etree.XMLParser(resolve_entities=False)
        self.tree = etree.parse(os.path.join(CRITICAL_DIR, 'critical.xml'),
                                parser)
        # self.tree = etree.fromstring(open(os.path.join(CRITICAL_DIR,
        #                                                'critical.xml'),
        #                              'r', encoding="utf-8").read())
        self.page_path = os.path.join(data_path, 'cpsfcritical')
        self.info_count = 0
        self.page_list = []

    def process(self):
        """Process all the pages."""
        print('creating new critical pages')
        for div in self.tree.xpath('//tei:div[@type="book"]/tei:div',
                                   namespaces={'tei':
                                               'http://www.tei-c.org/ns/1.0'}):

            self.process_page(div)


        with open(os.path.join(self.data_path,
                               'cpsf_critical_pages.js'),
                  'w', encoding="utf-8") as list_fo:
            list_fo.write('CPSF_CRITICAL_PAGES = ')
            json.dump(self.page_list, list_fo, indent=4)

    def get_text(self, block):
        """ """

        text = ''

        for element in block.iter():

            if element.tag == '{http://www.tei-c.org/ns/1.0}ab':
                if element.text:
                    text += element.text
            if element.tag == '{http://www.tei-c.org/ns/1.0}head':
                if element.text:
                    text += element.text
            if element.tag == '{http://www.tei-c.org/ns/1.0}hi':
                if element.text:
                    if element.get('rend'):
                        rend = element.get('rend')
                    else:
                        rend = ""
                    text += ' <span class="hi %s">%s</span>' % (rend, element.text)
                if element.tail:
                    text += element.tail
            if element.tag == '{http://www.tei-c.org/ns/1.0}space':
                text += '<span class="space" />'
                if element.tail:
                    text += element.tail
            if element.tag =='{http://www.tei-c.org/ns/1.0}div':
                if element.get('class') == 'tooltip':
                    temp = element.getchildren()[0]
                    text += '<span class="hoverover keyterm" data-tooltip-content="#info-%d">%s</span>' % (self.info_count, element.text)
                    text += '<div class="tooltip_templates"><span id="info-%d">%s</span></div>%s' % (self.info_count, temp.text, element.tail)
                    self.info_count += 1

        return text

    def process_page(self, div):
        """Process a single page."""
        has_opening_rubric = False
        has_closing_rubric = False

        first_rubric = div.getchildren()[0]
        last_rubric = div.getchildren()[-1]
        has_opening_rubric = first_rubric.attrib['n'].lower() == "rubric"
        if last_rubric.attrib['n'].lower() == "rubric":
            if first_rubric != last_rubric:
                has_closing_rubric = True

        name = div.get('n')
        output = '<span class="chapter">%s</span>\n' % name

        if has_opening_rubric:
            #output += RUBRIC_TEMPLATE % first_rubric.text
            text = self.get_text(first_rubric)
            output += RUBRIC_TEMPLATE % text
            if has_closing_rubric:
                blocks = div.getchildren()[1:-1]
            else:
                blocks = div.getchildren()[1:]
        else:
            blocks = div.getchildren()

        for block in blocks:
            block_n = block.get('n')
            text = self.get_text(block)
            output += '<span id="%s"><sub>%s</sub>%s</span>\n' % (block_n,
                                                                  int(int(block_n)/100),
                                                                  text)

        if has_closing_rubric:
            output += '<br />'
            output += RUBRIC_TEMPLATE % last_rubric.text


        self.page_list.append(name)

        with open(os.path.join(self.page_path, '%s.html' % name),
                  'w', encoding="utf-8") as output_fo:
            output_fo.write(output)

    def clear_cpsfcritical_directory(self):
        try:
            shutil.rmtree(self.page_path)
        except:
            pass
        try:
            os.mkdir(self.page_path)
        except FileExistsError:
            pass
        print('old critical pages deleted')

def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--data_path',
                        help='the path to the data directory'
                             '(only used by the django app, use default for '
                             'webpack build)')

    args = parser.parse_args()

    if args.data_path:
        CRITICAL = Critical(data_path=args.data_path)
    else:
        CRITICAL = Critical()
    CRITICAL.clear_cpsfcritical_directory()
    CRITICAL.process()

if __name__ == "__main__":
    main(sys.argv[1:])
