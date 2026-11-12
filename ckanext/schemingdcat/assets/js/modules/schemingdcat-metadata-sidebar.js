/**
 * A CKAN module that provides functionality for opening and closing a sidebar.
 *
 * @module schemingdcat-metadata-sidebar
 * @param {Object} $ - The jQuery object.
 * @param {Object} _ - The underscore object.
 */
(function () {
  this.ckan.module("schemingdcat-metadata-sidebar", function ($, _) {
    return {
        initialize: function () {
            this.el.on('click', this._onClick.bind(this));
            $(document).on('click', this._onDocumentClick.bind(this));
            $('.metadata-sidebar-nav li').on('click', function(event) {
              event.stopPropagation();
            });
          },

        _onClick: function(event) {
        event.stopPropagation();
        var sidebar = document.getElementById('metadata-sidebar');
        var button = document.getElementById('sidebarButton');
        if (sidebar.classList.contains('open')) {
            sidebar.classList.remove('open');
            button.style.opacity = '1'; // Show the button
            button.style.visibility = 'visible';
        } else {
            sidebar.classList.add('open');
            button.style.opacity = '0'; // Hide the button
            button.style.visibility = 'hidden';
        }
        },

      _onDocumentClick: function(event) {
        var sidebar = document.getElementById('metadata-sidebar');
        var button = document.getElementById('sidebarButton');
        var isClickInside = sidebar.contains(event.target);

        if (!isClickInside && sidebar.classList.contains('open')) {
          sidebar.classList.remove('open');
          button.style.opacity = '1'; // Show the button
          button.style.visibility = 'visible';
        }
      }
    };
  });
}).apply(this);