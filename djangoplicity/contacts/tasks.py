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

import hashlib
from celery.task import PeriodicTask, task
from datetime import timedelta

from django.apps import apps
from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import send_mail
from django.core.urlresolvers import reverse

from djangoplicity.actions.plugins import ActionPlugin  # pylint: disable=E0611
from djangoplicity.utils.history import add_admin_history  # pylint: disable=E0611


@task(ignore_result=True)
def direct_import_data(import_pk):
    from djangoplicity.contacts.models import Import
    obj = Import.objects.get(pk=import_pk)

    logger = direct_import_data.get_logger()

    if obj.status == 'imported':
        return

    if obj.direct_import_data():
        obj.save()
        logger.warning('File was imported (pk=%s)' % obj.pk)
    else:
        logger.warning('File has already been imported (pk=%s)' % obj.pk)


@task( ignore_result=True )
def import_data( import_pk, request_POST ):
    """
    Run contacts import in the background, import_contacts is a dict:
    {'line_number ': {
            'target: 'new' or 'id'  # Create new contact or update 'id'
            'form': {}              # form for contact
        }, }
    of contact to import/create or update
    """
    logger = import_data.get_logger()

    from djangoplicity.contacts.models import Import
    from djangoplicity.contacts.admin import ImportAdmin
    from django.http import QueryDict

    # Convert request_POST (a dict) back to a QuerySet
    # All the values are single values except for the groups so we look at the
    # key name to figure out  how to insert the values in the QueryDict
    request = QueryDict('', mutable=True)
    for key in request_POST:
        if key.endswith('-groups'):
            request.setlist(key, request_POST[key])
        else:
            request[key] = request_POST[key]

    import_contacts = ImportAdmin.clean_import_data(request)

    obj = Import.objects.get( pk=import_pk )

    if obj.import_data(import_contacts):
        obj.save()
        logger.warning( "File was imported (pk=%s)" % obj.pk )
    else:
        logger.warning( "File has already been imported (pk=%s)" % obj.pk )


@task( ignore_result=True )
def prepare_import( import_pk, email ):
    """
    Look for potential duplicates in import
    """
    logger = prepare_import.get_logger()

    from djangoplicity.contacts.models import Import

    obj = Import.objects.get( pk=import_pk )

    if obj.prepare_import():
        obj.status = 'review'
        obj.save()
        logger.warning( "Import was preparred(pk=%s)" % obj.pk )

        # Send email to user:
        site = Site.objects.get_current()
        message = '''Dear User,

The import from file "%s" has been prepared and potential duplicates identified.
You can review the results and import the contacts at:
http://%s%s

''' % (obj.data_file, site.domain, reverse('admin:contacts_import_review', args=[obj.pk]))

        msg_from = getattr(settings, 'DEFAULT_FROM_EMAIL', '')
        msg_to = getattr(settings, 'CONTACT_IMPORT_NOTIFY', '')
        send_mail('Import %s (%s) ready for review' % (obj.pk, obj.data_file),
                message, msg_from, [email, msg_to])


@task(ignore_result=True)
def run_deduplication(deduplication_pk, email):
    """
    Look for potential duplicates in groups selected in deduplication
    """
    logger = run_deduplication.get_logger()

    from djangoplicity.contacts.models import Deduplication

    dedup = Deduplication.objects.get( pk=deduplication_pk )

    if dedup.run():
        dedup.status = 'review'
        dedup.save()
        logger.warning( "Deduplication task complete(pk=%s)" % dedup.pk )

        # Send email to user:
        site = Site.objects.get_current()
        message = '''Dear User,

The deduplication task is complete and potential duplicates identified.
You can review the results at:
http://%s%s

''' % (site.domain, reverse('admin:contacts_deduplication_review', args=[dedup.pk]))

        msg_from = getattr(settings, 'DEFAULT_FROM_EMAIL', '')
        msg_to = getattr(settings, 'CONTACT_IMPORT_NOTIFY', '')
        send_mail('Deduplication %s ready for review' % dedup.pk,
                message, msg_from, [email, msg_to])


