if (typeof $ === 'undefined') {
	var $ = django.jQuery;
}

var response_cache = {};

function fill_regions(country_id) {
	if (response_cache[country_id]) {
		$("#id_regions").html(response_cache[country_id]);
	} else {
		$.getJSON('/public/contacts/countryregions/' + country_id + '/json/',
			function(ret, textStatus) {
				var options = '<option value="" selected="selected">---------</option>';
				for (var i in ret) {
					options += '<option value="' + ret[i].pk + '">'
					+ ret[i].name + '</option>';
				}
				response_cache[country_id] = options;
				$("#id_region").html(options);
			}
		);
	}
}

$(document).ready(function() {
	$("#id_country").change(function() {
		fill_regions($(this).val());
	});
});
