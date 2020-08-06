# -*- coding: utf-8 -*-
#
# djangoplicity-contacts
# Copyright (c) 2007-2011, European Southern Observatory (ESO)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#
#   * Redistributions in binary form must reproduce the above copyright
#     notice, this list of conditions and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#
#   * Neither the name of the European Southern Observatory nor the names
#     of its contributors may be used to endorse or promote products derived
#     from this software without specific prior written permission.
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

import json


def serialize_contact( c, out ):
    """
    Write serialization of object to output stream
    """
    d = {
        'pk': c.pk,
        'first_name': c.first_name.encode('utf-8'),
        'last_name': c.last_name.encode('utf-8'),
        'title': c.title.encode('utf-8'),
        'organisation': c.organisation.encode('utf-8'),
        'department': c.department.encode('utf-8'),
        'street_1': c.street_1.encode('utf-8'),
        'street_2': c.street_2.encode('utf-8'),
        'city': c.city.encode('utf-8'),
        'country': c.country.iso_code,
    }
    if out:
        json.dump( d, out)


def print_sideby( a, b ):
    l_a = len(a['address_lines'])
    l_b = len(b['address_lines'])
    l = max(l_a, l_b)

    if l_a != l:
        a['address_lines'] += [''] * (l - l_a)
    if l_b != l:
        b['address_lines'] += [''] * (l - l_b)

    a_lines = [a['name']] + a['address_lines'] + [a['city'], a['country']]
    b_lines = [b['name']] + b['address_lines'] + [b['city'], b['country']]

    linelen = max([len(x) for x in a_lines + b_lines]) + 1

    lines = []
    for i in range(len(a_lines)):
        lina = a_lines[i]
        linb = b_lines[i]
        lina += " " * (linelen - len(lina))
        linb += " " * (linelen - len(linb))
        lines.append( "%s %s" % (lina, linb))
    return "\n".join( lines )


def joinfields( *args ):
    return " ".join( [a for a in args if a] )


def debug_data( data ):
    return "\n".join( filter(lambda x: x, [data['name']] + data['address_lines'] + [data['city'], data['country']] ) )