@task
def contactgroup_change_check(old_groups_ids, contact_id, email):
    from djangoplicity.contacts.models import Contact, ContactGroup
    from djangoplicity.contacts.signals import contact_added, contact_removed
    logger = contactgroup_change_check.get_logger()
    try:
        c = Contact.objects.get(id=contact_id)
    except Contact.DoesNotExist:
        c = None

    old_groups = set(ContactGroup.objects.filter(id__in=old_groups_ids))

    if c:
        new_groups = set(c.groups.all())
        added = []
        removed = []

        for g in new_groups - old_groups:
            logger.info('Added "%s" to group "%s"', c, g)
            added.append(g.name)
            contact_added.send(sender=c.__class__, group=g, contact=c)

        for g in old_groups - new_groups:
            logger.info('Removed "%s" from group "%s"', c, g)
            removed.append(g.name)
            contact_removed.send(sender=c.__class__, group=g, contact=c, email=email)

        messages = []
        if added:
            messages.append('Added to groups: %s' % (', '.join(added)))
        if removed:
            messages.append('Removed from groups: %s' % (', '.join(removed)))

        if messages:
            add_admin_history(c, ', '.join(messages))

    else:
        # Contact has disappeared, remove it from its group
        for g in old_groups:
            logger.info('Remove disappeared contact "%s" from group "%s"', email, g)
            contact_removed.send(sender=c.__class__, group=g, contact=c, email=email)


class PeriodicAction( PeriodicTask ):
    """
    Dispatch periodic actions for groups.
    """
    abstract = True
    on_event_name = None

    def run( self ):
        """
        """
        logger = self.get_logger()

        from djangoplicity.contacts.models import ContactGroupAction, ContactGroup

        if self.on_event_name is None:
            raise ImproperlyConfigured( "on_event_name must be specified on class %s" % self.__class__.name )

        logger.info( "Dispatching periodic actions with event %s" % self.on_event_name )

        actions_by_group = ContactGroupAction.get_actions_for_event( self.on_event_name )
        group_pks = [int( x ) for x in actions_by_group.keys()]

        if group_pks:
            for group in ContactGroup.objects.filter( pk__in=group_pks ):
                for a in actions_by_group[str( group.pk )]:
                    a.dispatch( group=group )


class Every5minAction( PeriodicAction ):
    run_every = timedelta( minutes=5 )
    on_event_name = 'periodic_5min'


class Every30minAction( PeriodicAction ):
    run_every = timedelta( minutes=30 )
    on_event_name = 'periodic_30min'


class EveryHourAction( PeriodicAction ):
    run_every = timedelta( hours=1 )
    on_event_name = 'periodic_1hr'


class Every6HourAction( PeriodicAction ):
    run_every = timedelta( hours=6 )
    on_event_name = 'periodic_6hr'


class EveryDayAction( PeriodicAction ):
    run_every = timedelta( hours=24 )
    on_event_name = 'periodic_24hr'


#
# Contact actions
#
class ContactAction( ActionPlugin ):
    """
    An action plugin is a configurable celery task,
    that can be dynamically connected to events in the system.
    """
    abstract = True

    def _get_group( self, group_name ):
        """
        Get a group by its name
        """
        from djangoplicity.contacts.models import ContactGroup
        return ContactGroup.objects.get( name=group_name )

    def _get_object( self, model_identifier, pk ):
        """
        Helper method to get the object by model_identifier and primiary key ( e.g "contacts.contact" and 2579 )
        """
        Model = apps.get_model( *model_identifier.split( "." ) )
        return Model.objects.get( pk=pk )


