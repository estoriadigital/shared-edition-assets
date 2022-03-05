"use strict";

import './main.css';
const $ = require('jquery');
const ko = require('knockout');

import { GridStack } from 'gridstack';
// HTML5 drag&drop
import 'gridstack/dist/h5/gridstack-dd-native';

const tooltipster = require('tooltipster');

const DATA_PATH = 'data/';
const MANUSCRIPTS_WITH_IMAGES = ["Ss", "T", "Q"];

let WIDGET_I = 0;

var ESTORIA = (function () {
    return {
        get_version: function () {
            return "0.1";
        },

        load_indice: function () {
            var windowheight;
            var filename = DATA_PATH + "indice.json";
            $.ajax({
                url: filename,
                success: function (data) {ESTORIA.do_load_indice(data);},
                dataType: 'json'
            });
            windowheight = $('#page-wrapper').height();
            // $('.sidebar-nav').height(windowheight + 'px');
        },

        do_load_indice: function (data) {
            var key, list, html, ms, i;
            html = [];
            list = document.getElementById('side-menu');
            for (key in data) {
                if (data.hasOwnProperty(key)) {
                    html.push('<li><div class="indice-entry"><span class="divnum">Chapter ' + data[key].div + '</span><span class="PCGchap">[' + data[key].PCG + ']</span><br/><span title="' + data[key].title + '">' + data[key].title.substring(0, 35) + '...</span>');
                    html.push('<br/><select class="form-select form-select-sm ms-select" id="ms-select-' + key + '">');
                    html.push('<option value="none">select</option>');
                    for (i = 0; i < data[key].manuscripts.length; i+=1) {
                        ms = data[key].manuscripts[i];
                        if (data[key].pages.hasOwnProperty(ms)) {
                            html.push('<option value="' + ms + '|' + data[key].pages[ms] + '">' + ms + '</option>');
                        }
                    }
                    html.push('</select><br/></div></li>');
                }
            }
            list.innerHTML = html.join('');
            $('.ms-select').change(function (event) {
                var temp;
                if (event.target.value != 'none') {
                    temp = event.target.value.split('|');
                    new Transcription(temp[0], temp[1]);
                    document.getElementById(event.target.id).value = 'none';
                }
            });
        },

        add_index_toggle: function () {
            $('#index_toggle').click(function () {
                if (document.getElementById('index_sidebar').style.display === 'none') {
                    document.getElementById('index_sidebar').style.display = 'block';
                } else {
                    document.getElementById('index_sidebar').style.display = 'none';
                }
            });
        },

        setup_critical: function () {
          $("span.overtext").mouseover(function() {
            $( "span.variant" ).removeClass('hover');
            $( "span.overtext" ).removeClass('hover');
  	        var ovi_id = $(this)[0].id;
  	        var variant = $( "span.variant#" + ovi_id);
  	        variant.addClass('hover');
            var overtext_place = $( "span.overtext#" + ovi_id);
            if (overtext_place.has('span.critical_marker').length) {
              overtext_place.addClass('hover');
            }
          });

          $("span.variant").mouseover(function() {
	        $( "span.variant" ).removeClass('hover');
          $( "span.overtext" ).removeClass('hover');
	        var ovi_id = $(this)[0].id;
	        var variant = $( "span.variant#" + ovi_id);
	        variant.addClass('hover');
                var overtext_place = $( "span.overtext#" + ovi_id);
                if (overtext_place.has('span.critical_marker').length) {
                    overtext_place.addClass('hover');
                }
            });

            $("span.variant_number").click(function() {
                var variant = $(this).next("span.variant");
                var counter = variant.find("span.base_counter");
                var witness_name = counter.attr("data-base-last-wit");
                var page_name = counter.attr("data-base-page-name");
                new Transcription(witness_name, page_name);
            });

            $("span.witname").click(function() {
                var witness_name = $(this).text();
                var page_name = $(this).attr("data-page-name");
                new Transcription(witness_name, page_name);
            });

            $("span.variant-wit-text").click(function() {
                var witname = $(this).prev("span.witname");
                var witness_name = witname.text();
                var page_name = witname.attr("data-page-name");
                new Transcription(witness_name, page_name);
            });
        },

        add_menu_item: function (key, value) {
            var selly = $("#li-" + key + " select");
            $.each(value, function( index, page ) {
                selly.append('<option value="' + key + '-' + page + '">'
                             + page + '</option>');
            });
        },

        add_reader_menu: function (page) {
            var key = "reader";
            var selly = $("#li-" + key + " select");
            selly.append('<option value="' + key + '-' + page + '">'
                         + page + '</option>');
        },

        add_critical_menu: function (page) {
            var key = "critical";
            var selly = $("#li-" + key + " select");
            selly.append('<option value="' + key + '-' + page + '">'
                         + page + '</option>');
        },

        fill_menu: function () {
            $.each( MENU_DATA, function( key, value ) {
                ESTORIA.add_menu_item(key,value);
                ESTORIA.setup_page_selection(key);
            });
            $.each( READER_PAGES, function( page ) {
                ESTORIA.add_reader_menu(READER_PAGES[page]);
            });
            $.each( CRITICAL_PAGES, function( page ) {
                ESTORIA.add_critical_menu(CRITICAL_PAGES[page]);
            });
            ESTORIA.load_indice();
            ESTORIA.add_index_toggle();
            ESTORIA.setup_reader_selection();
            ESTORIA.setup_critical_selection();
            return "0.1";
        },

        setup_reader_selection: function () {
            $( "#pageselect-reader").change(function() {
                var selectedText = $(this).find("option:selected").text();
                var selectedValue = $(this).val();
                if (selectedValue === null) {
                    return;
                }
                if (selectedValue === "title") {
                    return;
                }
                new Reader(selectedText);
            });
        },

        setup_critical_selection: function () {
            $( "#pageselect-critical").change(function() {
                var selectedText = $(this).find("option:selected").text();
                var selectedValue = $(this).val();
                if (selectedValue === null) {
                    return;
                }
                if (selectedValue === "title") {
                    return;
                }
                new Critical(selectedText);
            });
        },

        setup_page_selection: function (key) {
            $( "#pageselect-" + key ).change(function() {

                var selectedText = $(this).find("option:selected").text();
                var selectedValue = $(this).val();
                if (selectedValue === null) {
                    return;
                }
                if (selectedValue === "title") {
                    return;
                }
                var manuscript = selectedValue.split('-')[0]
                new Transcription(manuscript, selectedText);
            });
        },

        get_widget_by_id: function(id) {
            var widgets = ESTORIA.controller.widgets();
            var widgets_length = widgets.length;
            for (var i = 0; i < widgets_length; i++) {
                if (id == widgets[i].id) {
                    return widgets[i];
                }
            }
        },

        get_Url_Vars: function () {
    	    var vars = [], hash;
            var hashes = window.location.href.slice(window.location.href.indexOf('?') + 1).split('&');
            for(var i = 0; i < hashes.length; i++) {
                hash = hashes[i].split('=');
                vars.push(hash[0]);
                vars[hash[0]] = hash[1];
            }
            return vars;
        },

    	preload_page: function () {
    	    var vars;
    	    if (window.location.href.indexOf('?') !== -1) {
        		vars = ESTORIA.get_Url_Vars();
        		if (vars.hasOwnProperty('ms') && vars.hasOwnProperty('p')) {
                            new Transcription(vars['ms'], vars['p']);
        		} else {
        		    return;
        		}
        	}
    	    return;
    	},

        setup_knockout: function() {

            ko.components.register('dashboard-grid', {
                viewModel: {
                    createViewModel: function (controller, componentInfo) {
                        var ViewModel = function (controller, componentInfo) {
                            var grid = null;
                            this.widgets = controller.widgets;
                            this.afterAddWidget = function (items) {
                                if (!grid) {
                                    grid = GridStack.init({
                                        auto: false,
                                        draggable: {
                                            handle: '.panel-heading'
                                          }
                                        })
                                }
                                var item = items.find(function (i) { return i.nodeType == 1 });
                                grid.addWidget(item, {w: 6, h:5});
                                ko.utils.domNodeDisposal.addDisposeCallback(item, function () {
                                  grid.removeWidget(item);
                                });
                            };
                        };
                        return new ViewModel(controller, componentInfo);
                    }
                },
                template: { element: 'gridstack-template' }
            });

            var widgets = [];
            var controller = new Controller(widgets);
            ko.applyBindings(controller);
            ESTORIA.controller = controller;

        },
    };
}());

