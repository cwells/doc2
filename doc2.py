#!/usr/bin/python
# -*- coding: utf-8 -*-

# --------------------------------------------------------------------------
# doc2.py
# A utility to convert Nginx XML documentation source into various formats.
# It also breaks up those documents into smaller fragments that can be
# referenced by module/name.
#
# (c) Cliff Wells, 2012  <cliff@nginx.com>
# --------------------------------------------------------------------------

from __future__ import print_function
import os, sys, errno, traceback
import logging; logging.basicConfig ()
import re, string
from glob import glob
from cStringIO import StringIO
from lxml import etree
from optparse import OptionParser
from rulesparser import RulesParser
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict


class Transformer (object):
    def __init__ (self, config):
        self._cfg = config
        self._root = None            # root element to start processing at
        self._newfile = False        # flag that a new file should be generated
        self._store = {}
        self.last_output = ''
        self.directives = [f [len ('dd_'):] for f in dir (self) if f.startswith ('dd_')]
        self._globals = {}

    def description (self):
        return self._cfg.get ('info')['description']

    def extension (self):
        return self._cfg.get ('info')['extension']

    def directory (self):
        return self._cfg.get ('info')['directory']

    def set_srcfile (self, srcfile):
        self._srcfile = srcfile

    def root (self, root):
        self._root = etree.ElementTree (root)

    def process_element (self, event, elem):
        logger = logging.getLogger (__name__)

        xpath = self._root.getpath (elem)
        match, mo = self._cfg.search (xpath)

        t = elem.text if event == 'start' else elem.tail
        if t is None: t = ''

        if match is None:
            logger.warn ('No rule matching {0}, skipping...'.format (xpath))
            return

        vars = {
            're': re,
            'string': string,
            'event': event,
            'elem': elem,
            'last_output': self.last_output,
            'match': mo,
            'regex': match,
            'xpath': xpath,
            'globals': self._globals
        }

        try:
            exec (self._cfg.obj (match, event), self._globals, vars)
        except:
            exc_type, exc_value, exc_traceback = sys.exc_info ()
            tb = traceback.extract_tb (exc_traceback)
            tb_rule, tb_lineno, _, _ = tb [1]
            print ("\nError: {3}\nRule: {0}\nEvent: {1}\nLine {2}:\n".format (match, event, tb_lineno, exc_value), file=sys.stderr)
            print ("{0}\n\n".format (self.dd_indent (self._cfg.src (match, event), indent=4)), file=sys.stderr)
            sys.exit (1)

        for directive in self._cfg.settings (match, event):
            if t is None: return
            if directive in self.directives:
                method = getattr (self, "dd_{0}".format (directive))
                t = method (t, **vars)

        if t is not None:
            self.last_output = t
        return t

    #
    # directive definitions
    #
    def dd_discard (self, t, discard=False, **_):
        if discard:
            return None
        return t

    def dd_replace (self, t, replace=None, **_):
        if replace:
            t = replace
        return t

    def dd_sanitize (self, t, sanitize=True, **_):
        if sanitize:
            t = re.sub (ur'\xa0', ' ', t)
            t = re.sub (ur'[\u201c\u201d]', '"', t)
            t = re.sub (ur'\u2019', "'", t)
            t = re.sub (ur'[\u2014\u2018]', '-', t)
        return t

    def dd_collapse (self, t, collapse=True, **_):
        ''' collapse sequences of spaces and newlines, replace non-ascii quotes
        '''
        if collapse:
            t = re.sub (ur'\s+', ' ', t)
        return t

    def dd_strip (self, t, strip=False, debug=False, **_):
        if strip:
            if debug:
                print ("{xpath}".format (**_))
                print ("\tstrip ({0})".format (t), file=sys.stderr)
            return t.strip ()
        return t

    def dd_lstrip (self, t, lstrip=False, debug=False, **_):
        if lstrip:
            if debug:
                print ("{xpath}".format (**_))
                print ("\tlstrip ({0})".format (t), file=sys.stderr)
            return t.lstrip ()
        return t

    def dd_rstrip (self, t, rstrip=False, debug=False, **_):
        if rstrip:
            if debug:
                print ("{xpath}".format (**_))
                print ("\trstrip ({0})".format (t), file=sys.stderr)
            return t.rstrip ()
        return t

    def dd_format (self, t, format = None, **_):
        '''format using Python string.format
        '''
        if format:
            return format.format (t)
        return t

    def dd_indent (self, t, indent=4, **_):
        ''' indent a region
        '''
        lines = t.split ('\n')
        return '\n'.join ([(" " * indent + l) for l in lines])

    def dd_prefix (self, t, prefix='', **_):
        ''' prepend a string
        '''
        return prefix + t

    def dd_suffix (self, t, suffix='', **_):
        ''' append a string
        '''
        return suffix + t

    def dd_combine (self, t, elem=None, event=None, combine=None, **_):
        ''' combine all identical siblings in a single, comma-separated string
        '''
        if combine:
            t = ', '.join ([c.text for c in elem.getparent().findall (combine)])
        return t

    def dd_store (self, t, store=None, debug=False, **_):
        if store:
            if debug:
                print ("{xpath}".format (**_))
                print ("\tstore ({0}, {1})".format (store, t), file=sys.stderr)
            self._store.setdefault (store, [])
            self._store [store].append (t)
            return None
        return t

    def dd_retrieve (self, t, retrieve=None, debug=False, **_):
        if retrieve:
            if retrieve in self._store:
                t = ', '.join (self._store [retrieve])
                if debug:
                    print ("{xpath}".format (**_))
                    print ("\tretrieve ({0}) = {1}".format (retrieve, t), file=sys.stderr)
                del self._store [retrieve]
        return t

    def dd_newfile (self, t, newfile=False, **_):
        self._newfile = newfile
        return t


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
verbosity_levels = dict (debug=logging.DEBUG, info=logging.INFO, warn=logging.WARN, error=logging.ERROR, crit=logging.CRITICAL)
available_formats = [os.path.splitext (f)[0] for f in glob ("*.rules")]

