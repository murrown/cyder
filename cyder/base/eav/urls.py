from django.conf.urls import patterns, url

from cyder.base.eav.views import search


urlpatterns = patterns(
    '',
    url(r'^search/', search, name='eav-search'))
