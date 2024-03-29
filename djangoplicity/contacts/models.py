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


from datetime import datetime
from dirtyfields import DirtyFieldsMixin
from hashids import Hashids
import logging
import os
import json

from django.conf import settings
from django.core.cache import cache
from django.core.files.storage import FileSystemStorage
from django.core.urlresolvers import reverse as url_reverse
from django.db import models, connection
from django.db.models.signals import pre_delete, post_delete, post_save, \
    pre_save
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from djangoplicity.actions.models import Action  # pylint: disable=E0611
from djangoplicity.contacts.labels import LabelRender, LABEL_PAPER_CHOICES
from djangoplicity.contacts.signals import contact_added, contact_removed, \
    contact_updated
from djangoplicity.contacts.tasks import contactgroup_change_check
from djangoplicity.contacts import deduplication
from djangoplicity.translation.fields import LanguageField  # pylint: disable=E0611


logger = logging.getLogger( 'djangoplicity' )


class Label( models.Model ):
    """
    Object to define labels
    """
    name = models.CharField( max_length=255 )
    paper = models.CharField( max_length=255, choices=LABEL_PAPER_CHOICES )
    repeat = models.PositiveIntegerField( default=1 )
    style = models.TextField( blank=True )
    template = models.TextField( blank=True )
    enabled = models.BooleanField( default=True )

    def get_label_render( self ):
        return LabelRender( self.paper, label_template=self.template, style=self.style, repeat=self.repeat )

    def __unicode__( self ):
        return self.name

    class Meta:
        ordering = ['name']


class Field( models.Model ):
    """
    Definition of extra fields (i.e. fields not defined on contact model.)

    This allows users to create an new field, and add data in it. Normally this should
    only be used to record extra non-essential data, as access to the data (searching etc)
    is limited and slower than when defined on the contacts models.
    """

    slug = models.SlugField( unique=True )
    # Short name used for external applications to pass data to the contacts database.

    name = models.CharField( max_length=255, unique=True )
    # Human readable name for field.

    blank = models.BooleanField( default=True )
    # Does field allow blank values

    _allowed_fields = None

    @classmethod
    def _get_cache( cls ):
        """
        List of fields are cached for speed efficiency.
        """
        if cls._allowed_fields is None:
            cls._allowed_fields = list( cls.objects.values_list( 'slug', 'name' ) )
        return cls._allowed_fields if cls._allowed_fields else []

    @classmethod
    def field_options( cls ):
        """
        Get a list of field choices (slug,name) for use in form field choices.
        """
        return cls._get_cache()

    @classmethod
    def allowed_fields( cls ):
        """
        Get a list of field slugs
        """
        return [ x[0] for x in cls._get_cache() ]

    def save( self, *args, **kwargs ):
        """
        Clear field cache if an object is saved.
        """
        super( Field, self ).save( *args, **kwargs )
        self.__class__._slug_cache = None

    def __unicode__( self ):
        return self.name

    class Meta:
        ordering = ['name']


class GroupCategory( models.Model ):
    """
    Groupings of groups.
    """
    name = models.CharField( max_length=255, blank=True )

    def __unicode__( self ):
        return self.name

    class Meta:
        verbose_name_plural = 'group categories'
        ordering = ( 'name', )


class CountryGroup( models.Model ):
    """
    Allow grouping of countries (e.g. EU, member states)
    """
    name = models.CharField( max_length=255, blank=True, db_index=True )
    category = models.ForeignKey( GroupCategory, blank=True, null=True )

    def __unicode__( self ):
        return self.name

    class Meta:
        ordering = ( 'category__name', 'name' )


class PostalZone( models.Model ):
    """
    Postal zones for countries
    """
    name = models.CharField( max_length=255, unique=True )

    def __unicode__( self ):
        return self.name

    class Meta:
        ordering = [ 'name', ]


class Country( models.Model ):
    """
    Country model for storing country names.
    """
    name = models.CharField( max_length=40, db_index=True )
    iso_code = models.CharField( _( 'ISO code' ), max_length=5, blank=True )
    dialing_code = models.CharField( max_length=10, blank=True )
    zip_after_city = models.BooleanField( default=False )
    postal_zone = models.ForeignKey( PostalZone, null=True, blank=True )
    groups = models.ManyToManyField( CountryGroup, blank=True )

    def get_zip_city( self, zip_, city ):
        """
        Method to combine ZIP/post case and city for a country.
        """
        if self.zip_after_city:
            return ( "%s %s" % ( city, zip_ ) ).strip()
        else:
            return ( "%s %s" % ( zip_, city ) ).strip()

    @classmethod
    def country_index( cls ):
        """
        Get a dictionary which can be indexed by ISO code to get the country.
        """
        data = {}
        for c in cls.objects.all():
            if c.iso_code:
                data[c.iso_code.upper()] = c
        return data

    def save( self, *args, **kwargs ):
        """ Ensure ISO code is in upper case """
        self.iso_code = self.iso_code.upper()
        super( Country, self ).save( *args, **kwargs )

    def __unicode__( self ):
        return self.name

    class Meta:
        verbose_name_plural = _( 'countries' )
        ordering = ['name', ]


class Region(models.Model):
    '''
    Regions for Countries
    '''
    name = models.CharField(max_length=200, db_index=True, verbose_name='Region/State name')
    local_name = models.CharField(max_length=200, verbose_name='Region/State name in the local language')
    code = models.CharField(max_length=200, db_index=True)
    country = models.ForeignKey(Country)

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['country', 'name']