class BaseWidget {
    constructor(manuscript, page, page_list, filetype) {
        this.manuscript = manuscript;
        this.page = ko.observable(page);

        if (typeof filetype == "undefined") {
            this.filetype = "html";
        } else {
            this.filetype = filetype;
        }

        this.auto_position = true;
        this.has_image = false;
        this.is_image = false;
        this.has_eye = false;
        this.body = ko.observable("");
        this.previous = ko.observable("");
        this.next = ko.observable("");
        this.filename = ko.observable("");

        this.id = WIDGET_I;
        WIDGET_I += 1;
        this.long_feature_name = this.constructor.name;
        this.update_filename()

        this.page_list = page_list;
        this.set_next_previous()
    }

    update_filename() {
        var filename = DATA_PATH + this.get_feature_name() + "/";
        if (this.manuscript) {
            filename += this.manuscript + '/';
        }
        filename += this.page() + '.' + this.filetype;
        this.filename(filename);
    }

    get_feature_name() {
        return this.constructor.name.toLowerCase();
    }

    set_next_previous() {
        var reader_page = this.page_list.indexOf(this.page());
        this.previous(this.page_list[reader_page - 1]);
        this.next(this.page_list[reader_page + 1]);
    }

    next_page(item, click_event) {
        this.update_page(this.next())
    }
    previous_page() {
        this.update_page(this.previous())
    }
    update_page(target_page) {
        this.page(target_page);
        this.set_next_previous();
        this.update_filename();
        this.update_body(false);
    }

