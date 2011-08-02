
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
	Determine if two names are similar.
	"""
	if a and not b or b and not a:
		return False
	a = _preprocess_name( a )
	b = _preprocess_name( b )
	seq = difflib.SequenceMatcher( a=a.lower(), b=b.lower() )
	return seq.ratio() > ratio_limit