parser = OptionParser ()
parser.set_defaults (format='text', dest_dir='processed', pattern='*.xml', verbosity='warn', root_element='//directive', fname_attribute='name', srcdir='src')
parser.add_option ("-s", "--source", dest="srcdir", help="source directory for XML files", metavar="SRC")
parser.add_option ("-d", "--destination", dest="dest_dir", help="destination directory", metavar="DIR")
parser.add_option ("-p", "--pattern", dest="pattern", help="convert files matching pattern", metavar="PATTERN")
parser.add_option ("-r", "--root", dest="root_element", help="the root element, files will be split at every one of these", metavar="ROOT")
parser.add_option ("-a", "--attribute", dest="fname_attribute", help="files will be named for this attribute of the ROOT element", metavar="ATTR")
parser.add_option ("-f", "--format", dest="format", help="output format [{0}]".format ('|'.join (available_formats)), metavar="FORMAT")
parser.add_option ("-v", "--verbosity", dest="verbosity", help="set verbosity [{0}]".format ('|'.join (verbosity_levels)), metavar="LEVEL")
(options, args) = parser.parse_args ()

if options.format not in available_formats:
    parser.error ("Invalid output format: %s.  Use -h for help." % options.format)

try:
    options.verbosity = verbosity_levels [options.verbosity]
except KeyError:
    parser.error ("Invalid verbosity level")


logger = logging.getLogger (__name__)
logger.setLevel (options.verbosity)

rules = RulesParser ()
rules.parse (file ('%s.rules' % options.format))

parser = etree.XMLParser (dtd_validation=True)
processor = Transformer (rules)
logger.info (processor.description ())

# for each xml file
for srcfile in glob (os.path.join (options.srcdir, options.pattern)):
    tree = etree.parse (srcfile, parser)
    logger.debug ("  processing: {0}".format (os.path.basename (srcfile)))

    # for each element, in its own output file
    for directive in tree.xpath (options.root_element):
        processor.root (directive)
        output = StringIO ()

        # process element's tree
        for event, element in etree.iterwalk (directive, events=('start', 'end')):
            t = processor.process_element (event, element)
            if t is not None:
                try:
                    output.write (t)
                except UnicodeError, e:
                    print (u"\n\nUnicode error processing the following text:\n{0}\n\n".format (t), file=sys.stderr)
                    raise

            if processor._newfile:
                target_dir = os.path.join (options.dest_dir, processor.directory (), os.path.splitext (os.path.basename (srcfile))[0])
                output_file = '{0}.{1}'.format (os.path.join (target_dir, element.get (options.fname_attribute)), processor.extension ())
                logger.debug ("      -> {0}".format (output_file))

                # mkdir -p
                try:
                    os.makedirs (target_dir)
                except OSError, e:
                    if e.errno != errno.EEXIST:
                        raise

                # write output file
                fragment = file (output_file, 'w')
                fragment.write (output.getvalue ().encode ('utf-8'))
                fragment.close ()

                output = StringIO ()
                processor._newfile = False