class ContactGroup( DirtyFieldsMixin, models.Model ):
    """
    Groups for contacts

    The order field allows to specify a numerical values
    by which the groups should be sorted and allows you to
    sort contacts by the ordering of groups. Due to the way the django
    ORM works, it's however difficult to order by a related attribute
    and at the same time select only distinct contacts. For that reason
    a minimum group order value is stored on each contact. This value
    is automatically propagated to all contacts.

    djangoplicity.contacts.tets.orderpropagation contains tests to validate
    that the propagation happens correctly.
    """
    name = models.CharField( max_length=255, blank=True )
    category = models.ForeignKey( GroupCategory, blank=True, null=True )
    order = models.PositiveIntegerField( blank=True, null=True )

    def get_emails( self ):
        """ Get all email addresses for contacts in this group """
        return self.contact_set.exclude(email='').exclude(email__iendswith='-invalid').values_list('email', flat=True)

    def __unicode__( self ):
        return self.name

    @classmethod
    def pre_delete_callback( cls, sender, instance=None, **kwargs ):
        """
        Propagate ContactGroup.order to contacts on delete
        """

        # Get a query of contacts to update and make sure it's evaluated (the contacts will be updated in the post_delete_callback)
        # This cannot be done in post_delete, since then the object have been deleted from the database, and the relationships are
        # no longer present in the database.
        if instance.order:
            instance._cached_contact_set = list( instance.contact_set.filter( group_order__gte=instance.order ).values_list( 'pk', flat=True ) )
        else:
            instance._cached_contact_set = []

    @classmethod
    def post_delete_callback( cls, sender, instance=None, **kwargs ):
        """
        Propagate ContactGroup.order to contacts on delete
        """

        # See notes in pre_delete_callback
        for c in Contact.objects.filter( pk__in=instance._cached_contact_set ).annotate( min__group_order=models.Min( 'groups__order' ) ):
            if c.group_order != c.min__group_order:
                Contact.objects.filter( pk=c.pk ).update( group_order=c.min__group_order )

    @classmethod
    def pre_save_callback( cls, sender, instance=None, raw=False, **kwargs ):
        """
        Propagate ContactGroup.order to contacts on save (if order was changed)
        """
        if raw:
            return
        instance._dirty_fields = instance.get_dirty_fields()

    @classmethod
    def post_save_callback( cls, sender, instance=None, **kwargs ):
        """
        Propagate ContactGroup.order to contacts on save (if order was changed)
        """
        if 'raw' in kwargs and kwargs['raw']:
            return

        dirty_fields = instance._dirty_fields
        instance._dirty_fields = None

        if 'order' in dirty_fields:
            if dirty_fields['order'] is None or dirty_fields['order'] - instance.order > 0:
                # Order value was changed to a smaller value - hence we must update all contacts
                # with a group_order greater than instance.order.
                if instance.order is not None:
                    instance.contact_set.filter( group_order__gt=instance.order ).update( group_order=instance.order )
            elif instance.order is None or dirty_fields['order'] - instance.order < 0:
                # Order value was changed to a greater value - hence we must update all contacts
                # with a group_order greater than the *old* instance.order
                for c in Contact.objects.filter( pk__in=instance.contact_set.filter( group_order__gte=dirty_fields['order'] ) ).annotate( min__group_order=models.Min( 'groups__order' ) ):
                    if c.group_order != c.min__group_order:
                        Contact.objects.filter( pk=c.pk ).update( group_order=c.min__group_order )

        # Reset dirty state - DirtyFieldMixin is supposed to do it automatically,
        # but apparently there's some conflicts with the signals it seems like.
        instance._original_state = instance._as_dict(False)

    class Meta:
        ordering = ( 'name', )