class UpdateContactAction( ContactAction ):
    action_name = 'Contact update'
    action_parameters = [
        #( 'group', 'Name of group to assign to/remove from contact.', 'str' ),
    ]

    @classmethod
    def get_arguments( cls, conf, *args, **kwargs ):
        """
        """
        from djangoplicity.contacts.models import Contact

        try:
            model_identifier = kwargs['model_identifier']
            pk = kwargs['pk']
        except KeyError:
            model_identifier = None
            pk = None

        defaults = { 'model_identifier': model_identifier, 'pk': pk }

        for k, v in kwargs.items():
            # Hack to allow for languages changes:
            if k == 'get_language':
                k = 'language'
                v = Contact.get_language_code(v)
            # Allow add contacts groups
            if k == 'get_groups':
                defaults[k] = v
            if k in Contact.ALLOWED_FIELDS:
                defaults[k] = v

        return ( [], defaults )

    def run( self, conf, model_identifier=None, pk=None, **kwargs ):
        """
        Update contact based on new field values in kwargs.
        """
        from djangoplicity.contacts.models import Contact

        if model_identifier == 'contacts.contact' and pk:
            contact = self._get_object( model_identifier, pk )

            defaults = {}
            g_names = []
            for k, v in kwargs.items():
                if k in Contact.ALLOWED_FIELDS:
                    defaults[k] = v
                if 'get_groups' in kwargs:
                    g_names = [s.strip() for s in kwargs['get_groups'].split(',')]
                    del kwargs['get_groups']

            if contact.update_object(groups=g_names, **defaults):
                contact.save()
                self.get_logger().info( "Contact %s was updated." % ( contact.pk ) )
            else:
                self.get_logger().info( "Contact %s was not updated." % ( contact.pk ) )


class UpdateContactEmail(ContactAction):
    action_name = 'Update Contact email'
    action_parameters = []

    @classmethod
    def get_arguments(cls, conf, *args, **kwargs):
        try:
            new_email = kwargs['new_email']
            old_email = kwargs['old_email']
            list_id = kwargs['list_id']
        except KeyError:
            new_email = None
            old_email = None
            list_id = None

        defaults = {
            'new_email': new_email,
            'old_email': old_email,
            'list_id': list_id
        }
        return [], defaults

    def run(self, conf, list_id=None, new_email=None, old_email=None, **kwargs):
        """
        Update contact email based on new field values in kwargs.
        """
        from djangoplicity.contacts.models import Contact
        from djangoplicity.mailinglists.models import MailChimpList

        if list_id and new_email and old_email:
            contact = None
            try:
                # Get list by Id
                m_list = MailChimpList.objects.get(list_id=list_id)
                # Check and get subscriber data in mailchimp
                email_hash = hashlib.md5(str(new_email).encode("utf-8")).hexdigest()
                result = m_list.connection(
                    'lists.members.get',
                    list_id,
                    email_hash,
                )

                try:
                    model_identifier = result.get('merge_fields').get('DPID')
                except AttributeError:
                    model_identifier = ''
                contact = m_list.get_object_from_identifier(model_identifier)
            except MailChimpList.DoesNotExist:
                pass

            if contact and 'email' in Contact.ALLOWED_FIELDS:
                contact.email = new_email
                contact.save()
                self.get_logger().info("Contact email %s was updated." % contact.pk)
            else:
                self.get_logger().info("Contact email was not updated.")
                raise Exception("The contact email was not updated")


