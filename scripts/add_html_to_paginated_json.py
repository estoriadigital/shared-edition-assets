#!/usr/bin/python3

"""
This script uses the paginated json created by make_paginated_json.py and
adds two html strings created from the XML already stored in the json.

* html - the version of the html which expands the abbreviations
* html_abbrev - the version of the html which displayes the abbreviated forms

The script finds all the pages and generates the html required for each one.

While most of the processing uses a stream parser some preparation is done using
the full tree.

* process_app does some preprocessing on app tags by
** removing the orig rdg all together
** removing the type 2 segs from the lit reading

NB. We do this because line breaks withint rdg tags were only recorded in the lit
reading so using orig as the original reading loses the line breaks. By losing
the type 2 segs from the lit reading we end up with the original reading plus
the line breaks.

* process_choice does some preprocessing on choice tags connected with expanding
abbreviations by
** constructing a list of hover overs for <choice> type abbreviations (there
are also <am><ex> types) which have the expanded and original form
** removes the form not required with the current abbreviation settings. This
way we don't have to worry about the settings later when it is more difficult
without access to the containing <choice> tag.

We also count columns in advance in order to be specific about the display. We
use bootstrap and its 12 column layout to allow us to do subcolumns etc. so we
need to know the number of main columns for the page so we can divide by 12 to
set the columns sizes.

Because we stream parse most of this there are lots of flags to allow us to
keep track of the context that matters.

Each tag that needs special handling has a process_start_[tagname] and
process_end_[tagname] function.

No arguments added unless being run by the admin app in which case
the path to the data directory must be supplied.
If the transcriptions have changed you must run make_paginated_json.py first

"""
import sys
import argparse
import re
import os
import io
import json
from xml.etree.ElementTree import iterparse, ParseError
from lxml import etree
from cgitb import text

DATA_DIR = '../data'
NO_TAIL = -666
FORCE = True

