Shared Edition Assets
----

This repository contains the css, JavaScript, fonts and data pocessing scripts that are used by both the Estoria-de-Espanna-Digital repository and the cpsf-digital repository. This repository is included as a submodule in both of these repositories to prevent duplication of this code.

CSS and JavaScript
----

* main.css contains all of the external dependencies used in the webpack build.
* estoria.css contains the css written for the editions.
* main.js contains all of the JavaScript written for the editions and imports any required.

Fonts
----

Junicode is included as the font for the edition.

Scripts
----

The scripts need to be run with Python3 and require lxml.
Each script can be run with -h or --help to see what arguments it can take.

More detailed documentation can be found at the top of each script.


### make_paginated_json.py

This script is the first stage for ingesting the XML transcriptions. It splits
the XML into pages and stores a json object for each page in a file in the
data/transcription directory (further subdivided by Manuscript)
with the page number used as the name of the file.


### add_html_to_paginated_json.py

This script uses the paginated json created by make_paginated_json.py and
adds two html strings created from the XML already stored in the json.

* html - the version of the html which expands the abbreviations
* html_abbrev - the version of the html which displayes the abbreviated forms

The script finds all the pages and generates the html required for each one.

### make_chapter_index_json.py

This script is used to create the chapter index (indice in Spanish) that
appears on the right hand side of the edition home page.

The chapter index data is provided in a csv file (spreadsheet) in the main edition repositories.

### make_reader.py

This script makes the readers edition which is stored as html files by chapter
in the data/reader directory.

At the same time this file creates the index data used for the VPL dropdown
which is saved at data/reader_pages.js

### make_critical_chapter_verse_json.py

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

### make_verse_page_index.py

This needs to be run in the preparation forgenrating any new critical text pages.
It establishes the page numbers used for the links from the critical apparatus
to the trancriptions.These links become 'baked' into the critical edition html
as the critical text is constructed.

### make_translation.py

CPSF only.

This script makes the translated chapter which is stored as html file
in the data/translation directory.

At the same time this file creates the index data used for the translation dropdown
which is saved at data/translation_pages.js

### make_cpsf_critical.py

CPSF only.

This script makes the critical text for the CPSF edition which is stored as html file
in the data/cpsfcritical directory.

Note this text is different from the edited text which is known as 'collation'
in the cpsf edition.

At the same time this file creates the index data used for the critical dropdown
which is saved at data/cpsf_critical_pages.js
