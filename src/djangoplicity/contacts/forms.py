# -*- coding: utf-8 -*-
#
# djangoplicity-contacts
# Copyright (c) 2007-2014, European Southern Observatory (ESO)
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

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit

from django import forms
from django.forms import ModelForm, widgets

from djangoplicity.contacts.models import Contact


class ContactForm(ModelForm):
    # country = forms.CharField()
    # region = forms.CharField()
    language = forms.CharField(required=False)
    # groups = forms.CharField()

    class Meta:
        model = Contact
        exclude = ('extra_fields', )


class ContactListAdminForm(forms.ModelForm):
    zip = forms.CharField(required=False,
        widget=widgets.TextInput(attrs={'size': '8'}))

    class Meta:
        model = Contact
        fields = '__all__'


class ContactAdminForm(forms.ModelForm):
    #  region = forms.ModelChoiceField(queryset=Region.objects.all(),
    #              widget=RegionWidget(), required=False)
    zip = forms.CharField(required=False,
        widget=widgets.TextInput(attrs={'size': '8'}))

    class Meta:
        model = Contact
        fields = '__all__'


class ContactPublicForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ContactPublicForm, self).__init__(*args, **kwargs)
        # Allow Region widget to access form
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-md-2'
        self.helper.field_class = 'col-md-8'
        self.helper.add_input(Submit('submit', 'Save'))

    class Meta:
        model = Contact
        exclude = ['social', 'groups', 'group_order', 'extra_fields', 'created', 'laste_modified']


class GroupSubscribeForm(forms.Form):
    subscribe = forms.BooleanField(required=False)
    confirmaddress = forms.BooleanField(required=False)

    def clean_confirmaddress(self):
        confirmaddress = self.cleaned_data.get('confirmaddress')
        if not confirmaddress:
           raise forms.ValidationError('Please, confirm your address is up to date.')
        return confirmaddress