class Contact( DirtyFieldsMixin, models.Model ):
    """
    Contacts model
    """
    title = models.CharField( max_length=50, blank=True, db_index=True )
    first_name = models.CharField( max_length=255, blank=True )
    last_name = models.CharField( max_length=255, blank=True )
    position = models.CharField( max_length=255, blank=True )
    organisation = models.CharField( max_length=255, blank=True )
    department = models.CharField( max_length=255, blank=True )
    street_1 = models.CharField( max_length=255, blank=True )
    street_2 = models.CharField( max_length=255, blank=True )
    zip = models.CharField( max_length=50, blank=True, help_text=_('ZIP/Postcal code'))
    city = models.CharField( max_length=255, blank=True )
    country = models.ForeignKey( Country, blank=True, null=True )
    region = models.ForeignKey(Region, blank=True, null=True)
    tax_code = models.CharField(_('Tax Code'), max_length=20, blank=True,
        help_text=_('Tax Code for Argentina, Brazil, Paraguay, Peru (CUIT/CPF/RUC)'))

    phone = models.CharField( max_length=255, blank=True )
    website = models.CharField( 'Website', max_length=255, blank=True )
    social = models.CharField( 'Social media', max_length=255, blank=True )
    email = models.EmailField( blank=True )

    language = LanguageField(verbose_name=_( 'Language' ), max_length=7, blank=True, null=True)

    groups = models.ManyToManyField( ContactGroup, blank=True )
    group_order = models.PositiveIntegerField( blank=True, null=True )

    extra_fields = models.ManyToManyField( Field, through='ContactField' )

    created = models.DateTimeField( auto_now_add=True )
    last_modified = models.DateTimeField( auto_now=True )

    def set_extra_field( self, field_slug, value ):
        """
        Convenience method to set the value of an extra field on a contact
        """
        f = Field.objects.get( slug=field_slug )
        try:
            cf = ContactField.objects.get( field=f, contact=self )
        except ContactField.DoesNotExist:
            cf = ContactField( field=f, contact=self )

        cf.value = value
        cf.save()

    def get_extra_field( self, field_slug ):
        """
        Convenience method to get the value of an extra field on a contact
        """
        f = Field.objects.get( slug=field_slug )
        try:
            cf = ContactField.objects.get( field=f, contact=self )
            return cf.value
        except ContactField.DoesNotExist:
            return None

    def get_data( self ):
        """
        Get a dictionary of this object
        """
        data = {}
        data['name'] = ( "%s %s %s" % ( self.title, self.first_name, self.last_name ) ).strip()
        data['first_name'] = self.first_name.strip()
        data['last_name'] = self.last_name.strip()
        data['address_lines'] = [x.strip() for x in self.organisation, self.department, self.street_1, self.street_2]
        data['street_1'] = self.street_1.strip()
        data['street_2'] = self.street_2.strip()
        data['city'] = self.city.strip()
        data['email'] = self.email.strip()
        data['organisation'] = self.organisation.strip()
        data['department'] = self.department.strip()
        data['country'] = self.country.pk if self.country else ''
        data['contact_object'] = self
        return data

    def get_language(self):
        '''
        Return the full language string:
        '''
        if self.language:
            for code, language in settings.LANGUAGES:
                if code == self.language:
                    return language
        return ''

    def get_groups(self):
        '''
        Return all name groups in a array
        '''
        return [g.name for g in self.groups.all()]

    @classmethod
    def get_contacts_with_email(cls, email):
        return cls.objects.filter(email=email)

    @classmethod
    def get_language_code(cls, language):
        '''
        Return the language code for the given language string:
        '''
        if language:
            for code, lang in settings.LANGUAGES:
                if lang == language:
                    return code
        return ''

    ALLOWED_FIELDS = ['first_name', 'last_name', 'title', 'position', 'organisation', 'department', 'street_1', 'street_2', 'tax_code', 'city', 'zip', 'state', 'country', 'region', 'phone', 'website', 'social', 'email', 'language' ]

    @classmethod
    def get_allowed_extra_fields( cls ):
        """
        Get list of allowed extra field names ( including extra fields ).
        """
        return Field.allowed_fields()

    @classmethod
    def find_or_create_object( cls, **kwargs ):
        """
        Find an object or create it if no match was found.
        """
        obj = cls.find_object( **kwargs )
        return obj if obj else cls.create_object( **kwargs )

    @classmethod
    def _select_contact( cls, qs ):
        """
        """
        qsnew = [x for x in qs if 'librarian' in x.last_name.lower()]
        if len( qsnew ) > 0:
            return qsnew[0]
        else:
            return qs[0]

    @classmethod
    def find_objects( cls, **kwargs ):
        """
        Find all matching contacts
        """
        for field in ['pk', 'id']:
            if field in kwargs and kwargs[field]:
                qs = cls.objects.filter( pk=kwargs[field] )
                if len( qs ) >= 1:
                    return qs

        for field in ['email']:
            if field in kwargs and kwargs[field]:
                qs = cls.objects.filter( email=kwargs[field] )
                if len( qs ) >= 1:
                    return qs
        return None

    @classmethod
    def find_object( cls, **kwargs ):
        """
        Find one matching contact
        """
        qs = cls.find_objects( **kwargs )
        if qs:
            if len( qs ) == 1:
                return qs[0]
            elif len( qs ) > 1:
                return cls._select_contact( qs )
        return None

    @classmethod
    def create_object( cls, groups=None, **kwargs ):
        """
        Create a new contact from dictionary.
        """
        if groups is None:
            groups = []
        obj = cls()
        if obj.update_object( **kwargs ):
            obj.save()
            obj.update_extra_fields( **kwargs )
            if groups:
                try:
                    groups = list(ContactGroup.objects.filter(id__in=groups))
                except ValueError:
                    # In case the groups is a list of strings and not ids
                    groups = list(ContactGroup.objects.filter(name__in=groups))
                if groups:
                    obj.groups.add( *groups )
                for g in groups:
                    contact_added.send(sender=obj.__class__, group=g, contact=obj)
            return obj
        else:
            return None

    def update_object( self, groups=None, **kwargs ):
        """
        Update a contact with new information from a dictionary. Following keys are supported:
            * first_name
            * last_name
            * title
            * position
            * organisation
            * department
            * street_1
            * street_2
            * city
            * zip
            * country (2 letter ISO code)
            * phone
            * website
            * social
            * email
        """
        changed = False

        ctry = None
        if 'country' in kwargs:
            if kwargs['country'] and isinstance(kwargs['country'], int):
                ctry = Country.objects.get(pk=kwargs['country'])
            elif kwargs['country'] and len( kwargs['country'] ) == 2:
                ctry = Country.objects.get( iso_code=kwargs['country'].upper() )
            elif kwargs['country']:
                ctry = Country.objects.get( name__iexact=kwargs['country'] )
            self.country = ctry
            changed = True
            del kwargs['country']
        if 'region' in kwargs:
            if kwargs['region']:
                try:
                    self.region = Region.objects.get(pk=kwargs['region'])
                    changed = True
                except ValueError:
                    if self.country:
                        query = Region.objects.filter(name__icontains=kwargs['region'], country=self.country)
                        if query:
                            self.region = query[0]
                            changed = True
            del kwargs['region']
        if groups:
            try:
                groups = list(ContactGroup.objects.filter(id__in=groups))
            except ValueError:
                groups = list(ContactGroup.objects.filter(name__in=groups))
            if groups:
                self.groups.add( *groups )
            for g in groups:
                contact_added.send(sender=self.__class__, group=g, contact=self)

        # Set the fields
        for field, val in kwargs.items():
            if field in self.ALLOWED_FIELDS:
                setattr( self, field, val )
                changed = True

        if self.pk:
            self.update_extra_fields( **kwargs )

        return changed

    def update_extra_fields( self, **kwargs ):
        """
        Settings extra fields requires the contact to be saved to the database
        before being able to set them, hence they are updated separately from the
        Contact's models fields.
        """
        extra_fields = self.get_allowed_extra_fields()
        changed = False

        for field, val in kwargs.items():
            if field in extra_fields:
                self.set_extra_field( field, val )
                changed = True

        return changed

    def __unicode__( self ):
        if self.first_name or self.last_name:
            return ( "%s %s %s" % ( self.title, self.first_name, self.last_name ) ).strip()
        elif self.organisation:
            return self.organisation
        elif self.department:
            return self.department
        else:
            return unicode( self.pk )

    @classmethod
    def pre_delete_callback( cls, sender, instance=None, **kwargs ):
        """
        Callback is used to send contact_removed, contact_added signals
        """
        # If there is a duplicated contact, do not unsubscribe it from Mailchimp
        if len(cls.get_contacts_with_email(instance.email)) == 1:
            for g in instance.groups.all():
                contact_removed.send_robust(sender=cls, group=g, contact=instance, email=instance.email)

    @classmethod
    def pre_save_callback( cls, sender, instance=None, raw=False, **kwargs ):
        """
        Callback for detecting changes to the model.
        """
        if raw:
            return
        if instance.email:
            # All email addresses use lower-case
            instance.email = instance.email.lower()
        instance._dirty_fields = instance.get_dirty_fields()

        # Start a celery task to check if the groups have been changed.
        # Ideally we would use m2m_changed signals, but at the moment Django
        # admin first clears then add the groups which makes it very hard
        # to identify changed groups. Instead we store the current groups' IDs
        # and check if they have change when the task is run 20s later.
        # 20s is just an arbitrary value to give enough time for the contact to
        # be saved and the m2m relations saved to the DB
        # In case the contact is new we don't have the PK yet, so we store
        # the groups in a instance attribute _initial_groups and call the
        # task in the post_save
        if instance.pk:
            instance._initial_groups = list(instance.groups.values_list('id', flat=True))
        else:
            # Contact is new:
            instance._initial_groups = []

    @classmethod
    def post_save_callback( cls, sender, instance=None, **kwargs ):
        """
        Callback for detecting changes to the model.
        """
        if 'raw' in kwargs and kwargs['raw']:
            return

        dirty_fields = instance._dirty_fields
        instance._dirty_fields = None
        if dirty_fields != {}:
            contact_updated.send( sender=cls, instance=instance, dirty_fields=dirty_fields )

        # Send task to check group changes, see pre_save_callback for details
        if instance and hasattr(instance, '_initial_groups'):
            contactgroup_change_check.apply_async(
                (instance._initial_groups, instance.pk, instance.email),
                countdown=20,
            )

    def get_uid(self):
        '''
        Returns the Contact's UID, used when publicly accessing the
        edit interface.
        We use Hashids to encrypt the Contact's ID into a unique string
        '''
        hashids = Hashids(salt=settings.HASHIDS_SALT)

        return hashids.encrypt(self.id)

    uid = property(get_uid)

    @classmethod
    def from_uid(cls, uid):
        '''
        Returns the contact matching the UID
        Raise Contact.DoesNotExist if no matching Contact
        '''
        hashids = Hashids(salt=settings.HASHIDS_SALT)

        pk = hashids.decrypt(uid)
        if pk:
            return Contact.objects.get(pk=pk[0])
        else:
            raise Contact.DoesNotExist

    class Meta:
        ordering = ['last_name']


class ContactField( models.Model ):
    """
    Stores a field value for a given contact.
    """
    field = models.ForeignKey( Field )
    contact = models.ForeignKey( Contact )
    value = models.CharField( max_length=255, blank=True, db_index=True )

    def __unicode__( self ):
        return self.value

    class Meta:
        unique_together = ( 'field', 'contact' )


# More advanced stuff - configurable actions to be execute once
# contacts are added/removed from groups (e.g subscribe to mailman).