class DisplayTextGenerator(object):
    """Generate pages for display."""
    def __init__(self,
                 data_path=DATA_DIR,
                 debug=False,
                 expanded=False):
        self.data_path = data_path
        self.page_path = os.path.join(data_path, 'transcription')
        self.expanded = expanded
        self.debug = debug
        self.abbreviations = []
        self.app_tag_open = False


    def generate_all_pages(self):
        """Go through file system to find the pages and call generate_page on each"""
        if self.expanded:
            print('adding expanded html')
        else:
            print('adding abbreviated html')
        for directory in os.listdir(self.page_path):
            dir_path = os.path.join(self.page_path, directory)
            print(directory)
            for filename in os.listdir(dir_path):
                if filename.endswith('.json'):

                    if self.debug:
                        print(directory, filename)

                    try:
                        self.generate_page(directory, filename)
                    except ParseError:
                        if self.debug:

                            print("Skipping:", directory, filename)


    def remove_segs(self, rdg):
        for seg in rdg.findall('.//seg[@type="2"]'):
            tail = seg.tail
            if tail is not None:
                sibling = seg.xpath('preceding-sibling::*')[0]
                if sibling.tail != None:
                    sibling.tail = sibling.tail + tail
                else:
                    sibling.tail = tail
            seg.getparent().remove(seg)


    def process_app(self, text, document, page):
        try:
            root_element = etree.fromstring(text)
        except etree.XMLSyntaxError:
            print("Not parsing apps of %s, %s" % (document, page))
            return text
        apps = root_element.findall('.//app')

        for app in apps:
            rdgs = app.findall('./rdg')
            for rdg in rdgs:
                if rdg.attrib['type'] == 'orig':
                    app.remove(rdg)
                if rdg.attrib['type'] == 'lit':
                    self.remove_segs(rdg)
        outputtext = etree.tostring(root_element,encoding="unicode")
        return outputtext

    def process_choice(self, text, document, page):
        try:
            root_element = etree.fromstring(text)
        except etree.XMLSyntaxError:
            print("Not parsing choices of %s, %s" % (document, page))
            return text
        choices = root_element.findall('.//choice')
        for choice in choices:
            abbr = choice.find('./abbr')
            abbr_string = str(etree.tostring(abbr), 'utf-8').replace('\n', '')
            expan = choice.find('./expan')
            expan_string = str(etree.tostring(expan), 'utf-8').replace('\n', '')
            self.choice_hovers.append('%s expands to %s' % (re.sub('<.*?>', '', abbr_string),\
                                                       re.sub('<.*?>', '', expan_string)))

            if self.expanded:
                choice.remove(abbr)
            else:
                choice.remove(expan)

        outputtext = etree.tostring(root_element,encoding="unicode")
        return outputtext


    def count_columns(self, data, document, page):
        try:
            root_element = etree.fromstring(data['text'])
        except etree.XMLSyntaxError:
            print("Not parsing xml of %s, %s" % (document, page))
        cbs = root_element.findall('.//cb')
        column_structure = {}
        for cb in cbs:
            try:
                n = cb.attrib['n']
            except:
                n = 'a'
            if n.find('-') == -1:
                if n not in column_structure:
                    column_structure[n] = []
            else:
                splitn = n.split('-')
                if splitn[0] not in column_structure:
                    column_structure[splitn[0]] = []
                if splitn[1] not in column_structure[splitn[0]]:
                    column_structure[splitn[0]].append(splitn[1])
        return column_structure




    def generate_page(self,
                      document="Q",
                      page="2r.json"):
        """Generate a single display page."""
        self.sigla = document
        self.page = page.replace('.json', '')
        self.past_first_chapter_div = False
        self.past_first_ab = False
        self.column_number = 0
        self.in_main_column = False
        self.current_main_column = 'a'
        self.current_subcolumn = None
        self.subcolumn = False
        self.waiting_for_column = []
        self.in_rubric = False
        self.in_hi = False
        self.hi_list = []

        self.app_pos = 0
        self.app_open = False

        self.choice_pos = 0
        self.choice_open = False
        self.choice_hovers = []

        self.ex_open = False
        self.ex_text = []
        self.am_open = False
        self.am_text = []
        self.amex_pos = 0
        self.note_pos = 0

        self.abbr_open = False
        self.expan_open = False



        filename = os.path.join(self.page_path, document, page)
        with open(filename, encoding="utf-8") as file_p:
            data = json.load(file_p)
        self.column_structure = self.count_columns(data, document, page)

        if data['text']:
            cleaned = self.process_app(data['text'].replace('\n', ''), document, page)
            cleaned = self.process_choice(cleaned, document, page)
        else:
            cleaned = data['text']
        datastream = io.StringIO(cleaned)

        # iterparse is not deprecated
        # https://github.com/PyCQA/pylint/issues/947
        # pylint: disable=deprecated-method
        parser = iterparse(datastream, events=("start", "end"))
        output_text = []

        for event, element in parser:
            try:
                new_text = getattr(self,
                                   "process_%s_%s" % (event,
                                                      element.tag))(element)
            except AttributeError:
                if self.debug:
                    print("Skipping %s." % element.tag)
                if element.text:
                    self.update_text(output_text, element.text)
                    new_text = None
            else:
                if new_text == NO_TAIL:
                    pass
                elif new_text:
                    self.update_text(output_text, new_text)
            if element.tail and event == 'end':
                if new_text != NO_TAIL:
                    self.update_text(output_text, element.tail)


        if self.expanded:
            data['html'] = ''.join(output_text)
        else:
            data['html_abbrev'] = ''.join(output_text)

        with open(filename, 'w', encoding="utf-8") as file_p:
            json.dump(data, file_p, ensure_ascii=False, indent=4)

    #this function adds text to the output stream and also to the hover over
    #details for am and ex tags
    def update_text(self, output_text, text):
        output_text.append(text)
        if self.am_open:
            if len(self.am_text) == 0:
                text = text[text.find('>')+1:]
            self.am_text.append(text)
        if self.ex_open:
            if len(self.ex_text) == 0:
                text = text[text.find('>')+1:]
            self.ex_text.append(text)



    #what follows are the specific instructions for the handling of the
    #XML tags


    def process_start_root(self, element):
        pass

    def process_end_root(self, element):
        if self.subcolumn:
            return '</div></div></div></div>'
        if self.in_main_column:
            return '</div></div>'
        return ''

    def process_start_text(self, element):
        """Text is the root element at the top of the file.
        Do nothing at the moment."""
        pass

    def process_end_text(self, element):
        """Text is the root element at the top of the file.
        Close the current column at the end of the text."""
        return '</div>'

    def process_start_body(self, element):
        """Body is a root at the top of the file.
        Do nothing at the moment."""
        pass

    def process_end_body(self, element):
        """Body is a root at the top of the file.
        Do nothing at the moment."""
        pass

    def process_start_cb(self, element):
        """Column break is important and complex. We have main columns and
        subcolumns. sometimes subcolumns appear in the XML before a main column
        so we need to force a main column in those situations
        2022 update: bootstrap5 requires columns to be wrapped in a
        div@class=row element so this is now even more complicated.
        Also we need to close and reopen any open spans (rubric hopefully only
        one) either side of the div"""
        column_html = []
        add_opening_rubric = False
        if self.in_rubric and self.column_number != 0:
            column_html.append('</span>')
            add_opening_rubric = True
        if self.in_hi:
            column_html.extend(['</span>' for x in self.hi_list])
        if 'n' in element.attrib:
            if element.attrib['n'].find('-') == -1:
                main = True
                main_id = element.attrib['n']
                subcolumn_id = None
            else:
                main = False
                main_id = element.attrib['n'].split('-')[0]
                subcolumn_id = element.attrib['n'].split('-')[1]
        else:
            main = True
            main_id = self.current_main_column
            if self.debug:
                print('fix column here')

        if self.column_number == 0:
            #this is the first column on the page so it must include a main
            #column regardless of its type
            self.column_number = 1
            held_string = ''
            if len(self.waiting_for_column) > 0:
                held_string = ''.join(self.waiting_for_column)
                self.waiting_for_column = [] #reset although probably not needed as it is reset on pages anyway

            column_html.append('<div class="row"><div class="column col-md-%d">' % (12/len(self.column_structure)))
            self.in_main_column = True

            self.current_main_column = main_id
            if main:
                column_html.append(held_string)
            else:
                column_html.append('<div class="row"><div class="subcolumn col-md-%d">' % (12/len(self.column_structure[main_id])))
                column_html.append(held_string)
                self.subcolumn = True
                self.current_subcolumn = subcolumn_id

        else:
            if main and main_id != self.current_main_column:
                if self.subcolumn:
                    column_html.append('</div></div>')
                    self.subcolumn = False
                column_html.append('</div>')
                column_html.append('<div class="column col-md-%d">' % (12/len(self.column_structure)))
                self.in_main_column = True
                self.current_main_column = main_id
            elif main and main_id == self.current_main_column: #this is end of subcolumn and associated row
                column_html.append('</div></div>')
                self.subcolumn = False
            elif not main and main_id != self.current_main_column:
                if self.subcolumn:
                    column_html.append('</div>')
                column_html.append('</div>')
                column_html.append('</div>')
                column_html.append('<div class="column col-md-%d">' % (12/len(self.column_structure)))
                self.in_main_column = True
                self.current_main_column = main_id
                column_html.append('<div class="row"><div class="subcolumn col-md-%d">' % (12/len(self.column_structure[main_id])))
                self.current_subcolumn = subcolumn_id
                self.subcolumn = True
            elif not main:
                if self.subcolumn:
                    column_html.append('</div>')
                else:
                    column_html.append('<br class="clear"/><div class="row">')
                column_html.append('<div class="subcolumn col-md-%d">' % (12/len(self.column_structure[main_id])))
                self.subcolumn = True
        if self.in_hi:
            column_html.append(''.join(self.hi_list))
        if add_opening_rubric:
            column_html.append('<span class="rubric">')
        return ''.join(column_html)

    def process_end_cb(self, element):
        """Column break is Milestone, so we don't end the div here,
        we end it in text."""
        pass


    def process_start_div(self, element):
        """Div. Chapter number."""
        if 'n' in element.attrib:
            if not self.past_first_chapter_div:
                self.past_first_chapter_div = True
                try:
                    chapter_number = int(element.attrib['n'])
                except ValueError:
                    if FORCE:
                        chapter_number = 0
                    else:
                        raise
                #starting_chapter = str(chapter_number - 1)
                #return '<span class="chapter">(%s)</span>' % starting_chapter

            if len(element.attrib['n']) == 0:
                #this is a probably continuation of a chapter so no marker needed
                return ''
            elif 'continued' in element.attrib and element.attrib['continued'] == 'true':
                #this is a continuation of a chapter so no marker needed
                return ''
            else:
                return '<br class="clear" /><span class="chapter">%s</span>' % \
                    element.attrib['n']
        else:
            return element.text

    def process_end_div(self, element):
        """End of chapter div, do nothing."""
        pass

    def process_start_lb(self, element):
        """Line break."""
        if 'rend' in element.attrib and element.attrib['rend'] == 'hyphen':
            return '<br />\n' #TODO: put the hyphen back in once the page/column stuff is fixed
        else:
            return '<br />\n'

    def process_end_lb(self, element):
        """Line break is Milestone, so we don't do anything."""
        pass

    # def process_start_ab(self, element):
    #     """Block."""
    #     text = ""
    #     if not self.past_first_ab:
    #         self.past_first_ab = True
    #     else:
    #         text += '</span>'
    #     try:
    #         identifier = element.attrib['n']
    #     except KeyError:
    #         if FORCE:
    #             identifier = "000"
    #         else:
    #             raise
    #     if len(identifier) == 0:
    #         #then for some reason this doesn't have an identifier so don't add title
    #         text += '<span class="ab">'
    #     else:  #we need to get the number right and display it
    #         if identifier[-1] == '0' and identifier[-2] == '0':
    #             identifier = identifier[:-2]
    #         elif identifier[-1] == '0':
    #             identifier = '%s.%s' % (identifier[:-2], identifier[-2])
    #         else:
    #             identifier = '%s.%s' % (identifier[:-2], identifier[-2:])
    #         if 'continued' in element.attrib and element.attrib['continued'] == 'true':
    #             text += '<span class="ab" id="%s">' % identifier
    #         else:
    #             text += '<span class="ab" id="%s"><sub>%s</sub>&nbsp;' % (identifier,
    #                                                           identifier)
    #     if element.text:
    #         text += element.text
    #     return text

    def process_start_ab(self, element):
        """Block."""
        text = ""
        # if not self.past_first_ab:
        #     self.past_first_ab = True
        # else:
        #     text += '</span>'
        try:
            identifier = element.attrib['n']
        except KeyError:
            if FORCE:
                identifier = "000"
            else:
                raise
        if len(identifier) == 0:
            pass
            #then for some reason this doesn't have an identifier so don't add title
            # text += '<span class="ab">'
        else:  #we need to get the number right and display it
            if identifier[-1] == '0' and identifier[-2] == '0':
                identifier = identifier[:-2]
            elif identifier[-1] == '0':
                identifier = '%s.%s' % (identifier[:-2], identifier[-2])
            else:
                identifier = '%s.%s' % (identifier[:-2], identifier[-2:])
            if 'continued' in element.attrib and element.attrib['continued'] == 'true':
                pass
                # text += '<span class="ab" id="%s">' % identifier
            else:
                text += '<sub>%s</sub>&nbsp;' % (identifier)
        if element.text:
            text += element.text
        return text

    def process_end_ab(self, element):
        """End of a block"""
        pass

    def process_start_am(self, element):
        if self.expanded:
            return ''
        if self.choice_open:
            if element.text:
                return '<span class="inner-abbreviation">%s' % element.text.replace('⁊', 'τ')
            return '<span class="inner-abbreviation">'

        self.am_open = True

        if element.text:
            return '<span class="abbreviation_marker hoverover" data-tooltip-content="#amex-%s-%s-%d">%s' % (self.sigla, self.page, self.amex_pos, element.text.replace('⁊', 'τ'))
        else:
            return '<span class="abbreviation_marker hoverover" data-tooltip-content="#amex-%s-%s-%d">' % (self.sigla, self.page, self.amex_pos)

    def process_end_am(self, element):
        if self.expanded:
            return ''
        if self.choice_open:
            if self.abbr_open:
                return '</span>'
            return ''
        self.am_open = False
        return '</span>'

    def process_start_ex(self, element):
        """Expansion - expanded form of abbreviation,
        can be found alone with am and inside choice"""
        if not self.expanded:
            if element.text:
                self.ex_text.append(element.text)
            return ''
        if self.choice_open:
            if element.text:
                return '<span class="inner-expansion">%s' % element.text
            return '<span class="inner-expansion">'

        self.ex_open = True
        if element.text:
            return '<span class="expansion">%s' % element.text
        return '<span class="expansion">'


    def process_end_ex(self, element):
        """End the expansion."""
        if self.choice_open:
            if not self.expanded and self.expan_open:
                return NO_TAIL
            return '</span>'
        self.ex_open = False
        if self.expanded:
            return '</span>'
        else:
            tooltip = '<div class="tooltip_templates"><span class="expansion_details" id="amex-%s-%s-%d">%s expands to %s</span></div>' % (self.sigla, self.page, self.amex_pos, ''.join(self.am_text), ''.join(self.ex_text))
            self.am_text = []
            self.ex_text = []
            self.amex_pos += 1
            return tooltip

    def process_start_abbr(self, element):
        """abbr tag."""
        self.abbr_open = True
        if element.text:
            return '<span class="abbreviation hoverover" title="%s">%s' % (self.choice_hovers[self.choice_pos], element.text.replace('⁊', 'τ'))
        else:
            return '<span class="abbreviation hoverover" title="%s">' % self.choice_hovers[self.choice_pos]
        return ''

    def process_end_abbr(self, element):
        """End abbr tag."""
        self.abbr_open = False
        return '</span>'

    def process_start_expan(self, element):
        """expan tag."""
        self.expan_open = True
        if element.text:
            return '<span class="expansion">%s' % element.text
        return '<span class="expansion">'

    def process_end_expan(self, element):
        """End expan tag."""
        self.expan_open = False
        return '</span>'


    def process_start_g(self, element):
        """G can be a child of AM or EX"""
        if element.text:
            return element.text
        return ''

    def process_end_g(self, element):
        """G can be a child of AM or EX"""
        return ''


    def process_start_gap(self, element):
        """Gap in the manuscript."""
        try:
            length = element.attrib['quantity']
        except KeyError:
            length = 1
        else:
            try:
                length = int(length)
            except ValueError:
                if FORCE:
                    length = 5
                else:
                    raise
        text = '<span class="gap">'
        text += '&nbsp;' * length
        text += '</span>'
        return text

    def process_end_gap(self, element):
        """Gap in the manuscript."""
        pass

    #def process_expan(self, element):
    #    print ("Monkey three")

    def process_start_head(self, element):
        """Heading, which may not necessarily be anywhere near
        the top of the page, used for several different things."""
        if 'n' in element.attrib:
            if element.attrib['n'] in ['Rubric', 'rubric']:
                self.in_rubric = True
                if element.text != None:
                    if self.column_number == 0:
                        self.waiting_for_column.append('<span class="rubric">%s' % element.text)
                        return ''
                    return '<span class="rubric">%s' % element.text
                else:
                    if self.column_number == 0:
                        self.waiting_for_column.append('<span class="rubric">')
                        return ''
                    return '<span class="rubric">'
        if element.text != None:
            return element.text


    def process_end_head(self, element):
        """Heading, which may not necessarily be anywhere near
        the top of the page, used for several different things."""
        self.in_rubric = False
        if 'n' in element.attrib and element.attrib['n'] in ['Rubric', 'rubric']:
            return '</span><br />'
        return ''

    def process_start_hi(self, element):
        """Hi tag."""
        if 'rend' in element.attrib:
            if element.attrib['rend'].startswith('init1'):
                if self.in_rubric:
                    cls = 'rubricinit1'
                else:
                    cls= 'init1'
                if not element.attrib['rend'].endswith('unex') and element.text != None:
                    return '<span class="%s">%s' % (cls, element.text)
                else:
                    return '<span class="%s">&nbsp;' % cls

            elif element.attrib['rend'].startswith('init'):
                #value = int(element.attrib['rend'].split('init')[1])
                #we use the same class for everything even though end might be different

                if self.in_rubric:
                    cls = 'rubricinit'
                else:
                    cls= 'init'

                #if element.text != None:
                if not element.attrib['rend'].endswith('unex') and element.text != None:
                    return '<span class="%s">%s' % (cls, element.text)
                else:
                    return '<span class="%s">&nbsp;&nbsp;&nbsp;' % cls
            else:
                self.in_hi = True
                self.hi_list.append('<span class="%s">' % element.attrib['rend'])
                if element.text != None:
                    return '<span class="%s">%s' % (element.attrib['rend'], element.text)
                else:
                    return '<span class="%s">' % element.attrib['rend']
        if element.text != None:
            return element.text
        else:
            pass

    def process_end_hi(self, element):
        """End hi tag."""
        if self.in_hi is True:
            self.hi_list.pop()
            if len(self.hi_list) == 0:
                self.in_hi = False
        if 'rend' in element.attrib:
            return '</span>'
        else:
            pass


    def process_start_choice(self, element):
        """choice tag."""
        self.choice_open = True
        return '<span class="choice">'


    def process_end_choice(self, element):
        """End choice tag."""
        self.choice_open = False
        self.choice_pos += 1
        return '</span>'


    def process_start_app(self, element):
        self.app_open = True
        return '<span class="app">&nbsp;'

    def process_end_app(self, element):
        self.app_open = False
        self.app_pos += 1
        return '</span>'


    def process_start_rdg(self, element):
        rend_class = ''
        if 'rend' in element.attrib:
            rend_class = '%s ' % element.attrib['rend']

        if 'type' in element.attrib and element.attrib['type'] == 'lit':
            if element.text:
                return '<span class="%srdg_orig hoverover" data-tooltip-content="#rdg-%s-%s-%d">%s' % (rend_class, self.sigla, self.page, self.app_pos, element.text)
            else:
                return '<span class="%srdg_orig hoverover" data-tooltip-content="#rdg-%s-%s-%d">' % (rend_class, self.sigla, self.page, self.app_pos)
        if 'type' in element.attrib and element.attrib['type'] == 'mod':
            if element.text:
                return '<div class="tooltip_templates"><span id="rdg-%s-%s-%d" class="rdg_mod">changed to <span class="%s">%s</span>' % (self.sigla, self.page, self.app_pos, rend_class, element.text)
            else:
                return '<div class="tooltip_templates"><span id="rdg-%s-%s-%d" class="rdg_mod">' % (self.sigla, self.page, self.app_pos)
        return ''

    def process_end_rdg(self, element):
        if 'type' in element.attrib and element.attrib['type'] == 'mod':
            return '</span></div>'
        return '</span>'

    def process_start_seg(self, element):
        cls = ''
        if '{http://www.w3.org/XML/1998/namespace}id' in element.attrib:
            if element.attrib['{http://www.w3.org/XML/1998/namespace}id'].startswith('rubric'):
                cls = ' rubric'
        if element.text:
            return '<span class="seg%s">%s' % (cls, element.text)
        else:
            return '<span class="seg%s">' % cls

    def process_end_seg(self, element):
        if element.tail:
            return '</span>%s' % element.tail
        else:
            return '</span>'

    def process_start_unclear(self, element):
        data = '<span class="hoverover unclear"'
        reason = element.get('reason')
        if reason and not self.app_open:
            data += ' title="text ' + reason + '"'
        data += '>'
        if element.text:
            data += element.text
        return data

    def process_end_unclear(self, element):
        return '</span>'

    def process_start_note(self, element):
        if 'type' in element.attrib and element.attrib['type'] == 'ed':
            pass
        else:
            text = element.text if element.text is not None else ''
            if 'place' in element.attrib:
                return '<span class="note hoverover" data-tooltip-content="#note-%s-%s-%s">☜</span><div class="tooltip_templates"><span id="note-%s-%s-%s">%s: %s' % (self.sigla, self.page, self.note_pos, self.sigla, self.page, self.note_pos, element.attrib['place'], text.replace('"', '\''))
            else:
                return '<span class="note hoverover" data-tooltip-content="#note-%s-%s-%s">☜</span><div class="tooltip_templates"><span id="note-%s-%s-%s">%s' % (self.sigla, self.page, self.note_pos, self.sigla, self.page, self.note_pos, text.replace('"', '\''))

    def process_end_note(self, element):
        if 'type' in element.attrib and element.attrib['type'] == 'ed':
            pass
        else:
            self.note_pos += 1
            return '</span></div>'

    def process_start_figDesc(self, element):
        return '<span class="note hoverover" title="%s">☜</span>' % (element.text)

    def process_end_figDesc(self, element):
        pass

    def process_start_space(self, element):
        if 'unit' not in element.attrib or element.attrib['unit'] in ['char', 'chars']:
            try:
                length = int(element.attrib['quantity'])
            except:
                length = 1
            text = ''
            text = '<span class="space">'
            text += '&nbsp;' * length
            text += '</span>'
            return text
        elif element.attrib['unit'] in ['line', 'lines']:
            try:
                length = int(element.attrib['quantity'])
            except:
                length = 1
            #it gets a bit out of hand it if it is a lot of lines so reduce
            if length > 10:
                length = 10
            text = ''
            text += '<br />' * length
            return text
        else:
            pass


    def process_end_space(self, element):
        pass

    def process_start_fw(self, element):
        place = ''
        column_close = ''
        # first escape the column if this is in the bottom margin
        if 'place' in element.attrib:
            place = ' ' + element.attrib['place']
            if place[1] == 'b':
                if self.subcolumn:
                    column_close = '</div></div></div></div><br class="clear"/>'
                    self.subcolumn = False
                    self.in_main_column = False
                else:
                    column_close = '</div></div><br class="clear"/>'
                    self.in_main_column = False

        if 'type' in element.attrib and element.attrib['type'] == 'header':
            if element.text != None:
                return '%s<span title="header" class="hoverover header%s">%s' % (column_close, place, element.text)
            else:
                return '%s<span title="header" class="hoverover header%s">' % (column_close, place)

        if 'type' in element.attrib and element.attrib['type'] == 'pageNum':
            if element.text != None:
                return '%s<span title="page number" class="hoverover pageNum%s">%s' % (column_close, place, element.text)
            else:
                return '%s<span title="page number" class="hoverover pageNum%s">' % (column_close, place)

        if 'type' in element.attrib and element.attrib['type'] == 'catch':
            if element.text != None:
                return '%s<span title="catch word" class="hoverover catch%s">%s' % (column_close, place, element.text)
            else:
                return '%s<span title="catch word" class="hoverover catch%s">' % (column_close, place)

        if element.text != None:
            '<span class="%s">%s' % (place, element.text)
        else:
            return '<span class="%s">' % place

    def process_end_fw(self, element):
        if 'place' in element.attrib and element.attrib['place'] == 'tm':
            return '</span><br class="clear"/>'
        if 'type' in element.attrib and element.attrib['type'] == 'catch':
            return '</span>'
        return '</span>'



def main(argv):
    """Run when module called."""

    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--data_path',
                        help='the path to the data directory'
                             '(only used by the django app, use default for '
                             'webpack build)')

    args = parser.parse_args()

    # run once for abbreviated
    if args.data_path:
        gen = DisplayTextGenerator(debug=False,
                                   expanded=False,
                                   data_path=args.data_path)
    else:
        gen = DisplayTextGenerator(debug=False, expanded=False)
    gen.generate_all_pages()

    #and again for expanded
    if args.data_path:
        gen = DisplayTextGenerator(debug=False,
                                   expanded=True,
                                   data_path=args.data_path)
    else:
        gen = DisplayTextGenerator(debug=False, expanded=True)
    gen.generate_all_pages()

if __name__ == '__main__':
    main(sys.argv[1:])
