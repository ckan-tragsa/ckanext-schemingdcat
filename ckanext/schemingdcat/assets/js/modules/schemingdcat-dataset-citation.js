// Define a closure for external links functionality, but only if it hasn't been defined
window.record_citations =
  window.record_citations ||
  (function () {
    var self = {};

    /**
     * Find the elements we need and bind hover listeners to them.
     */
    self.bind = function () {
      self.element = $(document).find('#citation-status');
      self.info = $(document).find('#citation-info-popup');
      self.info.hide();
      self.element.hover(self.enter, self.exit);

      // Bind click event to copy citation to clipboard
      $(document).on('click', '.citation-string', self.copyToClipboard);
    };

    self.enter = function () {
      var elementPosition = self.element.position();
      // make sure the info box is positioned next to the info icon
      self.info.css({
        top: elementPosition.top,
        left: elementPosition.left + self.element.width() + 15,
      });
      self.info.show();
    };

    self.exit = function () {
      self.info.hide();
    };

    self.copyToClipboard = function () {
      var citationText = $(this).get(0).innerText;

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(citationText)
          .then(() => {
            // Show the clipboard icon and change its color temporarily
            var clipboardIcon = $('#clipboard-icon');
            clipboardIcon.fadeIn(200).delay(1000).fadeOut(200);
          })
          .catch(err => {
            console.error('Error copying text: ', err);
          });
      } else {
        // Fallback for browsers that do not support navigator.clipboard
        var tempInput = $('<textarea>');
        $('body').append(tempInput);
        tempInput.val(citationText).select();
        document.execCommand('copy');
        tempInput.remove();

        // Show the clipboard icon and change its color temporarily
        var clipboardIcon = $('#clipboard-icon');
        clipboardIcon.fadeIn(200).delay(1000).fadeOut(200);
      }
    };

    return self;
  })();

// Bind up as soon as the document is ready for it
$(document).ready(function () {
  window.record_citations.bind();
});