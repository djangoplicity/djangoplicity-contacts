"""test_project URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf.urls import url, include
from django.contrib import admin
from test_project.admin import adminlogs_site
from test_project.admin import admin_site
from django.conf import settings
from django.contrib.auth import views as auth_views


subpathurls = [
    # Djangoplicity Administration
    url(r'^admin/', include(admin_site.urls), {'extra_context': {'ADMIN_SITE': True}}),
    url(r'^admin/', admin.site.urls),
    url(r'^admin/cache/', include('djangoplicity.cache.urls', namespace="admincache_site", app_name="cache")),
    url(r'^admin/history/',
        include('djangoplicity.adminhistory.urls', namespace="adminhistory_site", app_name="history")),
    url(r'^admin/system/', include(adminlogs_site.urls), {'extra_context': {'ADMINLOGS_SITE': True}}),
    url(r'^admin/', include('djangoplicity.metadata.wtmlimport.urls'), {'extra_context': {'ADMIN_SITE': True}}),
    url(r'^tinymce/', include('tinymce.urls')),

    # djangoplicty contacts
    url(r'^contacts/', include('djangoplicity.contacts.urls'), {'translate': True}),

    # User authentication
    url(r'^password-reset/$', auth_views.password_reset,
        {'email_template_name': 'registration/password_reset_email.txt'}, name='password_reset'),
    url(r'^password-reset/done/$', auth_views.password_reset_done, name='password_reset_done'),
]


# Prepends the basepath in case this app is being served in a subpath by a proxy, e.g. /admin -> /public/admin
if settings.URLS_BASEPATH:
    urlpatterns = [url(r'^{}/'.format(settings.URLS_BASEPATH), include(subpathurls))]
else:
    urlpatterns = subpathurls

if settings.DEBUG_TOOLBAR:
    import debug_toolbar
    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]