ACTION_EVENTS = (
    ( 'contact_added', 'Contact added to group' ),
    ( 'contact_removed', 'Contact removed from group' ),
    ( 'contact_updated', 'Contact updated' ),
    ( 'periodic_5min', 'Every 5 minutes' ),
    ( 'periodic_30min', 'Every 30 minutes' ),
    ( 'periodic_1hr', 'Every hour' ),
    ( 'periodic_6hr', 'Every 6 hours' ),
    ( 'periodic_24hr', 'Every day' ),
)


class ContactGroupAction( models.Model ):
    """
    Define actions to be executed when a contact is added
    or removed to a group.
    """
    group = models.ForeignKey( ContactGroup )
    action = models.ForeignKey( Action )
    on_event = models.CharField( max_length=50, choices=ACTION_EVENTS, db_index=True )

    _key = 'djangoplicity.contacts.action_cache'

    @classmethod
    def clear_cache( cls, *args, **kwargs ):
        """
        Ensure cache is reset in case any change is made.
        """
        cache.delete( cls._key )

    @classmethod
    def create_cache( cls, *args, **kwargs ):
        """
        Generate new action cache.

        The cache has two ways of indexing:
            * by group then event
            * or, event then group

        Since ``group_pk'' are always numbers, and ``on_event'' is
        always characters, the keys will not collide.

        cache = {
            '<group_pk>' : {
                '<on_event>' : [ <action>, ... ],
                ...
            },
            ...
            '<on_event>' : {
                '<group_pk>' : [ <action>, ... ],
                '<group_pk>' : [ <action>, ... ],
            },
            ...
        }
        """
        action_cache = {}
        for a in cls.objects.all().select_related('action', 'group').order_by( 'group', 'on_event', 'action' ):
            g_pk = str( a.group.pk )
            # by group_pk, event
            if g_pk not in action_cache:
                action_cache[ g_pk ] = {}
            if a.on_event not in action_cache[g_pk]:
                action_cache[ g_pk ][a.on_event] = []

            if a.on_event not in action_cache:
                action_cache[a.on_event] = {}
            if g_pk not in action_cache[a.on_event]:
                action_cache[a.on_event][ g_pk ] = []

            action_cache[ g_pk ][a.on_event].append( a.action )
            action_cache[ a.on_event ][g_pk].append( a.action )

            # by event, group_pk = actions

        cache.set( cls._key, action_cache )
        return action_cache

    @classmethod
    def get_cache( cls, ):
        """
        Get the action cache - generate it if necessary.

        Caches results to prevent many queries to the database. Currently the entire
        table is cached, however in case of issues, this caching strategy can be improved.
        """
        action_cache = cache.get( cls._key )

        # Prime cache if needed
        if action_cache is None:
            action_cache = cls.create_cache()

        return action_cache

    @classmethod
    def get_actions_for_event( cls, on_event, group_pk=None ):
        """
        """
        action_cache = cls.get_cache()

        try:
            actions = action_cache[on_event]
            return actions if group_pk is None else actions[str( group_pk )]
        except:  # pylint: disable=W0702
            return {} if group_pk is None else []

    @classmethod
    def get_actions( cls, group, on_event=None ):
        """
        Get all actions defined for a certain group.
        """
        action_cache = cls.get_cache()

        # Find actions for this group
        try:
            actions = action_cache[ str( group.pk ) ]
            return actions if on_event is None else actions[on_event]
        except KeyError:
            return {} if on_event is None else []

    @classmethod
    def contact_added_callback( cls, sender=None, group=None, contact=None, **kwargs ):
        """
        Callback handler for when a contact is *added* to a group. Will execute defined
        actions for this group.
        """
        logger.debug( "contact %s added to group %s", contact.pk, group.pk )
        for a in cls.get_actions( group, on_event='contact_added' ):
            a.dispatch( group=group, contact=contact )

    @classmethod
    def contact_removed_callback( cls, sender=None, group=None, contact=None, email=None, **kwargs ):
        """
        Callback handler for when a contact is *removed* from a group. Will execute defined
        actions for this group.
        """
        logger.debug( "contact %s removed from group %s", contact.pk, group.pk )
        for a in cls.get_actions( group, on_event='contact_removed' ):
            a.dispatch( group=group, contact=contact, email=email )

    @classmethod
    def contact_updated_callback( cls, sender=None, instance=None, dirty_fields=None, **kwargs ):
        """
        Callback handler for when a local field is *updated*. Will execute defined actions for
        all groups for this contact.
        """
        if dirty_fields is None:
            dirty_fields = {}
        logger.debug( "contact %s updated", instance.pk )
        updates = {}
        if dirty_fields:
            for attr, val in dirty_fields.items():
                updates[attr] = ( val, getattr( instance, attr, None ) )

            for group in instance.groups.all():
                for a in cls.get_actions( group, on_event='contact_updated' ):
                    a.dispatch( instance=instance, changes=updates )


# ====================================================================
# Import-related models
# ====================================================================

class DataImportError( Exception ):
    pass


class ColumnDoesNotExists( Exception ):
    pass


ISO_EXPANSION = {
    'ES': [u'espana', u'españa'],
    'IT': [u'italia', ],
    'GB': [u'uk', u'england', u'great britan', ],
    'US': [u'united states'],
    'NL': [u'netherlands', u'holland'],
    'MX': [u'méxico'],
    'DE': [u'deutschland'],
}

DUPLICATE_HANDLING = [
# Tue Mar 12 18:50:35 CET 2013 - Mathias Andre
# Disabled "simple" import for now as it was broken by
# the updated duplicate merging changes
    ( 'none', 'Import all - no duplicate detection' ),
    ( 'smart', 'Detect duplicates and wait for review' ),
]


