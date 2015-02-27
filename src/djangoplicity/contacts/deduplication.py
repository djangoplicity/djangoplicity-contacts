# -*- coding: utf-8 -*-
#
# djangoplicity-contacts
# Copyright (c) 2007-2011, European Southern Observatory (ESO)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#
#    * Neither the name of the European Southern Observatory nor the names
#      of its contributors may be used to endorse or promote products derived
#      from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY ESO ``AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
# EVENT SHALL ESO BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
# IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE
#

"""
Module to help find contact duplicates.

Usage::
	find_duplicates( data, search_space )

``data'' is a dictionary with the following keys:
	* ``name'' - full name including civil titles like Dr., Mr., Ms. etc.
	* ``address_lines'' - a list of address lines, e.g. ['organisation','department','street 1', 'street 2']
	* ``city'' - zip/post code, city and county in one line.
	* ``country'' - country iso code (upper case)

``search_space'' is a list of dictionaries like data. The dictionary can be created from
contacts_search_space for all contacts in the contact database.




"""
import difflib
import re

#
# Variables defining tokens/characters for splitting a name in title and name.
#
TITLES = ['acad', 'brother', 'dr', 'mr', 'mrs', 'ms', 'miss', 'prof', 'sir', 'rev', 'master', 'fr', 'ing',
		'herr', 'frau', 'dir', 'habil', 'med', 'phil', 'fil', 'herrn', 'hr', 'mag', 'mme', 'sheikh', 'sig',
		'sr', 'univ', ]

WHITESPACE = [" ", "\n", "\r", "\t", ""]

PUNCTUATION = [".", "-"]

ORG_INDICATORS = [
u'earth',
u'institut',
u'deutsche',
u'zentrum',
u'systems',
u'observat',
u'astronom',
u'dept.',
u'vereniging',
u'max-planck',
u'livraria',
u'national',
u'bibliothek',
u'canada',
u'librarian',
u'nachrichten',
u'gmbh',
u'library',
u'univers',
u'schott ag',
u'b.v.',
u'museum',
u'gymnasi',
u'opservatorija',
u'sternwarte',
u'e.v.',
u'space',
u'planetar',
u'laborato',
u'radio',
u'telescope',
u'politiken',
u'post',
u'aftenposten',
u'arbeitsgemeinschaft',
u'academy',
u'science',
u'accademia',
u'administrative',
u'akademi',
u'college',
u'asociacion',
u'assoc.',
u'mediothek',
u'astro',
u'sterrenwacht',
u'student',
u'aarhus',
u'publishing',
u'm.i.t.',
u'csiro',
u'lip',
u'esac',
#u'société',
u'physique',
u'associazione',
u'inst.',
u'dipartimento',
u'campus',
u'periodicals',
u'museo',
u'cern',
u'physik',
u'department',
u'bibliot',
u'sterrenkunde',
u'cultur',
u'optical',
u'organisa',
u'organiza',
u'nwo',
u'zeitung',
u'tidende',
u'bundes',
u'bureau',
u'c n r s',
u'c.e.r.g.a.',
u'zeiss',
u'centre',
u'e m b l',
u'esrin-sds',
u'ecmwf',
u'europ',
u'schule',
u'g e p',
u'fakultet',
u'gesellschaft',
u'kostskole',
u'ugeblad',
u'centro',
u'istituto',
u'redaktion',
u'ministero',
u'ministry',
u'die welt',
u'research',
u'center',
u'nasa',
u'foundation',
u'photometrie',
u'optique',
u'physics',
u'world',
u'warszawska',
u'recherches',
u'royal',
u'society',
u'agentur',
u'harvard-smithsonian',
u'vaticana',
u'state',
u'sterrewacht',
u'instituut',
u'research',
u'council',
u'dagbladet',
u't.a.r.o.t.',
u'fysikers förening',
u'american',
u'association',
u'training',
u'career',
u'uai/yb',
u'serials',
u'records',
u'nick kylafis',
u'uniwersytet',
u'vereinigung',
u'sterrewacht',
u'anzeiger',
u'e.p.bus',
u'station',
u'section',
u'inaf',
u'natuur',
u'centre',
u'nazionale',
u'ricerche',
u'fiube',
u'esoc',
u'jet joint undertaking',
u'lehrstuhl',
u'vermittlungsstelle',
u'technical',
u'services',
u'istituto',
u'forskning',
u'press',
u'inc.',
u'ricerca',
u'scientifica',
u'cnpq/lna',
u'arbeitskreis',
u'sternfreunde',
u'argentina',
u'polytech',
u'scientific',
u'inpe',
u'scienze',
u'missouri',
u'framtidsmuseet',
u'redaktsija',
u'die sterne',
u'magazine',
u'sterrenkundig',
u'departamento',
u'wilhelms-univ.',
u'fysikafdelingen',
u'grupo nordico',
u'vs-rug',
u'comu-caam',
u'standard',
u'stazione',
u'osservativa',
u'missions',
]

