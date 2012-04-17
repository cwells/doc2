# --------------------------------------------------------------------------
# rulesparser.py
#
# A module for parsing the rules files used by doc2.py
#
# (c) Cliff Wells, 2012  <cliff@nginx.com>
# --------------------------------------------------------------------------

from __future__ import print_function
import sys
import logging
import string
import re
import traceback
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
from pyparsing import (
    Literal, Word, White, ZeroOrMore, OneOrMore,
    Group, Dict, Optional, printables, ParseException, restOfLine
)

def tokens2dict (tokens):
    return OrderedDict ([(t [0], t [1:]) for t in tokens])

###
# Parse a rules file
###
class RulesParser (object):
    def __init__ (self):
        self.processors = dict (
            defaults = self.__process_rules,
            rules = self.__process_rules,
            info = self.__process_section,
            defines = self.__process_section
        )

        lbracket = Literal ("[").suppress ()
        rbracket = Literal ("]").suppress ()
        tilde  = Literal ("~").suppress ()
        equals = Literal ("=").suppress ()
        colon  = Literal (":").suppress ()
        pound  = Literal ("#")
        startEvent = Literal ('start')
        endEvent = Literal ('end')
        
        comment  = pound + Optional (restOfLine)
        nonequals = "".join ([ c for c in printables if c != "=" ]) + " \t"
        noncolon  = "".join ([ c for c in printables if c != ":" ]) + " \t"
        nonbracket = "".join ([ c for c in printables if c not in ['[',']'] ]) + " \t"

        sectionDef = lbracket + Word (nonbracket) + rbracket
        keyDef = ~tilde + Word (printables) + ZeroOrMore (Literal(' ')).suppress () + equals + ZeroOrMore (Literal (' ')).suppress () + restOfLine
        eventDef = Word (noncolon) + colon
        regexDef = tilde + ZeroOrMore (White (' \t').suppress ()) + restOfLine
        
        keyBlock = Group (keyDef)
        eventBlock = Group (eventDef + ZeroOrMore (keyBlock))
        regexBlock = Group (regexDef + ZeroOrMore (eventBlock))
        sectionBlock = Group (sectionDef + (ZeroOrMore (regexBlock) ^ ZeroOrMore (keyBlock)))

        self.bnf = Dict (OneOrMore (sectionBlock))
        self.bnf.ignore (comment)

    def __process_rules (self, rules):
        config = OrderedDict ()
        for rule in rules:
            regex = rule [0]
            config [regex] = OrderedDict ()
            try:
                config [regex]['.re'] = re.compile (regex)
            except:
                exc_type, exc_value, exc_traceback = sys.exc_info ()
                print ("\nRegex Error: {0}\nRule: {1}\n".format (exc_value, regex), file=sys.stderr)
                sys.exit (1)

            events = tokens2dict (rule [1:])
            for e in events:
                config [regex][e] = OrderedDict ()
                keys = OrderedDict (events[e])
                for k, v in keys.items ():
                    config [regex][e][k] = v
                config [regex][e]['.src'] = '\n'.join (["{0} = {1}".format (k, v) for (k, v) in config [regex][e].items ()])

        return config

    def __process_section (self, settings):
        config = OrderedDict ()
        for k, v in settings:
            config [k] = v 
        return config

    def __compile (self, config):
        ''' apply definitions to rule keyblocks and compile code block
        '''
        for section in 'rules', 'defaults':
            for rule, event in config.get (section, {}).items ():
                for e, keyblock in event.items ():
                    if e.startswith ('.'): continue
                    try:
                        code = string.Template (keyblock ['.src']).substitute (config.get ('defines', {}))
                    except KeyError, exc:
                        print ("\nException parsing rule:\n", file=sys.stderr)
                        print ("~ {0}\n\t{1}:".format (rule, e), file=sys.stderr)
                        print ('\t\t' + keyblock ['.src'].replace ('\n', '\n\t\t'), file=sys.stderr)
                        print ("\nKeyError: {0}\n".format (exc), file=sys.stderr)
                        sys.exit (1)

                    try:
                        keyblock ['.obj'] = compile (code, "{0} {1}".format (rule, e), 'exec')
                    except SyntaxError, exc:
                        print ("\nException parsing rule:\n", file=sys.stderr)
                        print ("~ {0}\n\t{1}:".format (rule, e), file=sys.stderr)
                        print ('\t\t' + keyblock ['.src'].replace ('\n', '\n\t\t'), file=sys.stderr)
                        print ("\nSyntaxError line {0}, char {1}\n".format (exc.lineno, exc.offset), file=sys.stderr)
                        sys.exit (1)


    def parse (self, config):
        if type (config) != type (""):
            config = config.read ()
        tokens = self.bnf.parseString (config)
        struct = tokens2dict (tokens.asList ())
        config = OrderedDict () 

        for section in struct:
            if not section in self.processors:
                logging.warn ("Skipping unknown section {0}".format (section))
                continue
            config [section] = self.processors [section] (struct [section])

        self.__compile (config)
        self._config = config
        return config

    def get (self, section):
        return self._config [section]

    def sections (self):
        for section in self._config:
            yield section

    def rules (self):
        ''' generate list of rule expressions
        '''
        for regex in self._config ['rules']:
            yield regex

    def events (self, rule):
        for event in self._config ['rules'][rule]:
            if not event.startswith ('.'):
                yield event

    def settings (self, rule, event):
        if event in self._config ['rules'][rule]:
            settings = self._config ['rules'][rule][event].items ()
        else:
            try:
                settings = self._config ['defaults'].values ()[0][event].items ()
            except KeyError:
                settings = {}

        return OrderedDict ([
            (k, v) for (k, v) in settings
            if not k.startswith ('.')    
        ])

    def src (self, rule, event):
        ''' for debugging
        '''
        return self._config ['rules'][rule][event]['.src']
    
    def obj (self, rule, event):
        if event in self._config ['rules'][rule]:
            return self._config ['rules'][rule][event]['.obj']

        try:
            return self._config ['defaults'].values ()[0][event]['.obj']
        except KeyError:
            logging.warn ("No handler found for {1} event in rule {0}, passing raw data.".format (rule, event))
            return compile ('pass', 'No default found', 'exec')

    def search (self, pattern):
        for regex in self.rules ():
            mo = self._config ['rules'][regex]['.re'].search (pattern, re.M)
            if mo: return regex, mo
        return None, None

###
# do a quick test
###
if __name__ == '__main__':
    cfg = r'''
    [info]
    description = test rules
    extension = .txt

    [defines]
    cr = "\n"

    [defaults]
    ~ ^
        start: 
            sanitize = True
            collapse = True
        end:
            sanitize = True
            collapse = True

    [rules]
    ~ /directive(\[\d+\])?$
        start:
            globals()['x'] = 'y'
            _name = 'foo'
            prefix = "{0}{cr}".format (_name, cr=$cr)
        end:
            sanitize = True
            collapse = True
            newfile = True

    ~ /context(\[1\])?$
        start:
            combine = "context"
            prefix = "{cr}<tr><td>Context:</td>".format (cr=$cr)
            format = "<td><pre>{0}</pre></td></tr></table>"
        end:
            sanitize = True
            collapse = True
    '''

    config = RulesParser ()
    c = config.parse (cfg)

    for r in config.rules ():
        print (r)
        for e in config.events (r):
            print ("\t{0}".format (e))
            for k, v in config.settings (r, e).items ():
                print ("\t\t{0} = {1}".format (k, v))

    print ("Searching")
    print (config.search ("/module/section[3]/directive[1]"))