class ImportTemplate( models.Model ):
    """
    An import template defines how a CSV or Excel file should be
    imported into the contacts model. It supports mapping columns
    to contacts fields.

    It also supports mapping columns to country and groups models.

    Mapping to a country is done in a fuzzy way, to allow for different
    spellings of a country name.

    Caching Notes
    -------------
    An ImportTemplate and ImportMapping caches selectors/mappings/group mappings
    and countries inside the instance of the object. If you change (and save) a
    selector, mapping or group mapping, this cache will be cleared for the
    instance in this thread. However, other threads may have cached the data
    and also the country cache is not cleared automatically.

    In practice this is however not a problem, since usually an ImportTemplate is
    loaded and used to run an import once. If an loaded ImportTemplate, however is
    used several times and selectors or mappings are changed during those imports
    be sure to test that the import is actually doing what you want it to do.
    """
    name = models.CharField( max_length=255, unique=True )
    duplicate_handling = models.CharField( max_length=20, choices=DUPLICATE_HANDLING, help_text='', default='smart' )
    frozen_groups = models.ManyToManyField( ContactGroup, blank=True, help_text='Contacts belonging to these groups will not be updated.', related_name='importtemplate_frozen_set' )

    tag_import = models.BooleanField( default=True, help_text="Create a contact group for this import." )
    extra_groups = models.ManyToManyField( ContactGroup, blank=True )

    _selectors_cache = None
    _mapping_cache = None

    class Meta:
        ordering = ['name', ]

    def __unicode__( self ):
        return self.name

    def clear_selector_cache( self ):
        """
        Called from ImportSelector, to clear the selector cache on a template
        if a selector is changed.
        """
        self._selectors_cache = None

    def clear_mapping_cache( self ):
        """
        Called from ImportMapping, to clear the selector cache on a template
        if a mapping is changed.
        """
        self._mapping_cache = None

    def get_selectors( self ):
        """
        Get selectors for this template. Selectors are being cached, to make retrieval faster.
        """
        if self._selectors_cache is None:
            self._selectors_cache = [x for x in ImportSelector.objects.filter( template=self )]
        return self._selectors_cache

    def is_selected( self, data ):
        """
        Determine if a data row should be imported or not.
        """
        selectors = self.get_selectors()

        if not selectors:
            return True

        for s in selectors:
            if s.is_selected( data ):
                return True
        return False

    def get_mapping( self ):
        if self._mapping_cache is None:
            self._mapping_cache = [x for x in ImportMapping.objects.filter( template=self )]
        return self._mapping_cache

    def parse_row( self, incoming_data, as_list=False, flat=False, include_missing=False ):
        """
        Transform the incoming data according to
        the defined data mapping.
        """
        # TODO: this should be cleaned up to avoid the pylint warning
        # pylint: disable=too-many-nested-blocks
        if self.is_selected( incoming_data ):
            outgoing_data = [] if as_list else {}
            for m in self.get_mapping():
                field = str( m.get_field() )
                try:
                    val = m.get_value( incoming_data )

                    if as_list:
                        # Groups are a list of ids and are handled separetely
                        if field == 'groups':
                            if flat:
                                groups = []
                                for group_id in val:
                                    try:
                                        groups.append(ContactGroup.objects.get(id=group_id).name)
                                    except ContactGroup.DoesNotExist:
                                        groups.append('Unknown group: %d' % group_id)

                                outgoing_data.append(groups)
                            else:
                                outgoing_data.append(val)
                        else:
                            outgoing_data.append( ", ".join( val ) if isinstance( val, list ) and flat else val )
                    else:
                        if field in outgoing_data:
                            outgoing_data[field] += val
                        else:
                            outgoing_data[field] = val
                except ColumnDoesNotExists:
                    if include_missing:
                        if as_list:
                            outgoing_data.append( 'ERROR' )
                        else:
                            if field not in outgoing_data:
                                outgoing_data[field] = 'ERROR'
            return outgoing_data
        return None

    def get_importer( self, filename ):
        """
        """
        from djangoplicity.contacts.importer import CSVImporter, ExcelImporter

        dummy_base, ext = os.path.splitext( filename )
        extmap = {
            '.xls': ExcelImporter,
            '.csv': CSVImporter,
        }

        try:
            importercls = extmap[ext.lower()]
        except KeyError:
            raise DataImportError( "Unsupported file format '%s'." % ext )

        return importercls( filename=filename )

    def extract_data( self, filename ):
        """
        Extract data from an import file. Supported formats
        are currently, CSV and Excel (.xls).
        """
        importer = self.get_importer( filename )
        return ( self.parse_row( row ) for row in importer )

    def preview_data( self, filename ):
        """
        Preview the data file according to the defined
        import template.
        """
        data_table = []
        i = 1  # Excel start with header at row 1
        for row in self.get_importer( filename ):
            i += 1
            data = self.parse_row( row, as_list=True, flat=True, include_missing=True )
            if data:
                data.insert( 0, i )
                data_table.append( data )
        return ( ["Row"] + self.get_mapping(), data_table )

    def _get_review_form_data(self, mapping, contact=None):
        '''
        Return a dict with 'type', 'id' and 'value' based on
        the type of the given field name (from the mapping)
        '''
        django_field = mapping.get_django_field()

        if contact and hasattr(contact, mapping.field):
            value = getattr(contact, mapping.field)
        else:
            value = None

        if django_field.__class__ == models.fields.CharField:
            type_ = 'textinput'
        else:
            type_ = 'text'

        return {
            'type': type_,
            'id': '%s_%s' % (id, mapping.field),
            'value': value,
            'name': mapping.field,
            }

    def review_data( self, filename, duplicate_contacts, imported_contacts):
        """
        Review the data file according to the defined import template,
        displaying the potential duplicates
        """
        from djangoplicity.contacts.forms import ContactForm
        imported = []
        new = []
        duplicates = []
        mapping = self.get_mapping()

        i = 1  # Excel start with header at row 1
        for data in self.extract_data( filename ):
            i += 1
            if data:
                try:
                    id = imported_contacts[unicode(i)]
                    contact = {
                        'row': unicode(i),
                        'contact_link': '<a href="%s">%s</a>' %
                        (url_reverse('admin:contacts_contact_change', args=[id]), id),
                        'data': data,
                    }
                    # Check that the contact still exists:
                    try:
                        Contact.objects.get(id=id)
                    except Contact.DoesNotExist:
                        contact['contact_link'] = '<span style="color: red;">Contact %d disappeared!</span>' % id

                    imported.append(contact)

                except KeyError:
                    # Create a new contact (without saving it)
                    # to generate the form
                    record = {'row': unicode(i), 'form': ContactForm(initial=data, prefix='%d_new' % i)}
                    # Get the list of group names from the import data
                    new_groups = []
                    if 'groups' in data:
                        new_groups = [ ContactGroup.objects.get(id=x).name for x in data['groups'] ]

                    if unicode(i) in duplicate_contacts:
                        dups = []
                        #  Duplicates dict is using 0 based arrays
                        #  We loop over the IDs, stored in reverse score order:
                        for id, score in sorted(duplicate_contacts[unicode(i)].iteritems(),
                                                key=lambda(k, v): (v, k), reverse=True):

                            try:
                                contact = Contact.objects.get(id=id)
                                # Create a list of extra fields to display in the form
                                fields = ('<a href="%s">%s</a> (%.2f)' % (url_reverse('admin:contacts_contact_change',
                                                args=[id]), id, score),)
                                if 'groups' in data:
                                    # Get the list of groups from the contact and the Import data:
                                    groups = data['groups'] + list(contact.groups.all().values_list('id', flat=True))
                                else:
                                    groups = list(contact.groups.all().values_list('id', flat=True))
                                form = ContactForm(instance=contact, initial={'groups': groups}, prefix='%d_update_%s' % (i, id))
                            except Contact.DoesNotExist:
                                fields = ('<span style="color: red">Contact %s disappeared! Please re-run deduplication</span>' % id,)
                                form = None

                            dups.append({
                                'fields': fields,
                                'contact_id': id,
                                'contact': contact,
                                'form': form,
                            })
                        record['duplicates'] = dups
                        record['new_groups'] = new_groups
                        duplicates.append(record)
                    else:
                        # New contact
                        record['new_groups'] = new_groups
                        new.append(record)

        return (mapping, imported, new, duplicates)

    def direct_import_data(self, filename):
        """
        Import the data file according to the defined import template
        without duplicate handling
        """
        if self.tag_import:
            import_grp, _created = ContactGroup.objects.get_or_create( name='Import %s at %s' % ( self.name, datetime.now().replace( microsecond=0 ) ) )
        else:
            import_grp = None

        extra_groups = list( self.extra_groups.all().values_list( 'name', flat=True ) )
        _frozen_set = set( self.frozen_groups.all().values_list( 'pk', flat=True ) )

        i = 0
        for data in self.extract_data( filename ):
            if data:
                i += 1
                if 'groups' in data and data['groups']:
                    data['groups'] += extra_groups
                else:
                    data['groups'] = extra_groups

                # Add import group if needed
                if import_grp:
                    data['groups'].append( import_grp.name )

                obj = Contact.create_object( **data )
                logger.info( "Creating contact %s", obj.pk )

    def import_data( self, import_contacts ):
        """
        Import the give data according to the given import template
        import contact is a dict:
        {'line_number ': {
            'target: 'new' or 'id'  # Create new contact or update 'id'
            'form': {}              # form for give contact
        }, }
        """
        if self.tag_import:
            import_grp, dummy_created = ContactGroup.objects.get_or_create( name='Import %s at %s' % ( self.name, datetime.now().replace( microsecond=0 ) ) )
        else:
            import_grp = None

        extra_groups = list( self.extra_groups.all().values_list( 'name', flat=True ) )
        # Add import group if needed
        if import_grp:
            extra_groups.append( import_grp.name )

        imported_contacts = {}

        for line_number, contact_data in import_contacts.iteritems():
            form = contact_data['form']
            if not form:
                continue
            contact = form.save()
            if extra_groups:
                extra_groups = list(ContactGroup.objects.filter( name__in=extra_groups ))
                contact.groups.add( *extra_groups )
                for g in extra_groups:
                    contact_added.send(sender=contact.__class__, group=g, contact=contact)
            imported_contacts[line_number] = contact.pk

        return imported_contacts

    def prepare_import( self, filename ):
        """
        Search for a and returns a list of potential duplicates in the file.
        """

        if self.duplicate_handling != 'smart':
            return

        duplicate_contacts = {}
        search_space = deduplication.contacts_search_space()

        i = 1  # Excel start with header at row 1
        for data in self.extract_data( filename ):
            i += 1
            if data:
                dups = deduplication.find_duplicates(data, search_space)
                if not dups:
                    continue

                # Create a dict of duplicate score with Contact id as key
                keys = {}
                for dup in dups:
                    keys[dup[1]['contact_object'].pk] = dup[0]

                duplicate_contacts[i] = keys

        return duplicate_contacts


