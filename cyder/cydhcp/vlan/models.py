from django.db import models
from django.core.exceptions import ObjectDoesNotExist

from cyder.base.mixins import ObjectUrlMixin
from cyder.cydns.domain.models import Domain

from cyder.cydhcp.keyvalue.models import KeyValue


class Vlan(models.Model, ObjectUrlMixin):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    number = models.PositiveIntegerField()

    class Meta:
        db_table = "vlan"
        unique_together = ("name", "number")

    def __str__(self):
        return "{0}".format(self.name)

    def __repr__(self):
        return "<Vlan {0}>".format(str(self))

    def details(self):
        """For tables."""
        data = super(Vlan, self).details()
        data['data'] = [
            ('Name', self),
            ('Number', self.number),
        ]
        return data

    def find_domain(self):
        """
        This memeber function will look at all the Domain objects and attempt
        to find an approriate domain that corresponds to this VLAN.
        """
        for network in self.network_set.all():
            if network.site:
                expected_name = "{0}.{1}.mozilla.com".format(
                    self.name, network.site.get_site_path())
                try:
                    domain = Domain.objects.get(name=expected_name)
                except ObjectDoesNotExist:
                    continue
                return domain.name

        return None


class VlanKeyValue(KeyValue):
    vlan = models.ForeignKey(Vlan, null=False)

    class Meta:
        db_table = "vlan_key_value"
        unique_together = ("key", "value")

    def _aa_description(self):
        return