=====
About
=====
doc2.py is a utility for converting XML documents into various text formats (wiki markups, reStructuredText, etc).

usage::

  ./doc2.py --help

  Options:
    -h, --help            show this help message and exit
    -s SRC, --source=SRC  source directory for XML files
    -d DIR, --destination=DIR
                          destination directory
    -p PATTERN, --pattern=PATTERN
                          convert files matching pattern
    -r ROOT, --root=ROOT  the root element, files will be split at every one of these
    -a ATTR, --attribute=ATTR
                          files will be named for this attribute of the ROOT element
    -f FORMAT, --format=FORMAT
                          output format [text|mediawiki]
    -v LEVEL, --verbosity=LEVEL
                          set verbosity [crit|warn|info|debug|error]

example::

  ./doc2.py -s ../src -p "*.xml"  -d ../output -f mediawiki -r "//directive" -a name

============
Dependencies
============
lxml_, OrderedDict_

If you are using Python 2.7 or greater, OrderedDict is not required.

.. _OrderedDict: http://pypi.python.org/pypi/ordereddict
.. _lxml: http://pypi.python.org/pypi/lxml/2.3.4

============
Config files
============
A format is defined by a config file (extension ".cfg").  A config file has several sections, described below.


[info] 
------
This section contains info about the config, as well as some defaults:

:description: 
  A general description of the config 
:extension:
  the extension to use for generated files
:directory:
  the directory to output generated files

Other options may be included (author, version, etc), but will be ignored.

[defaults]
----------
Default values may be set here. If a variable isn't explicitly defined in a section,
the value from here will be used (if present).  

You may want to at least set defaults for "start" and "end" processing sequences, 
otherwise internal defaults are used that may cause surprises. Exclude any directives
that won't be used.

[defines]
---------
This section allows you to define strings that can be substituted into the [rules] section.  These 
are not really variables, rather they are interpolated into the block.  If you aren't careful, this 
can lead to mistakes.  For example::

    [defines]
    newline = "\n"

    [rules]
    ^/foo/bar$:
        prefix = "$newline"

would result in::

    [rules]
    ^/foo/bar$:
        prefix = ""\n""

being evaluated, which probably isn't what you intended.

Also note that the regex itself is unaffected by substitutions.

[rules]
-------
This section is where you define regular expressions that will match particular XPaths, 
followed by a set of processing directives. The processing directives are executed as
Python code.

Rules are processed, in order, from top to bottom. The first matching rule is used. This
means you should put more specific rules above more general ones.

Once a rule is located, the rule's block is evaluated as Python code. 

A rule consists of the following::

    [regular expression]:
        [directives | nothing]

For example::

    ^/foo/bar.*/baz$:
        debug = True

Processing
----------
A rule may set special variables that control the generated output:

Variables  (type, default) 
--------------------------
:debug:    (boolean, False) - cause some output to be generated whenever this rule is matched
:discard:  (boolean, False) - causes the current element to be discarded
:replace:  (string, None)   - replace the current element with string
:combine:  (boolean, False) - combine all similar sibling elements into a single comma-separated string
:sanitize: (boolean, True)  - replaces non-ascii characters with ascii equivalents
:collapse: (boolean, True)  - collapses sequences of whitespace and newlines into a single space
:strip:    (boolean, False) - removes whitespace from both ends of element
:format:   (string, None)   - format the element using string
:prefix:   (string, None)   - prepend string to element
:suffix:   (string, None)   - append string to element
:indent:   (integer, 0)     - indent element by integer spaces
:newfile:  (boolean, False) - cause a new file to be started with the next element
:store:    (string, None)   - store the element in an array named string
:retrieve: (string, None)   - retrieve the elements stored in array named string
:begin:    (list)           - control processing sequence of the begin event
:end:      (list)           - control processing sequence of the end event

The order of these variables is irrelevant.  If you need to control the processing order, use 
the "begin" and "end" variables to tune how an element is processed. For example::

    /foo/bar$:
        begin = do.sanitize, do.collapse, do.prefix
        end = do.sanitize, do.collapse, do.suffix
        suffix = ">"
        prefix = "<"

"begin" corresponds to the opening tag of an element, "end" corresponds with the closing tag.

Variables
---------
Besides the directive-oriented variables, other information is provided:
:re:    - the Python regular expression module
:event: - the current event ("start" or "end")
:elem:  - the current element
:match: - the regular expression Match object
:regex: - the current regular expression 
:xpath: - the XPath of the current element


A more involved example
-----------------------

Given the following XML fragment::

    <list>
      <listitem name="bar">
        some text
        <list>
          <listitem name="foo">
            some more text
          </listitem>
        </list>
      </listitem>
    </list>

this rule::

    /listitem$:
        _depth = len (re.findall ('/list(/|$)', xpath))
        prefix = "*" * _depth
        format = " {tag}/{name}: {0}".format (tag=elem.tag, name=elem.get('name'))
    
would output::

    * listitem/bar: some text
    ** listitem/foo: some more text