CONTACTS_FIELDS = [
    ( 'title', 'Title' ),
    ( 'first_name', 'First name' ),
    ( 'last_name', 'Last name' ),
    ( 'position', 'Position' ),
    ( 'organisation', 'Organisation' ),
    ( 'department', 'Department' ),
    ( 'street_1', 'Street 1' ),
    ( 'street_2', 'Street 2' ),
    ( 'zip', 'ZIP code' ),
    ( 'city', 'City' ),
    ( 'country', 'Country' ),
    ( 'region', 'Region' ),
    ( 'tax_code', 'Tax Code' ),
    ( 'phone', 'Phone' ),
    ( 'website', 'Website' ),
    ( 'social', 'Social' ),
    ( 'email', 'Email' ),
    ( 'language', 'Language' ),
    ( 'groups', 'Contact groups' ),
    ( 'pk', 'Id' ),
]
# + Field.field_options() # Todo: needs to be dynamic since if extra field is added, then it will require server restart to have the list updated.


class ImportMapping( models.Model ):
    """
    Defines a mapping from a column in an CSV or Excel file to a contact model field.
    """
    template = models.ForeignKey( ImportTemplate )
    header = models.CharField( max_length=255 )
    field = models.SlugField( max_length=255 )
    group_separator = models.CharField( max_length=20, default='', blank=True )

    _country_cache = None
    _groupmap_cache = None

    def save( self, *args, **kwargs ):
        # Clear mapping cache on import template
        super( ImportMapping, self ).save( *args, **kwargs )
        self.template.clear_mapping_cache()

    def clear_groupmap_cache( self ):
        """
        Clear group map cache if requested/
        """
        self._groupmap_cache = None

    def get_field( self ):
        """
        """
        trail = self.field.split( "__" )
        return trail[0]

    def get_django_field(self):
        '''
        Returns the actual field used in the Contact model
        matching the ImportMapping field
        '''
        return Contact._meta.get_field(self.field)

    def get_country_value( self, value ):
        """
        """
        from djangoplicity.contacts.deduplication import similar_text

        # Make country cache if it doesn't exists
        if ImportMapping._country_cache is None:
            ImportMapping._country_cache = { 'iso': {}, 'name': {} }
            for c in Country.objects.all():
                ImportMapping._country_cache['iso'][c.iso_code.lower()] = c.pk
                ImportMapping._country_cache['name'][c.name.lower()] = c.pk

        if not isinstance(value, unicode):
            value = unicode(value)
        value = value.lower().strip()
        if len( value ) == 2 and value in ImportMapping._country_cache['iso']:
            return ImportMapping._country_cache['iso'][value]
        elif value in ImportMapping._country_cache['name']:
            return ImportMapping._country_cache['name'][value]
        else:
            for k, v in ImportMapping._country_cache['name'].items():
                if similar_text( k, value ):
                    logger.info( "similar %s = %s", k, value )
                    return v

            for iso, exps in ISO_EXPANSION.items():
                for e in exps:
                    if similar_text( unicode( value ), e ):
                        return ImportMapping._country_cache['iso'][iso.lower()]
            return None

    def get_region_value(self, value, country_id):
        if not value:
            return None
        queryset = Region.objects.filter(country=country_id) if country_id else Region.objects.all()
        region = queryset.filter(code__iexact=value).first()
        if not region:
            region = queryset.filter(Q(name__istartswith=value) | Q(local_name__istartswith=value)).first()
        return region.pk if region else None

    def get_groups_value( self, value ):
        """
        """
        if self.field == 'groups' and self.group_separator:
            values = [x.strip() for x in value.split( self.group_separator )]
        else:
            values = [value.strip()]

        # Cache the mapping from values to contact groups so future queries are fast.
        if self._groupmap_cache is None:
            self._groupmap_cache = dict( ImportGroupMapping.objects.filter( mapping=self ).values_list( 'value', 'group__id' ) )

        return filter( lambda x: x, map( lambda x: self._groupmap_cache.get( x, None ), values ) )

    def get_value( self, data ):
        """
        Get the value for the model field. For most fields, this is just
        the direct value, however for groups and country there are special
        processing going on.
        """
        try:
            val = data[self.header]
            if self.field:
                trail = self.field.split("__")
                if trail[0] == 'groups':
                    return self.get_groups_value(val)
                if trail[0] == 'country':
                    return self.get_country_value(val)
                if trail[0] == 'region':
                    # Try to get the country from the imported data to filter Regions inside that country
                    country = data.get('country', None) or data.get('Country', None)
                    country_id = self.get_country_value(country)
                    return self.get_region_value(val, country_id)
                if trail[0] == 'language':
                    if not isinstance(val, unicode):
                        val = unicode(val)
                    return val.lower()
            # Excel uses float for many numbers.
            if isinstance( val, float ) and val - int( val ) == 0.0:
                return int(val)
            return val
        except KeyError:
            raise ColumnDoesNotExists( self.header )


