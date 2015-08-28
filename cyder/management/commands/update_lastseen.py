from activate import activate
activate()

from django.conf import settings
from django.core.management.base import BaseCommand
from cyder.models import StaticInterface, DynamicInterface, Range
from cyder.management.commands.lib.utilities import ip2long
from cyder.cydhcp.constants import ALLOW_ANY, STATIC, DYNAMIC
from datetime import datetime
from os import lstat
import re

regex = re.compile("(\w+)\s+(\d+)\s+(\d+):(\d+):(\d+)\s\w+ dhcpd: DHCPACK on "
                   "(\d+\.\d+\.\d+\.\d+) to ([0-9a-fA-F:]{17})")

months = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
          "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}

now = datetime.now()
nowyear = now.year
nowmonth = now.month

wireless_range = Range.objects.get(start_lower=ip2long("10.255.255.255"))


def is_wireless_registration(arange):
    if 1339 <= arange.pk <= 1342:
        return True
    return False


def log(msg, loglevel=0):
    print msg


def update_interface(interface, timetuple):
    month, day, hour, minute, second = timetuple
    month = months[month.lower()]
    year = nowyear
    if month > nowmonth:
        year -= 1
    day, hour, minute, second = tuple(map(int, [day, hour, minute, second]))
    dt = datetime(year, month, day, hour, minute, second, 0)
    interface.__class__.objects.filter(pk=interface.pk).update(last_seen=dt)
    return


def parse_line(line):
    match = regex.match(line)
    if match:
        month, day, hour, minute, second, ip_str, mac = match.groups()
        timetuple = (month, day, hour, minute, second)
        try:
            ip_long = ip2long(ip_str)
            myrange = Range.objects.get(
                ip_type="4", start_lower__lte=ip_long,
                end_lower__gte=ip_long)
        except Range.DoesNotExist:
            log("No such range exists.")
            return

        if is_wireless_registration(myrange):
            myrange = wireless_range
        elif myrange.allow == ALLOW_ANY:
            return

        if myrange.range_type == STATIC:
            try:
                si = StaticInterface.objects.get(ip_str=ip_str)
                update_interface(si, timetuple)
                return
            except StaticInterface.DoesNotExist:
                pass

        if myrange.range_type != DYNAMIC:
            log("Appropriate range is not dynamic.")
            return

        try:
            di = DynamicInterface.objects.get(mac=mac, range=myrange)
            update_interface(di, timetuple)
        except DynamicInterface.DoesNotExist:
            log("Dynamic interface matching MAC and range does not exist.")
            return


def read_and_update(filename=None):
    oldname, seekaddr, oldmodified = None, 0, None
    stopfile = open(settings.LASTSEEN_STOPFILE, "a+")
    stopfile.close()
    stopfile = open(settings.LASTSEEN_STOPFILE, "rw+")
    for line in stopfile.readlines():
        line = line.strip()
        if not line or line[0] == '#':
            continue
        if "STOP" in line:
            log("Update aborted because an update is already in progress.")
            return
        oldname, seekaddr, oldmodified = line.split()
        seekaddr = int(seekaddr, 0x10)
        oldmodified = int(oldmodified)
    stopfile.close()

    if filename is None:
        filename = oldname
    if filename is None:
        raise ValueError("No log file specified.")

    modified = int(lstat(filename).st_mtime)
    if oldmodified is not None and modified != oldmodified:
        seekaddr = 0

    stopfile = open(settings.LASTSEEN_STOPFILE, "w+")
    stopfile.write("STOP\n")
    stopfile.write("%s %x %s\n" % (filename, seekaddr, modified))
    stopfile.close()

    f = open(filename)
    f.seek(seekaddr)
    while True:
        line = f.readline()
        if not line or line[-1] != "\n":
            break
        if "DHCPACK on" in line:
            parse_line(line)
        seekaddr = f.tell()
    f.close()

    stopfile = open(settings.LASTSEEN_STOPFILE, "w+")
    stopfile.write("%s %x %s\n" % (filename, seekaddr, modified))
    stopfile.close()


class Command(BaseCommand):
    def handle(self, *args, **options):
        if args:
            filename = args[0]
        else:
            filename = None
        read_and_update(filename)
