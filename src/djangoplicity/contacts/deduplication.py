
import difflib
import re

TITLES = ['acad', 'brother', 'dr', 'mr', 'mrs', 'ms', 'miss', 'prof', 'sir', 'rev', 'master', 'fr', 'ing', 
		'herr', 'frau', 'dir', 'habil', 'med', 'phil', 'fil', 'herrn', 'hr', 'mag', 'mme', 'sheikh', 'sig', 
		'sr', 'univ', ]
WHITESPACE = [" ", "\n", "\r", "\t", ""]
PUNCTUATION = [".", "-"]



import re
splitter = re.compile("(\s+|\.|\-)")

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
	title, name = split_name( name )
	return name.lower() 
	
def name_similar( a, b, ratio_limit=0.90 ):
	"""
	Determine if two names are similar. Note, two
	empty names are not similar.
	"""
	a = _preprocess_name( a )
	b = _preprocess_name( b )
	
	seq = difflib.SequenceMatcher( a=a.lower(), b=b.lower() )
	return seq.ratio() > ratio_limit



def similar( a, b ):
	"""
	Compare two objects to determine if they are similar.
	
	Algorithm:
	- Exclude objects until there's a high chance the two objects are similar
	"""
	# Country
	if a['country'] != b['country']:
		return False
	
	# Name
	if a['name'].strip() != "" and b["name"].strip() != "":
		if not name_similar( a['name'], b['name'] ):
			return False
	
	# Check city and street
	
	return True
		
	


def duplicates( obj, search_space ):
	"""
	Return a list of possible duplicates of obj in the search space
	"""
	dups = []
	
	for s in search_space:
		if similar( obj, s ):
			dups.append( s )

	return dups

