from gettext import gettext as _

from django.db import models
from django.db.models import get_model
from django.core.exceptions import ValidationError, ObjectDoesNotExist

from cyder.base.utils import transaction_atomic
from cyder.cydns.models import CydnsRecord, LabelDomainMixin
from cyder.cydns.validation import validate_fqdn
from cyder.cydns.search_utils import smart_fqdn_exists



class CNAME(LabelDomainMixin, CydnsRecord):
    """
    CNAMES can't point to an any other records. Said another way,
    CNAMES can't be at the samle level as any other record. This means
    that when you are creating a CNAME every other record type must be
    checked to make sure that the name about to be taken by the CNAME
    isn't taken by another record. Likewise, all other records must
    check that no CNAME exists with the same name before being created.

    >>> CNAME(label = label, domain = domain, target = target)

    """

    pretty_type = 'CNAME'

    # TODO cite an RFC for that ^ (it's around somewhere)
    id = models.AutoField(primary_key=True)
    target = models.CharField(max_length=100, validators=[validate_fqdn])
    template = _("{bind_name:$lhs_just} {ttl:$ttl_just}  "
                 "{rdclass:$rdclass_just} "
                 "{rdtype:$rdtype_just} {target:$rhs_just}.")

    search_fields = ('fqdn', 'target')
    sort_fields = ('fqdn', 'target')

    class Meta:
        app_label = 'cyder'
        db_table = 'cname'
        unique_together = ('label', 'domain', 'target')

    def __unicode__(self):
        return u'{} CNAME {}'.format(self.fqdn, self.target)

    def details(self):
        """For tables."""
        data = super(CNAME, self).details()
        data['data'] = [
            ('Label', 'label', self.label),
            ('Domain', 'domain', self.domain),
            ('Target', 'target', self.target)
        ]
        return data

    @staticmethod
    def eg_metadata():
        """EditableGrid metadata."""
        return {'metadata': [
            {'name': 'label', 'datatype': 'string', 'editable': True},
            {'name': 'domain', 'datatype': 'string', 'editable': True},
            {'name': 'target', 'datatype': 'string', 'editable': True},
        ]}

    @property
    def rdtype(self):
        return 'CNAME'

    @transaction_atomic
    def save(self, *args, **kwargs):
        self.full_clean()

        super(CNAME, self).save(*args, **kwargs)

    def clean(self, *args, **kwargs):
        super(CNAME, self).clean(*args, **kwargs)
        if self.fqdn == self.target:
            raise ValidationError("CNAME loop detected.")
        self.check_roundrobin_condition()
        self.check_SOA_condition()
        self.existing_node_check()

    def check_roundrobin_condition(self):
        """
        Allow CNAMEs with the same name iff they share the same container.
        """
        existing = (CNAME.objects.filter(label=self.label, domain=self.domain)
                                 .exclude(ctnr=self.ctnr))
        if existing.exists():
            raise ValidationError("Cannot create CNAME because another CNAME "
                                  "with the name %s.%s already exists in a "
                                  "different container." % (self.label,
                                                            self.domain.name))

    def check_SOA_condition(self):
        """
        We need to check if the domain is the root domain in a zone.
        If the domain is the root domain, it will have an soa, but the
        master domain will have no soa (or it will have a a different
        soa).
        """
        try:
            self.domain
        except ObjectDoesNotExist:
            return  # Validation will fail eventually
        if not self.domain.soa:
            return
        root_domain = self.domain.soa.root_domain
        if root_domain is None:
            return
        if self.fqdn == root_domain.name:
            raise ValidationError(
                "You cannot create a CNAME whose left hand side is at the "
                "same level as an SOA"
            )

    def existing_node_check(self):
        """
        Make sure no other nodes exist at the level of this CNAME.

            "If a CNAME RR is present at a node, no other data should be
            present; this ensures that the data for
            a canonical name and its aliases cannot be different."

            -- `RFC 1034 <http://tools.ietf.org/html/rfc1034>`_

        For example, this would be bad::

            FOO.BAR.COM     CNAME       BEE.BAR.COM

            BEE.BAR.COM     A           128.193.1.1

            FOO.BAR.COM     TXT         "v=spf1 include:foo.com -all"

        If you queried the ``FOO.BAR.COM`` name, the class of the record
        that would be returned would be ambiguous.



        .. note::
            The following records classes are checked.
                * :class:`AddressRecord` (A and AAAA)
                * :class:`SRV`
                * :class:`TXT`
                * :class:`MX`
        """
        qset = smart_fqdn_exists(self.fqdn, cn=False)
        if qset:
            objects = qset.all()
            raise ValidationError(
                "Objects with this name already exist: {0}".format(
                    ', '.join(unicode(object) for object in objects))
            )

        MX = get_model('cyder', 'MX')
        if MX.objects.filter(server=self.fqdn):
            raise ValidationError(
                "RFC 2181 says you shouldn't point MX records at CNAMEs and "
                "an MX points to this name!"
            )

        PTR = get_model('cyder', 'PTR')
        if PTR.objects.filter(fqdn=self.fqdn):
            raise ValidationError("RFC 1034 says you shouldn't point PTR "
                                  "records at CNAMEs, and a PTR points to"
                                  " %s!" % self.fqdn)

        # Should SRV's not be allowed to point to a CNAME? /me looks for an RFC