class CreateContactAction( ContactAction ):
    action_name = 'Contact create'
    action_parameters = [
        ( 'group', 'Name of group to assign to contact.', 'str' ),
    ]

    @classmethod
    def get_arguments( cls, conf, *args, **kwargs ):
        """
        """
        from djangoplicity.contacts.models import Contact

        model_identifier = kwargs.get('model_identifier', None)
        pk = kwargs.get('pk', None)

        defaults = { 'model_identifier': model_identifier, 'pk': pk }

        for k, v in kwargs.items():
            # Hack to allow for languages changes:
            if k == 'get_language':
                k = 'language'
                v = Contact.get_language_code(v)
            # Allow add contacts groups
            if k == 'get_groups':
                defaults[k] = v
            if k in Contact.ALLOWED_FIELDS:
                defaults[k] = v

        return ( [], defaults )

    def run( self, conf, model_identifier=None, pk=None, **kwargs ):
        """
        Create contact based on new field values in kwargs.
        """
        from djangoplicity.contacts.models import Contact
        if not model_identifier:
            model_identifier = 'contacts.contact'

        if model_identifier == 'contacts.contact' and pk is None:

            defaults = {}
            g_names = []

            for k, v in kwargs.items():
                if k in Contact.ALLOWED_FIELDS:
                    defaults[k] = v

                if 'get_groups' in kwargs:
                    g_names = [s.strip() for s in kwargs['get_groups'].split(',')]
                    del kwargs['get_groups']
            contact = Contact.create_object(groups=g_names, **defaults)

            if contact:
                group = self._get_group(conf['group'])
                if group:
                    contact.groups.add(group)
                    self.get_logger().info("Contact %s was created and added to group %s." % (contact.pk, group))
                else:
                    self.get_logger().info("Contact %s was created." % (contact.pk))
            else:
                self.get_logger().info("Contact %s was not created." % (defaults['email']))


class SetContactGroupAction( ContactAction ):
    action_name = 'Contacts add group'
    action_parameters = [
        ( 'group', 'Name of group to assign to contact.', 'str' ),
    ]

    @classmethod
    def get_arguments( cls, conf, *args, **kwargs ):
        """
        """
        try:
            model_identifier = kwargs['model_identifier']
            pk = kwargs['pk']
        except KeyError:
            model_identifier = None
            pk = None

        return ( [], { 'model_identifier': model_identifier, 'pk': pk } )

    def run( self, conf, model_identifier=None, pk=None ):
        """
        Add a contact to a group
        """
        if model_identifier == 'contacts.contact' and pk:
            contact = self._get_object( model_identifier, pk )
            group = self._get_group( conf['group'] )

            contact.groups.add( group )
            self.get_logger().info( "Added contact %s from group %s." % ( contact.pk, group.name ) )


class UnsetContactGroupAction( ContactAction ):
    action_name = 'Contacts remove group'
    action_parameters = [
        ( 'group', 'Name of group to remove from contact.', 'str' ),
    ]

    @classmethod
    def get_arguments( cls, conf, *args, **kwargs ):
        """
        """
        try:
            model_identifier = kwargs['model_identifier']
            pk = kwargs['pk']
        except KeyError:
            model_identifier = None
            pk = None

        return ( [], { 'model_identifier': model_identifier, 'pk': pk } )

    def run( self, conf, model_identifier=None, pk=None ):
        """
        Remove from a group from a contact.
        """
        if model_identifier == 'contacts.contact' and pk:
            contact = self._get_object( model_identifier, pk )
            group = self._get_group( conf['group'] )

            contact.groups.remove( group )
            self.get_logger().info( "Removed contact %s from group %s." % ( contact.pk, group.name ) )


class RemoveEmailAction( ContactAction ):
    action_name = 'Contacts clean email'
    action_parameters = [
        ( 'clear', 'Clear the email field for all contacts with this email', 'bool' ),
        ( 'append', 'If clear is False, append the text in this field to contacts with this email (unless the field is empty)', 'str' ),
    ]

    @classmethod
    def get_arguments( cls, conf, *args, **kwargs ):
        """
        """
        try:
            email = kwargs['email']
        except KeyError:
            email = None

        return ( [], { 'email': email } )

    def run( self, conf, email=None ):
        """
        Remove from a group from a contact.
        """
        from djangoplicity.contacts.models import Contact

        if email:
            num = 0
            if conf['clear']:
                num = Contact.objects.filter( email__iexact=email ).update( email='' )
            elif conf['append']:
                num = Contact.objects.filter( email__iexact=email ).update( email=email.lower() + conf['append'] )

            if num > 0:
                self.get_logger().info( "Removed invalid email address %s from %s contact(s)." % ( email, num ) )


UnsetContactGroupAction.register()
SetContactGroupAction.register()
RemoveEmailAction.register()
UpdateContactAction.register()
CreateContactAction.register()
UpdateContactEmail.register()
