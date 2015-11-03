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

from djangoplicity.contacts.models import Contact, ContactGroup
from djangoplicity.contacts.forms import ContactPublicForm, GroupSubscribeForm
from djangoplicity.contacts.signals import contact_added, contact_removed

from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.contenttypes.models import ContentType
from django.http import Http404
from django.views.generic import FormView, UpdateView


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
		'''
		Check that a contact with the given UID exists
		or raise 404
		'''
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
			# registered User we use the ID of an anonymous User if it exists,
			# otherwise we use the first ID we fine
			try:
				user = User.objects.get(username='anonymous')
			except User.DoesNotExist:
				user = User.objects.all()[0]

			LogEntry.objects.log_action(
					user_id=user.id,
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


class GroupSubscribe(FormView):
	'''
	View to allow a contact to subscribe to a given group.
	group and template_name must be passed as arguments to as_view() such as:
	GroupSubscribe.as_view(group=357, template_name='contacts/messenger_public_subscribe.html')
	'''
	form_class = GroupSubscribeForm
	group = None
	template_name = ''

	def get_initial(self):
		'''
		Check that the contact actually exists and prepare the form
		'''
		uid = self.kwargs.get('uid', None)
		try:
			self.contact = Contact.from_uid(uid)
		except Contact.DoesNotExist:
			raise Http404

		# Check that the group has been set correctly in the urls.py and exists
		try:
			self.group = ContactGroup.objects.get(id=self.group)
		except ContactGroup.DoesNotExist:
			raise Http404

		initial = {}

		# Check if the contact already belongs to the group
		if self.group in self.contact.groups.all():
			initial['subscribe'] = True
		else:
			initial['subscribe'] = False

		return initial

	def form_valid(self, form):
		'''
		Subscribe/unsubscribe the contact to the group
		'''
		subscribe = form.cleaned_data['subscribe']

		if self.group in self.contact.groups.all():
			# The contact is already a member of the group
			if not subscribe:
				self.contact.groups.remove(self.group)
				contact_removed.send(sender=self.contact.__class__, group=self.group, contact=self.contact, email=self.contact.email)
		else:
			# The contact is already a member of the group
			if subscribe:
				self.contact.groups.add(self.group)
				contact_added.send(sender=self.contact.__class__, group=self.group, contact=self.contact)

		messages.success(self.request, 'Your Subscription preferences have been successful updated. Thank you!')

		return super(GroupSubscribe, self).form_valid(form)

	def get_context_data(self, **kwargs):
		context = super(GroupSubscribe, self).get_context_data(**kwargs)
		context['contact'] = self.contact

		return context

	def get_success_url(self):
		'''
		Return the current path to stay on the same page
		after a successful edit
		'''
		return self.request.path