splitter = re.compile(r"(\s+|\.|\-)")


#
# Functions
#

def contacts_search_space():
	"""
	Create a search space from all contacts in the database.
	"""
	from djangoplicity.contacts.models import Contact

	search_space = {}
	for c in Contact.objects.all().select_related( 'country' ):
		#search_space.append( c.get_data() )
		search_space[c.id] = c.get_data()

	return search_space

num_pattern = re.compile("([0-9]+|road)")


def is_street( name ):
	"""
	Determine is a text looks like a street name
	"""
	return True if num_pattern.search( name.lower() ) else False


def is_organisation( name ):
	"""
	Determine if name is an organisation name.
	"""
	name = name.lower()

	for indicator in ORG_INDICATORS:
		if indicator in name:
			return True


def split_addresslines( lines ):
	"""
	Split up to 4 lines into appropiate fields (org, dept, street 1/2)
	"""
	data = {
		'organisation': '',
		'department': '',
		'street_1': '',
		'street_2': '',
	}

	if len(lines) == 0:
		pass
	elif len(lines) == 1:
		data['street_1'] = lines[0]
	elif len(lines) == 2:
		if is_street( lines[0] ):
			data['street_1'] = lines[0]
			data['street_2'] = lines[1]
		elif is_street( lines[1] ):
			data['organisation'] = lines[0]
			data['street_1'] = lines[1]
		else:
			data['organisation'] = lines[0]
			data['department'] = lines[1]
	elif len(lines) == 3:
		if is_street( lines[1] ):
			data['organisation'] = lines[0]
			data['street_1'] = lines[1]
			data['street_2'] = lines[2]
		else:
			data['organisation'] = lines[0]
			data['department'] = lines[1]
			data['street_1'] = lines[2]
	else:
		data['organisation'] = lines[0]
		data['department'] = lines[1]
		data['street_1'] = lines[2]
		data['street_2'] = lines[3]

	return data


def split_name( name ):
	"""
	Split a name into civil titles and the name
	"""
	parts = splitter.split( name )

	i = 0
	for p in parts:
		tmp = p.lower()
		if tmp in TITLES or tmp in WHITESPACE or tmp in PUNCTUATION:
			i += 1
			continue
		else:
			break

	return ( "".join( parts[:i] ).strip(), "".join( parts[i:] ).strip() )


def _preprocess_name( name ):
	"""
	Preprocess a name before string comparision
	"""
	# Remove titles
	dummy_title, name = split_name( name )
	return name.lower()


def _preprocess_city( city, isocode ):
	if type(city) is not unicode:
		# If we only have number (e.g. zip)
		# then it will be exported as int and
		# strip() will fail
		city = unicode(city)
	# FIXME:
	return city
	if isocode and city.strip().lower().startswith( isocode.lower() ):
		return city[len(isocode):]
	else:
		return city


