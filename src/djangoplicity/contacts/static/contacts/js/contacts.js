if (typeof $ === 'undefined') {
	var $ = django.jQuery;
}

function fill_regions(country_id) {
    $.getJSON('/public/contacts/countryregions/' + country_id + '/json/',
        function(ret, textStatus) {
            let selected = $('#id_region').val();
            var options = '<option value="" selected="selected">---------</option>';
            for (var i in ret) {
                options += '<option value="' + ret[i].pk + '"';
                if (selected == ret[i].pk) {
                    options += ' selected="selected"';
                }
                options += '>' + ret[i].name + '</option>';
            }
            $('#id_region').html(options);
        }
    );
}

$(document).ready(function() {
    // Set initial regions
    let country = $('#id_country');
    fill_regions(country.val());

	$('#id_country').change(function() {
		fill_regions($(this).val());
	});
});
