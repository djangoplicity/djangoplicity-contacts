# -*- coding: utf-8 -*-
# Import all admin interfaces we need
import django.contrib.sites.admin
from djangoplicity.contrib.admin.discover import autoregister
from djangoplicity.contrib.admin.sites import AdminSite
from django.contrib.sites.models import Site
from django.contrib.sites.admin import SiteAdmin
from django.contrib.redirects.models import Redirect
from django.contrib.redirects.admin import RedirectAdmin
import importlib
import djangoplicity.contacts.admin

# Register each applications admin interfaces with
# an admin site.
admin_site = AdminSite(name="admin_site")
adminlogs_site = AdminSite(name="adminlogs_site")

autoregister(admin_site, django.contrib.auth.admin)
autoregister(admin_site, django.contrib.sites.admin)

autoregister(admin_site, djangoplicity.contacts.admin)

# System admin site
autoregister(adminlogs_site, importlib.import_module('djangoplicity.actions.admin'))
autoregister(adminlogs_site, importlib.import_module('djangoplicity.admincomments.admin'))


admin_site.register(django.contrib.auth.models.User, django.contrib.auth.admin.UserAdmin)

admin_site.register(django.contrib.auth.models.Group, django.contrib.auth.admin.GroupAdmin)


adminlogs_site.register(Site, SiteAdmin)
adminlogs_site.register(Redirect, RedirectAdmin)
