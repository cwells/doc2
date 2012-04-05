#!/usr/bin/python
# -*- coding: utf-8 -*-

# --------------------------------------------------------------------------
# doc2any.py
# A utility to convert Nginx XML documentation source into various formats.
# It also breaks up those documents into smaller fragments that can be 
# referenced by module/name.
#
# (c) Cliff Wells, 2012  <cliff@nginx.com>
# --------------------------------------------------------------------------


import os, sys, errno
import logging; logging.basicConfig ()
import re, string
from glob import glob
from cStringIO import StringIO
from lxml import etree
from optparse import OptionParser
from ConfigParser import RawConfigParser
from ordereddict import OrderedDict

def is_iterable (o): return hasattr (o, '__contains__')

class Transformer (object):
    directives = { # processed in order for each event
        'start': [ 'discard', 'replace', 'combine', 'sanitize', 'collapse', 'strip', 'format', 'prefix', 'indent', 'store' ],
        'end':   [ 'discard', 'sanitize', 'collapse', 'suffix', 'retrieve', 'newfile' ]
    }

    # _defaults = { 'collapse': True, 'sanitize': True }

    def __init__ (self, config):
        self._cfg = config
        self._root = None            # root element to start processing at
        self._newfile = False        # flag that a new file should be generated
        self._plan = OrderedDict ()  # used for debugging output
        self._store = {}

        self._defaults = self.parse_defaults (config)
        self._rules = self.parse_rules (config)
        self._compiled_rules = []
        for r in self._rules:
            self._plan [r] = {}
            try:
                self._compiled_rules.append (re.compile (r))
            except Exception, e:
                print e, r

    def __del__ (self):
        logger = logging.getLogger (__name__)
        for regex in self._plan:
            if not self._plan [regex]: continue
            logger.debug (" {0}".format (regex))
            for m, debug in sorted (self._plan [regex].items ()):
                if not debug: continue
                logger.debug ("       {0}".format (m))

    def parse_defaults (self, cfg):
        rules_defines = dict (cfg.items ('defines'))
        rules = OrderedDict ()
        code = '\n'.join (["{0}={1}".format (var, val) for var, val in cfg.items ('defaults')])
        t = string.Template (code).substitute (rules_defines)
        return compile (t, repr (type (t)), 'exec')

    def parse_rules (self, cfg):
        rules_defines = dict (cfg.items ('defines'))
        rules = OrderedDict ()
        for regex, settings in cfg.items ('rules'):
            t = string.Template (settings).substitute (rules_defines)
            rules [regex] = compile (t, repr (type (t)), 'exec')
        return rules

    def description (self):
        return self._cfg.get ('info', 'description')

    def extension (self):
        return self._cfg.get ('info', 'extension')

    def directory (self):
        return self._cfg.get ('info', 'directory')

    def set_srcfile (self, srcfile):
        self._srcfile = srcfile

    def root (self, root):
        self._root = etree.ElementTree (root)

    def process_element (self, event, elem):
        logger = logging.getLogger (__name__)

        # Look for a rule that matches the element's xpath.
        # Rules are processed in order, top down.
        # The first matching rule is selected.
        xpath = self._root.getpath (elem)
        match = None
        for _i, regex in enumerate (self._rules):
            mo = self._compiled_rules [_i].search (xpath)
            if mo:
                match = regex
                break

        t = elem.text if event == 'start' else elem.tail
        if t is None: t = ''
            
        if match is None:
            logger.warn ('No rule matching {0}'.format (xpath))
            match = 'NO RULE'

        class Proxy (object): pass
        proxy = Proxy ()
        for f in set (list.__add__ (*self.directives.values ())):
            setattr (proxy, f, getattr (self, f))

        vars = {
            're': re,
            'event': event, 
            'elem': elem, 
            'match': mo,
            'regex': match,
            'xpath': xpath,
            'do': proxy
        }

        if match:
            exec (self._defaults, {}, vars)
            exec (self._rules.get (match, ''), {}, vars)

        try:
            self._plan [match][xpath] = vars ['debug']
        except KeyError:
            pass

        processing_sequence = vars.get (event, [getattr (self, f) for f in self.directives [event] if f in vars])
        if not is_iterable (processing_sequence): processing_sequence = [processing_sequence]
        processing_sequence = [f for f in processing_sequence if f.__name__ in vars]
        
        for directive in processing_sequence:
            if t is None: return
            t = directive (t, **vars)
            try: # test our unicodiness
                str (t) 
            except UnicodeEncodeError, e:
                logger.error (u"{0}({1}):\n{3}".format (directive, elem.tag, e))
                    
        return t

    #
    # directive definitions
    #
    def discard (self, t, discard=False, **_):
        if discard:
            return None
        return t

    def replace (self, t, replace=None, **_):
        if replace:
            t = replace
        return t

    def sanitize (self, t, sanitize=True, **_):
        if sanitize:
            t = re.sub (ur'\xa0', ' ', t)
            t = re.sub (ur'[\u201c\u201d]', '"', t)
            t = re.sub (ur'\u2019', "'", t)    
            t = re.sub (ur'[\u2014\u2018]', '-', t)  
        return t

    def collapse (self, t, collapse=True, **_):
        ''' collapse sequences of spaces and newlines, replace non-ascii quotes
        '''
        if collapse:
            t = re.sub (ur'\s+', ' ', t)       
        return t

    def strip (self, t, strip=False, **_):
        if strip:
            return t.strip ()
        return t

    def format (self, t, format = None, **_):
        '''format using Python string.format
        '''
        return format.format (t)

    def indent (self, t, indent=4, **_):
        ''' indent a region
        '''
        lines = t.split ('\n')
        return '\n'.join ([(" " * indent + l) for l in lines])

    def prefix (self, t, prefix='', **_):
        ''' prepend a string
        '''
        return prefix + t

    def suffix (self, t, suffix='', **_):
        ''' append a string
        '''
        return suffix + t

    def combine (self, t, elem=None, event=None, combine=None, **_):
        ''' combine all identical siblings in a single string
        '''
        if combine:
            t = ', '.join ([c.text for c in elem.getparent().findall (combine)])
        return t

    def store (self, t, store=None, **_):
        if store:
            # print "store", _['re_match'].group (0)
            self._store.setdefault (store, [])
            self._store [store].append (t)
            return None
        return t

    def retrieve (self, t, retrieve=None, **_):
        if retrieve:
            # print "retrieve", _['re_match'].group (0)
            self._store [retrieve].append (t)
            t = ', '.join (self._store [retrieve])
            del self._store [retrieve]
        return t

    def newfile (self, t, newfile=False, **_):
        self._newfile = newfile
        return t


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
verbosity_levels = dict (debug=logging.DEBUG, info=logging.INFO, warn=logging.WARN, error=logging.ERROR, crit=logging.CRITICAL)
available_formats = [os.path.splitext (f)[0] for f in glob ("*.cfg")]

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

format_cfg = RawConfigParser (dict_type=OrderedDict)
format_cfg.optionxform = str # prevent configparser from lowercasing our regexes
format_cfg.read ('%s.cfg' % options.format)

parser = etree.XMLParser (dtd_validation=True) 

logger = logging.getLogger (__name__)
logger.setLevel (options.verbosity)

processor = Transformer (format_cfg)
logger.info (processor.description ())

# for each xml file
for srcfile in glob (os.path.join (options.srcdir, options.pattern)):
    tree = etree.parse (srcfile, parser)
    # logger.info ("  processing: {0}".format (os.path.basename (srcfile)))

    # for each element, in its own output file
    for directive in tree.xpath (options.root_element):
        processor.root (directive)
        output = StringIO ()

        # process element's tree
        for event, element in etree.iterwalk (directive, events=('start', 'end')):
            t = processor.process_element (event, element)
            if t is not None:
                output.write (t)

            if processor._newfile:
                target_dir = os.path.join (options.dest_dir, processor.directory (), os.path.splitext (os.path.basename (srcfile))[0])
                output_file = '{0}.{1}'.format (os.path.join (target_dir, element.get (options.fname_attribute)), processor.extension ())
                # logger.debug ("      -> {0}".format (output_file))

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


        