def _prepare_str(s):
	'''
	Strip whitespaces chars and remove duplicates from string
	'''
	try:
		s = s.strip().lower()
	except AttributeError:
		# The function was probably passed an int so we try and
		# convert it to a string:
		if not isinstance(s, basestring):
			return _prepare_str(unicode(s))
	return re.sub(r'\s+', ' ', s)


#def similar_name( a, b, ratio_limit=0.90 ):
#	"""
#	Determine if two names are similar. Note, two
#	empty names are not similar.
#	"""
#	a = _preprocess_name( a )
#	b = _preprocess_name( b )
#
#	seq = difflib.SequenceMatcher( a=a.lower(), b=b.lower() )
#	return seq.ratio() > ratio_limit

def similar_text( a, b, ratio_limit=0.90 ):
	"""
	Determine if two names are similar. Note, two
	empty names are not similar.
	"""
	seq = difflib.SequenceMatcher( a=a.lower(), b=b.lower() )
	return seq.ratio() > ratio_limit

#def similar( a, b ):
#	"""
#	Compare two objects to determine if they are similar.
#
#	Algorithm:
#	- Exclude contacts where country and name doesn't match.
#	- Introduce large penalty if one name is blank and the other not.
#	- Introduce penalty if city doesn't match
#	- Introduce small penalty if an address line does not match.
#
#	Note the comparison is not symmetrical - i.e A can be similar to B,
#	but B not similar to A
#
#	Function returns a ratio between 0.0 and 1.0, where 1.0 means a nearly
#	perfect match.
#	"""
#	c = 0
#	t = 0
#	# Country
#	if a['country'] and a['country'].strip() != "":
#		if a['country'] != b['country']:
#			return 0.0
#		c += 1
#		t += 1
#
#	# Name
#	if a['name'].strip() != "":
#		if not similar_name( a['name'], b['name'] ):
#			return 0.0
#		c += 1
#		t += 1
#	elif b['name'].strip() != "":
#		# A empty, b not, so introduce large penalty.
#		c -= 2
#
#	# City
#	if a['city'].strip() != "":
#		t += 1
#		if not similar_text( _preprocess_city( a['city'], a['country'] ), _preprocess_city( b['city'], b['country'] ), ratio_limit=0.85 ):
#			c -= 1 # Penalty if city does not match
#		else:
#			c += 1
#
#	# Address lines
#	if len( a['address_lines'] ) > 0:
#		for l in a['address_lines']:
#			t += 1
#			for l2 in b['address_lines']:
#				if similar_text( l, l2, ratio_limit=0.8 ):
#					c += 1
#					break
#
#	return float(c)/float(t)


#def find_duplicates( obj, search_space, ratio_limit=0.3 ):
#	"""
#	Return a list of possible duplicates of obj in the search space
#	"""
#	dups = []
#
#	for s in search_space:
#		ratio = similar( obj, s )
#		if ratio > ratio_limit:
#			dups.append( (ratio,s) )
#
#	dups.sort( key=lambda x: x[0] )
#	dups.reverse()
#	#dups = [x[1] for x in dups]
#	return dups
#
def similar_name(a, b, ratio_limit=0.8):
	"""
	Compare first name and last name, returns 0.8 if both match,
	0.5 if only last name, 0.1 if only first name
	"""
	a_first = _prepare_str(a['first_name']) if 'first_name' in a else ''
	b_first = _prepare_str(b['first_name']) if 'first_name' in b else ''
	a_last = _prepare_str(a['last_name']) if 'last_name' in a else ''
	b_last = _prepare_str(b['last_name']) if 'last_name' in b else ''

	# Compare first and last name if we have all the information
	if a_first and b_first and a_last and a_last:
		seq = difflib.SequenceMatcher(None,
				a_first + a_last, b_first + b_last)
		if seq.ratio() >= ratio_limit:
			return 0.8 * seq.ratio()

		# Look for first name initials (e.g.: "S.":
		if len(a_first) == 2 and a_first[1] == '.' and a_first[0] == b_first[0]:
			b_first = b_first[0] + '.'
			seq = difflib.SequenceMatcher(None,
					a_first + a_last, b_first + b_last)
			if seq.ratio() >= ratio_limit:
				return 0.75 * seq.ratio()

	# Compare last names
	if a_last and b_last:
		seq = difflib.SequenceMatcher(None, a_last, b_last)
		if seq.ratio() > ratio_limit:
			return 0.4 * seq.ratio()

	# Compare first names
	if a_first and b_first:
		seq = difflib.SequenceMatcher(None, a_first, b_first)
		if seq.ratio() > ratio_limit:
			return 0.1 * seq.ratio()

	return 0