    update_body(first_time) {
    }

    request(success_function) {
        $.ajax({
            url: this.filename(),
            success: success_function,
            dataType: this.filetype
        });
    }
    push() {
        ESTORIA.controller.widgets.push(this)
    }
}

class Critical extends BaseWidget {
    constructor(page) {
        var page_number = parseInt(page);
        if (isNaN(page_number)) {
            page_number = page;
        }
        super("", page_number, CRITICAL_PAGES);
        this.long_feature_name = "Versión primitiva editada";
        this.width = 6;
        this.height = 8;
        this.update_body(true);
    }
    update_body(first_time) {
        self = this
        var success_function = function(body) {
            self.body(body);
            if (first_time) {
                self.push();
            }
            ESTORIA.setup_critical();
        }
        this.request(success_function);
    }
}

class Reader extends BaseWidget {
    constructor(page) {
        super("", page, READER_PAGES);
        this.long_feature_name = "Versión primitiva de lectura";
        this.width = 5;
        this.height = 6;
        this.update_body(true);
    }

    update_body(first_time) {
        self = this
        var success_function = function(body) {
            self.body(body);
            if (first_time) {
                self.push();
            }
        }
        this.request(success_function);
    }
}

class ManuscriptImage extends BaseWidget {
    constructor(manuscript, page) {
        super(manuscript, page, MENU_DATA[manuscript], "jpg");
        this.is_image = true;
        this.width = 5;
        this.height = 9;
        this.push();
    }
}

class Transcription extends BaseWidget {
    constructor(manuscript, page, abbrev) {
        page = page.replace(/^0+/, ''); // Remove any leading zeros
        super(manuscript, page, MENU_DATA[manuscript], "json");
        this.has_eye = true;
        this.width = 6;
        this.height = 7;
        this.abbrev = -1;
        if (MANUSCRIPTS_WITH_IMAGES.indexOf(this.manuscript) != -1) {
            this.has_image = true;
        }
        this.update_body(true);
    }
    update_body(first_time) {
        var self = this;
        var success_function = function(jsondata) {
            if (self.abbrev != -1) {
                self.body(jsondata.html_abbrev);
            } else {
                self.body(jsondata.html);
            }
            if (first_time) {
                self.push();
            }
            $('.hoverover').tooltipster({
                theme: 'tooltipster-light'
            });
        };
        this.request(success_function);
    }
}

class Controller {
    constructor(widgets) {
        this.widgets = ko.observableArray(widgets);
    }

    add_new_widget(data) {
        new Widget(data);
    }

    delete_widget(item) {
        ESTORIA.controller.widgets.remove(item);
    }

    show_image(item) {
        new ManuscriptImage(item.manuscript, item.page());
    }

    hide_abbrev(item, second) {
        var icon, classes, close;
        if ($(second.target).prop('tagName') == 'I') {
            icon = $(second.target).parent().find("i");
        } else {
            icon = $(second.target).find("i");
        }
        icon.toggleClass('fa-eye fa-eye-slash');
        classes = $(icon).attr('class');
        close = classes.indexOf('slash');
        item.abbrev = close;
        item.update_body(false);
    }
}

$(document).ready(function(){
    ESTORIA.fill_menu();
    ESTORIA.setup_knockout();
    ESTORIA.preload_page();
});
