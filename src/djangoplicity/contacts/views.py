# -*- coding: utf-8 -*-
#
# djangoplicity-contacts
# Copyright (c) 2007-2014, European Southern Observatory (ESO)
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

from djangoplicity.contacts.models import Contact
from djangoplicity.contacts.forms import ContactPublicForm

from django.contrib import messages
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.contenttypes.models import ContentType
from django.http import Http404
from django.views.generic import UpdateView


class ContactPublicUpdate(UpdateView):
	'''
	Class to allow a given contact to be updated without authentication
	This is meant for people to update their contact information given
	a unique URL
	'''
	model = Contact
	form_class = ContactPublicForm
	template_name = 'contacts/contact_public_form.html'

	def get_object(self, queryset=None):
		uid = self.kwargs.get('uid', None)
		try:
			contact = Contact.from_uid(uid)
		except Contact.DoesNotExist:
			raise Http404

		return contact

	def form_valid(self, form):
		'''
		Add an entry to the Contact's admin history and set
		a success message to display to the user
		'''
		messages.success(self.request, 'Your Contact information have been successfully updated. Thank you!')

		# Get list of modifield fields
		obj = self.get_object()
		changed_fields = []

		for field, value in form.cleaned_data.items():
			if value != getattr(obj, field):
				changed_fields.append(form[field].label)

		if changed_fields:
			change_message = 'Changed (from public interface) %s' % ', '.join(changed_fields)

			# log_action expect a valid user_id, as the action is not done by a
			# registered User we fake it and use 93 (mandre)
			LogEntry.objects.log_action(
					user_id=93,
					content_type_id=ContentType.objects.get_for_model(self.object).pk,
					object_id=self.object.id,
					object_repr=unicode(self.object),
					action_flag=CHANGE,
					change_message=change_message)

		return super(ContactPublicUpdate, self).form_valid(form)

	def get_success_url(self):
		'''
		Return the current path to stay on the same page
		after a successful edit
		'''
		return self.request.path