class ImportSelector( models.Model ):
    """
    Defines a selector for an import template. This allows
    the template to only import certain rows (e.g. if a specific
    column contains an x in a cell it will be imported).
    """
    template = models.ForeignKey( ImportTemplate )
    header = models.CharField( max_length=255 )
    value = models.CharField( max_length=255 )
    case_sensitive = models.BooleanField( default=False )

    def save( self, *args, **kwargs ):
        # Clear selector cache on import template
        super( ImportSelector, self ).save( *args, **kwargs )
        self.template.clear_selector_cache()

    def get_value( self, data ):
        try:
            return data[self.header]
        except KeyError:
            raise ColumnDoesNotExists( self.header )

    def is_selected( self, data ):
        try:
            val = self.get_value( data )
            compare_val = unicode( self.value ).strip() if self.case_sensitive else unicode( self.value ).strip().lower()
            if val:
                val = unicode( val ).strip() if self.case_sensitive else unicode( val ).strip().lower()

            return val == compare_val
        except ColumnDoesNotExists:
            return False


class ImportGroupMapping( models.Model ):
    """
    Defines a mapping from values to groups.
    """
    mapping = models.ForeignKey( ImportMapping, limit_choices_to={ 'field': 'groups' } )
    value = models.CharField( max_length=255 )
    group = models.ForeignKey( ContactGroup )

    def save( self, *args, **kwargs ):
        # Make sure that the value is stripped (extra spaces would make
        # the string match to fail
        self.value = self.value.strip()
        # Clear group map cache on import mapping
        super( ImportGroupMapping, self ).save( *args, **kwargs )
        self.mapping.clear_groupmap_cache()


upload_dir = os.path.join( settings.SHARED_DIR, 'contacts_import' )
upload_fs = FileSystemStorage( location=upload_dir, base_url=None )


def handle_uploaded_file( instance, filename ):
    """
    Generate a new name for an uploaded filed.

    Pattern used: <template name>-<uuid>.<original extension>
    """
    dummy_base, ext = os.path.splitext( filename )

    import uuid
    name = "%s%s%s" % ( "%s_" % instance.template.name if instance.template else '', str( uuid.uuid1() ), ext.lower() )

    return name


DEDUPLICATION_STATUS = [
    ( 'new', 'New' ),
    ( 'processing', 'Processing' ),
    ( 'review', 'Review' ),
    ( 'imported', 'Imported' ),
]


class Import( models.Model ):
    """
    Import job - stores an excel file and selects which import template to use when importing
    the data.

    Allow for previewing of the data mapping and executing the import. An import can only be run once
    to prevent it from accidentally be imported twice.
    """
    template = models.ForeignKey( ImportTemplate )
    data_file = models.FileField( upload_to=handle_uploaded_file, storage=upload_fs )
    status = models.CharField( max_length=20, choices=DEDUPLICATION_STATUS, help_text='', default='new' )
    created = models.DateTimeField( auto_now_add=True )
    last_modified = models.DateTimeField( auto_now=True )
    last_deduplication = models.DateTimeField( null=True )
    imported_contacts = models.TextField( blank=True )
    duplicate_contacts = models.TextField( blank=True )

    def preview_data( self ):
        """
        Generate a preview of the data mapping for this import. The data
        will be used as the basis for the import.
        """
        return self.template.preview_data( self.data_file.path )

    def review_data( self ):
        """
        Generate a preview of the data mapping for this import including the
        poential duplicates. The data will be used as the basis for the import.
        """
        duplicate_contacts = json.loads(self.duplicate_contacts) if self.duplicate_contacts else {}
        imported_contacts = json.loads(self.imported_contacts) if self.imported_contacts else {}
        return self.template.review_data( self.data_file.path, duplicate_contacts, imported_contacts )

    def direct_import_data(self):
        if self.status != 'imported':
            self.template.direct_import_data(self.data_file.path)
            self.status = 'imported'
            return True
        return False

    def import_data( self, import_contacts ):
        """
        Run the data import. Normally this should be executed in a background task
        as it might be a long running task.

        Also, the user is responsible to save the import object afterwards to ensure
        that it's marked as done.
        """
        imported_contacts = self.template.import_data( import_contacts )

        # Save the dict of imported contacts
        if self.imported_contacts:
            tmp = json.loads(self.imported_contacts)
        else:
            tmp = {}
        tmp.update(imported_contacts)
        self.imported_contacts = json.dumps(tmp)
        return True

    def prepare_import( self ):
        """
        Look for potential duplicates in the import. Normally this should be
        executed in a background task as it might be a long running task.

        Also, the user is responsible to set the import status and save it
        afterwards to ensure that it's marked as done.
        """
        dups = self.template.prepare_import( self.data_file.path )
        if dups:
            self.duplicate_contacts = json.dumps(dups)
            self.save()
        return True

    @classmethod
    def pre_delete_callback( cls, sender, instance=None, **kwargs ):
        """
        Delete any file stored on the object, when the object is being deleted.
        """
        try:
            instance.data_file.delete()
        except Exception:
            pass


