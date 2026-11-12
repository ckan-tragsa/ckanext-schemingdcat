/**
 * This module provides a functionality to collapse rows in a CKAN table.
 * Collapsed rows can be expanded and collapsed by clicking on a link.
 *
 * @module schemingdcat-table-collapsible-rows
 * @requires jQuery
 * @requires Mustache
 * @exports {Object} - An object containing options, templates and functions for initialising and uninitialising the module.
 *
 * @example
 * // Import the module
 * var tableCollapsibleRows = this.ckan.module('schemingdcat-table-collapsible-rows');
 *
 * // Initialise the module
 * tableCollapsibleRows.initialize();
 *
 * // Disassemble the module
 * tableCollapsibleRows.teardown();
 */
(function () {
  var debug = $.proxy(window.console, "debug");
  var warn = $.proxy(window.console, "warn");

  var render = Mustache.render;

  this.ckan.module("schemingdcat-table-collapsible-rows", function ($, _) {
    return {
      options: {
        numcols: null,
        i18n: {
          show: _("Show more"),
          hide: _("Hide"),
        },
      },

      templates: {
        togglerow:
          '<tr class="toggle-show toggle-show-more">' +
          '<td colspan="{{numcols}}"><small>' +
          '<a href="#" class="show-more">{{showText}}</a>' +
          '<a href="#" class="show-less">{{hideText}}</a>' +
          "</small></td>" +
          "</tr>",
        separator:
          '<tr class="toggle-separator"><td colspan="{{numcols}}"></td></tr>',
      },

      initialize: function () {
        var module = this,
          $el = this.el,
          opts = this.options,
          templates = this.templates;

        var numcols = parseInt(opts.numcols || $el.find("colgroup col").length),
          $separator = $(
            render(templates.separator, {
              numcols: numcols,
            })
          ),
          $togglerow = $(
            render(templates.togglerow, {
              numcols: numcols,
              showText: this.i18n("show"),
              hideText: this.i18n("hide"),
            })
          );

        $el.addClass("table-toggle-more");

        var $rowsWithToggleNot = $el.find("tbody > tr.toggle-not");
        var $rowsWithoutToggleNot = $el.find("tbody > tr:not(.toggle-not)");
        var $lastRow = $rowsWithoutToggleNot.last();

        $rowsWithToggleNot.insertBefore($rowsWithoutToggleNot.first());
        $separator.insertAfter($lastRow);
        $togglerow.insertAfter($separator);

        $togglerow.find("a.show-more").on("click", function (ev) {
          $el.addClass("table-toggle-less");
          $el.removeClass("table-toggle-more");
          return false;
        });

        $togglerow.find("a.show-less").on("click", function (ev) {
          $el.addClass("table-toggle-more");
          $el.removeClass("table-toggle-less");
          return false;
        });

        //debug('Initialized module: schemingdcat-table-collapsible-rows, opts=', opts);
      },
    };
  });
}).apply(this);
