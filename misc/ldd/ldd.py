#!/usr/bin/env python

import os, sys
import re, glob
from optparse import OptionParser

from elftools import __version__
from elftools.common.exceptions import ELFError
from elftools.common.py3compat import bytes2str
from elftools.elf.elffile import ELFFile
from elftools.elf.dynamic import DynamicSection
from elftools.elf.descriptions import describe_ei_class

class ReadElf(object):
    def __init__(self, file):
        """ file: stream object with the ELF file to read
        """
        self.elffile = ELFFile(file)


    def elf_class(self):
        """ Return the ELF Class
        """
        header = self.elffile.header
        e_ident = header['e_ident']
        return describe_ei_class(e_ident['EI_CLASS'])

    def dynamic_dt_needed(self):
        """ Return a list of the DT_NEEDED
        """
        dt_needed = []
        for section in self.elffile.iter_sections():
            if not isinstance(section, DynamicSection):
                continue

            for tag in section.iter_tags():
                if tag.entry.d_tag == 'DT_NEEDED':
                    dt_needed.append(bytes2str(tag.needed))
                    #sys.stdout.write('\t%s\n' % bytes2str(tag.needed) )

        return dt_needed


def ldpaths(ld_so_conf='/etc/ld.so.conf'):
    """ Generate paths to search for libraries from ld.so.conf.  Recursively
        parse included files.  We assume correct syntax and the ld.so.cache
        is in sync with ld.so.conf.
    """
    with open(ld_so_conf, 'r') as path_file:
        lines = path_file.read()
    lines = re.sub('#.*', '', lines)                   # kill comments
    lines = list(re.split(':+|\s+|\t+|\n+|,+', lines)) # man 8 ldconfig

    paths = []
    include_globs = []
    for l in lines:
        if l == '':
            continue
        if l == 'include':
            f = lines[lines.index(l) + 1]
            include_globs.append(f)
            continue
        if l not in include_globs:
            paths.append(os.path.realpath(l))

    include_files = []
    for g in include_globs:
        include_files = include_files + glob.glob('/etc/' + g)
    for c in include_files:
        paths = paths + ldpaths(os.path.realpath(c))

    return list(set(paths))


def dynamic_dt_needed_paths( dt_needed, eclass, paths):
    for n in dt_needed:
        for p in paths:
            print('%s' % p + '/' + n)
    return

SCRIPT_DESCRIPTION = 'Print shared library dependencies'
VERSION_STRING = '%%prog: based on pyelftools %s' % __version__

def main():
    optparser = OptionParser(
        usage='usage: %prog <elf-file>',
        description=SCRIPT_DESCRIPTION,
        add_help_option=False, # -h is a real option of readelf
        prog='ldd.py',
        version=VERSION_STRING)
    optparser.add_option('-h', '--help',
        action='store_true', dest='help',
        help='Display this information')
    options, args = optparser.parse_args()

    if options.help or len(args) == 0:
        optparser.print_help()
        sys.exit(0)

    paths = ldpaths()
    print(paths)
    sys.exit(0)

    for f in args:
        with open(f, 'rb') as file:
            try:
                readelf = ReadElf(file)
                if len(args) > 1:
                    sys.stdout.write('%s : \n' % f)
                eclass = readelf.elf_class()
                #sys.stdout.write('\t%s\n' % eclass)
                dt_needed = readelf.dynamic_dt_needed()
                dt_needed_paths = dynamic_dt_needed_paths( dt_needed, eclass, paths)
                for n in dt_needed:
                    sys.stdout.write('\t%s\n' % n )
            except ELFError as ex:
                sys.stderr.write('ELF error: %s\n' % ex)
                sys.exit(1)

if __name__ == '__main__':
    main()