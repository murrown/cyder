from django.conf.urls import *

from cyder.cydns.urls import cydns_urls


urlpatterns = cydns_urls('sshfp')
