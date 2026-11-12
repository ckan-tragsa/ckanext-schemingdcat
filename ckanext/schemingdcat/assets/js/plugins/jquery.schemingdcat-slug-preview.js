/* Creates a new preview element for a slug field that displays an example of
 * what the slug will look like. Also provides an edit button to toggle back
 * to the original form element. If a slug preview already exists in the parent
 * container, a new one will not be created.
 *
 * options - An object of plugin options (defaults to slugPreview.defaults).
 *           prefix: An optional prefix to apply before the slug field.
 *           placeholder: Optional placeholder when there is no slug.
 *           i18n: Provide alternative translations for the plugin string.
 *           template: Provide alternative markup for the plugin.
 *
 * Examples
 *
 *   var previews = jQuery('[name=slug]').slugPreview({
 *     prefix: 'example.com/resource/',
 *     placeholder: '<id>',
 *     i18n: {edit: 'éditer'}
 *   });
 *   // previews === preview objects.
 *   // previews.end() === [name=slug] objects.
 *
 * Returns the newly created collection of preview elements, or the existing
 * ones if they already exist.
 */
(function ($, window) {
    var escape = $.url.escape;

    function slugPreview(options) {
        options = $.extend(true, slugPreview.defaults, options || {});

        var collected = this.map(function () {
            var element = $(this);
            var field = element.find('input');
            var preview = $(options.template);
            var value = preview.find('.slug-preview-value');
            var required = $('<div>').append($('.control-required', element).clone()).html();

            // Check if slugPreview already exists in the parent container
            if (element.parent().find('.slug-preview').length > 0) {
                return;
            }

            function setValue() {
                var val = escape(field.val()) || options.placeholder;
                value.text(val);
            }

            preview.find('strong').html(required + ' ' + options.i18n['URL'] + ':');
            preview.find('.slug-preview-prefix').text(options.prefix);
            preview.find('button').text(options.i18n['Edit']).click(function (event) {
                event.preventDefault();
                element.show();
                preview.hide();
            });

            setValue();
            field.on('change', setValue);

            element.after(preview).hide();

            return preview[0];
        });

        // Append the new elements to the current jQuery stack so that the caller
        // can modify the elements. Then restore the originals by calling .end().
        return this.pushStack(collected);
    }

    slugPreview.defaults = {
        prefix: '',
        placeholder: '',
        i18n: {
            'URL': 'URL',
            'Edit': 'Edit'
        },
        template: [
            '<div class="slug-preview">',
            '<strong></strong>',
            '<span class="slug-preview-prefix"></span><span class="slug-preview-value"></span>',
            '<button class="btn btn-default btn-xs"></button>',
            '</div>'
        ].join('\n')
    };

    $.fn.slugPreview = slugPreview;

})(this.jQuery, this);