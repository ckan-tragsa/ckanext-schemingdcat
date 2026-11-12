$(document).ready(function() {
    // Get the csrf value from the page meta tag
    var csrf_value = $('meta[name=_csrf_token]').attr('content');
    // Create the hidden input
    var hidden_csrf_input = $('<input name="_csrf_token" type="hidden" value="' + csrf_value + '">');

    // Append CSRF token to all forms
    $('form').each(function() {
        hidden_csrf_input.clone().prependTo($(this));
    });

    // Initialize the first tab and pane as active
    $("#groupTab .nav-pills li:first").addClass("active");
    $("#groupTab .nav-pills li:first .nav-link").addClass("active");
    $("#groupTab .tab-pane:first").addClass("active show");

    // Show the form group list of the first tab
    $("#groupTab .nav-pills li:first .form-group-list").show();

    // Move forward
    $("#next-tab").on('click', function(e) {
        e.preventDefault();
        var $activeTab = $('.tabs_container .nav-item .nav-link.active').closest('.nav-item');
        var $nextTab = $activeTab.next('.nav-item');

        if ($nextTab.length > 0) {
            $activeTab.find('.nav-link').removeClass('active');
            $nextTab.find('.nav-link').addClass('active');
            $nextTab.find('a.nav-link').tab('show'); // Use .tab('show') to activate the next tab

            // Hide all form group lists and show the one for the next tab
            $('.form-group-list').hide();
            $nextTab.find('.form-group-list').show();

            // Scroll to the corresponding content
            var targetTabId = $nextTab.find('a.nav-link').attr('href');
            $('html, body').animate({
                scrollTop: $(targetTabId).offset().top
            }, 700, function() {
                // Update the active tab pane after scroll animation completes
                $('.tab-pane').removeClass('active show');
                $(targetTabId).addClass('active show');
            });
        }

        // Check if the next tab is the last tab
        if ($nextTab.is(':last-child')) {
            $('#next-tab').hide();
        }

        return false;
    });

    // Show/hide form group list on tab click
    $(".tab-link").on('click', function(e) {
        e.preventDefault();
        var $formGroupList = $(this).siblings(".form-group-list");
        $(".form-group-list").not($formGroupList).slideUp();
        $formGroupList.slideToggle();

        // Scroll to the tab
        var targetTabId = $(this).attr('href');
        $('html, body').animate({
            scrollTop: $(targetTabId).offset().top
        }, 800, function() {
            // Update the active tab pane after scroll animation completes
            $('.tab-pane').removeClass('active show');
            $(targetTabId).addClass('active show');
        });

        // Show the next button if not on the last tab
        var $clickedTab = $(this).parent('li');
        if (!$clickedTab.is(':last-child')) {
            $('#next-tab').show();
        }
    });

    // Remove duplicate form groups
    var seenFormGroups = new Set();
    $("#groupTab .tab-pane .card").each(function() {
        var formGroupId = $(this).data("bs-form_group_id");
        if (seenFormGroups.has(formGroupId)) {
            $(this).remove();
        } else {
            seenFormGroups.add(formGroupId);
        }
    });

    // Handle secondary links click
    $(".secondary-link").on('click', function(e) {
        e.preventDefault();
        var targetId = $(this).attr('href');
        var $targetTab = $(targetId).closest('.tab-pane');
        var targetTabId = $targetTab.attr('id');
        
        // Activate the corresponding tab
        $('a[href="#' + targetTabId + '"]').tab('show');
        
        // Scroll to the form group
        $('html, body').animate({
            scrollTop: $(targetId).offset().top
        }, 700, function() {
            // Update the active tab pane after scroll animation completes
            $('.tab-pane').removeClass('active show');
            $(targetTabId).addClass('active show');
        });

        // Show the next button if not on the last tab
        var $clickedTab = $('a[href="#' + targetTabId + '"]').parent('li');
        if (!$clickedTab.is(':last-child')) {
            $('#next-tab').show();
        }
    });
});