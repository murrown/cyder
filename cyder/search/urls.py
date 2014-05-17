from django.conf.urls import patterns, url
from django.views.generic.base import TemplateView

from search.views import search_ajax, search_dns_text, get_zones_json
from search.views import search

urlpatterns = patterns(
    '',
    url(r'^search_ajax', search_ajax),
    url(r'^search_dns_text', search_dns_text),
    url(r'^get_zones_json', get_zones_json),
    url(r'^help/$', TemplateView.as_view(template_name='search/search_help.html'), name='search-help'),
    url(r'^$', search, name='search'),
)