def similar_address(a, b, no_name, ratio_limit=0.8):
	'''
	Compare two addresses
	'''
	address_a = ''
	address_b = ''
	if 'street_1' in a:
		address_a += a['street_1']
		if 'street_1' in b:
			address_b += b['street_1']
	if 'street_2' in a:
		address_a += a['street_2']
		if 'street_2' in b:
			address_b += b['street_2']

	address_a = _prepare_str(address_a)
	address_b = _prepare_str(address_b)

	if address_a and address_b:
		seq = difflib.SequenceMatcher(None, address_a, address_b)
		if seq.ratio() > ratio_limit:
			if no_name:
				return 0.4 * seq.ratio()
			else:
				return 0.2 * seq.ratio()

	return 0


def similar(a, b):
	# Compares two contacts' dictonaries and return a value
	# The higher the value the more similar the contacts

	# Name
	r = similar_name(a, b)

	# Email, compares basic email fields as well as potential
	# optional fields defined as Field
	emails = ['email', 'second_email', 'third_email']
	for email_a in emails:
		if not email_a in a or a[email_a].strip() == '':
			continue
		for email_b in emails or b[email_b].strip() == '':
			if not email_b in b:
				continue
			if similar_text(a[email_a], b[email_b],
							ratio_limit=0.95):
				r += 0.8

	# If we have neither first_name nor last_name we change the
	# algorithm to increase the weight of similar addresses as this
	# helps detecting duplicate organisation
	no_name = True
	for field in ('first_name', 'last_name'):
		for contact in (a, b):
			if field in contact and contact[field]:
				no_name = False

	# Two people with same address (e.g.: same institute) will always
	# be matched as duplicates, so if neither the name or email have
	# at least some similarities we don't compare the addresses, unless
	# we don't have a first_name or last_name (in which case the contact
	# is probably an institute or organisation):
	if not no_name and r < 0.15:
		return r

	# Country
	try:
		if a['country'] and b['country'] and \
				a['country'] == b['country']:
			if no_name:
				r += 0.2
			else:
				r += 0.1
	except KeyError:
		pass

	# City
	try:
		if a['city'] and b['city'] and \
				similar_text(_preprocess_city(a['city'], a['country']),
						_preprocess_city( b['city'], b['country'] ), ratio_limit=0.85):
			if no_name:
				r += 0.2
			else:
				r += 0.1
	except KeyError:
		pass

	# Organisation
	try:
		if a['organisation'] and b['organisation']:
			organisation_a = _prepare_str(a['organisation'])
			organisation_b = _prepare_str(b['organisation'])
			if similar_text(organisation_a, organisation_b):
				if no_name:
					r += 0.4
				else:
					r += 0.2
	except KeyError:
		pass

	# Department
	try:
		if a['department'] and b['department']:
			department_a = _prepare_str(a['department'])
			department_b = _prepare_str(b['department'])
			if similar_text(department_a, department_b):
				r += 0.2
	except KeyError:
		pass

	# Address
	r += similar_address(a, b, no_name)

	return r


def find_duplicates( obj, search_space, ratio_limit=0.75 ):
	"""
	Return a list of possible duplicates of obj in the search space
	"""
	dups = []

	for s in search_space.values():
		ratio = similar( obj, s )
		ratio = round(ratio, 2)
		if ratio > ratio_limit:
			dups.append( (ratio, s) )

	dups.sort( key=lambda x: x[0] )
	dups.reverse()
	return dups
