import logging

from djangae.test import TestCase
from djangae.contrib.security.management.commands import dumpurls
from django.test import override_settings
from django.conf.urls import url


def view_with_param(request, param):
    return


urlpatterns = [
    url("^public_view/(?P<param>[\w]+)/$", view_with_param, name="named_view"),
    url("^public_view/(?P<param>[\w]+)/$", view_with_param),
]


class DumpUrlsTests(TestCase):
    def test_dumpurls(self):
        """ Test that the `dumpurls` command runs without dying. """
        logging.debug('%s', "*" * 50)
        command = dumpurls.Command()
        command.handle()

    @override_settings(
        ROOT_URLCONF=__name__,
    )
    def test_dumpurls_unnamed_urls(self):
        """ Test that the `dumpurls` command runs without dying when a named url has a parameter. """
        logging.debug('%s', "*" * 50)
        command = dumpurls.Command()
        command.handle()
