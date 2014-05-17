from django.conf.urls import *

from cyder.cydns.urls import cydns_urls
from cyder.cydns.domain.views import domain_detail, get_all_domains, search


urlpatterns = cydns_urls('domain') + patterns(
    '',
    url(r'^search/', search, name='domain-search'),
    url(r'^get_all_domains/$', get_all_domains, name='get-all-domains'),
    url(r'(?P<pk>[\w-]+)/$', domain_detail, name='domain-detail'),
)