class Deduplication(models.Model):
    '''
    Deduplication job
    '''
    status = models.CharField(max_length=20, choices=DEDUPLICATION_STATUS,
                help_text='', default='new')
    last_deduplication = models.DateTimeField(null=True)
    duplicate_contacts = models.TextField(blank=True)
    deduplicated_contacts = models.TextField( blank=True )
    groups = models.ManyToManyField(ContactGroup, blank=True)
    max_display = models.IntegerField(default=25,
                    help_text='Maximum number of duplicates to display at once.')
    min_score_display = models.FloatField(default=0.7,
                            help_text='Only display duplicates with score above this score.')

    def run(self):
        '''
        Look for potential duplicates in the given groups (if any) or in the
        whole Contatcs DB. Normally this should be executed in a background
        task as it might be a long running task.

        Also, the user is responsible to set the import status and save it
        afterwards to ensure that it's marked as done.
        '''

        duplicate_contacts = {}
        search_space = deduplication.contacts_search_space()

        if self.groups.all():
            contacts = Contact.objects.filter(groups__in=self.groups.all()).select_related('country').distinct()
        else:
            contacts = Contact.objects.all().select_related('country')

        # Get set of known deduplicated contacts
        deduplicated_contacts = set()
        for d in Deduplication.objects.filter(status='review'):
            if d.deduplicated_contacts:
                deduplicated_contacts.update(json.loads(d.deduplicated_contacts))

        for contact in contacts:
            # Remove the current contact from the search space:
            del search_space[contact.id]

            dups = deduplication.find_duplicates(contact.get_data(), search_space)

            if not dups:
                continue

            # Create a dict of duplicate score with Contact id as key
            keys = {}
            for dup in dups:
                duplicate_id = dup[1]['contact_object'].pk
                if '%s_%s' % (contact.pk, duplicate_id) in deduplicated_contacts or \
                    '%s_%s' % (duplicate_id, contact.pk) in deduplicated_contacts:
                    # This pair was already deduplicated
                    logger.info('Ignore deduplicated: %s, %s', contact.pk, duplicate_id)
                    continue
                keys[duplicate_id] = dup[0]

            if keys:
                duplicate_contacts[contact.pk] = keys
                message = ''
                for key in keys:
                    message += '%d (%.2f), ' % (key, keys[key])
                    logger.info("Found duplicates for deduplication %s: %s", self.pk, message)

        # Deduplications can take many hours to complete, and we risk running
        # into a 'MySQL server has gone away' error, so we close the DB
        # connection, it will be automatically re-opened if necessary
        connection.close()

        if duplicate_contacts:
            self.duplicate_contacts = json.dumps(duplicate_contacts)
            self.save()

        return True

    def review_data( self, page=1 ):
        """
        Returns the view of the potential found duplicates as well as the total
        number of duplicates
        Only return max_display duplicates at a time
        """
        from djangoplicity.contacts.forms import ContactForm
        duplicate_contacts = json.loads(self.duplicate_contacts) if self.duplicate_contacts else {}

        # Load previously deduplicated contacts
        deduplicated_contacts = set()
        if self.deduplicated_contacts:
            deduplicated_contacts.update(json.loads(self.deduplicated_contacts))

        # Remove duplicated contacts
        duplicate_contacts = dict([
            (k, v) for k, v in duplicate_contacts.items()
            if '%s_%s' % (k, k) not in deduplicated_contacts
        ])

        total_duplicates = len(duplicate_contacts)

        # Paginate
        start = (page - 1) * self.max_display
        end = page * self.max_display
        duplicate_contacts = dict([
            (k, v) for k, v in duplicate_contacts.items()
        ][start:end])

        duplicates = []

        # Prefetch Contacts
        keys = []
        for k, v in duplicate_contacts.items():
            keys.append(k)
            keys += v.keys()
        contacts = Contact.objects.filter(pk__in=keys).prefetch_related(
            'groups', 'country').select_related('country', 'region')
        contacts = dict([(str(c.pk), c) for c in contacts])

        for contact_id in duplicate_contacts:
            try:
                contact = contacts[contact_id]
                fields = ('<a href="%s">%s</a>' % (url_reverse('admin:contacts_contact_change',
                                args=[contact_id]), contact_id), )
                form = ContactForm(instance=contact, prefix='%s_%s' % (contact_id, contact_id))
            except KeyError:
                fields = ('<span style="color: red;">Contact %s disappeared!</span>' % contact_id, )
                contact = None
                form = None

            record = {
                'fields': fields,
                'contact_id': contact_id,
                'contact': contact,
                'form': form,
            }

            dups = []

            for pk, score in sorted(duplicate_contacts[contact_id].iteritems(),
                    key=lambda(k, v): (v, k), reverse=True):

                if score < self.min_score_display:
                    continue

                try:
                    contact = contacts[pk]
                    # Create a list of extra fields to display in the form
                    fields = ('<a href="%s">%s</a> (%.2f)' % (url_reverse('admin:contacts_contact_change',
                                args=[pk]), pk, score),)
                    form = ContactForm(instance=contact, prefix='%s_%s' % (contact_id, pk))
                except KeyError:
                    fields = ('<span style="color: red">Contact %s disappeared! Please re-run deduplication</span>' % pk,)
                    form = None

                dups.append({
                    'fields': fields,
                    'contact_id': pk,
                    'contact': contact,
                    'form': form,
                })

            record['duplicates'] = dups

            duplicates.append(record)

        return duplicates, total_duplicates

    def deduplicate_data(self, update, delete, ignore):
        '''
        Update, delete and ignore the given contacts
        '''
        resultlist = {'errors': [], 'messages': []}
        deduplicated_contacts = []

        for contact_id in delete:
            try:
                contact = Contact.objects.get(id=contact_id.split('_')[1])
                contact.delete()
                resultlist['messages'].append('Deleted Contact "%s"' % contact_id)
            except Contact.DoesNotExist:
                resultlist['errors'].append(
                        'Couldn\'t delete Contact "%s", Contact doesn\'t exist!' % contact_id)
            deduplicated_contacts.append(contact_id)

        for contact, data in update.iteritems():
            form = data['form']
            form.save()
            contact_id = contact.split('_')[1]
            resultlist['messages'].append('Updated Contact <a href="%s">%s</a>' %
                    (url_reverse('admin:contacts_contact_change', args=[contact_id]), contact_id))

            deduplicated_contacts.append(contact)

        for contact in ignore:
            resultlist['messages'].append('Ignored Contact "%s"' % contact)
            deduplicated_contacts.append(contact)

        if deduplicated_contacts:
            old = json.loads(self.deduplicated_contacts) if self.deduplicated_contacts else []
            self.deduplicated_contacts = json.dumps(deduplicated_contacts + old)
            self.save()

        return resultlist


pre_delete.connect( Import.pre_delete_callback, sender=Import )

# Connect signals to clear the action cache
post_delete.connect( ContactGroupAction.clear_cache, sender=ContactGroupAction )
post_save.connect( ContactGroupAction.clear_cache, sender=ContactGroupAction )
post_delete.connect( ContactGroupAction.clear_cache, sender=Action )
post_save.connect( ContactGroupAction.clear_cache, sender=Action )
post_delete.connect( ContactGroupAction.clear_cache, sender=ContactGroup )
post_save.connect( ContactGroupAction.clear_cache, sender=ContactGroup )

# Connect signals needed to send out contact_added/contact_removed signals.
pre_delete.connect( Contact.pre_delete_callback, sender=Contact )
pre_save.connect( Contact.pre_save_callback, sender=Contact )
post_save.connect( Contact.post_save_callback, sender=Contact )

# Connect signals to propagate Contact.group_order values
pre_delete.connect( ContactGroup.pre_delete_callback, sender=ContactGroup )
post_delete.connect( ContactGroup.post_delete_callback, sender=ContactGroup )
pre_save.connect( ContactGroup.pre_save_callback, sender=ContactGroup )
post_save.connect( ContactGroup.post_save_callback, sender=ContactGroup )

# Connect signals handling the execution of actions
contact_added.connect( ContactGroupAction.contact_added_callback, sender=Contact )
contact_removed.connect( ContactGroupAction.contact_removed_callback, sender=Contact )
contact_updated.connect( ContactGroupAction.contact_updated_callback, sender=Contact )
