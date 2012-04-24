#!/usr/bin/python

#
# Utility to scan local Subversion copy and determine which docs have 
# been changed and purge the MediaWiki cache for just those pages.  
# Also outputs a list of missing or misnamed pages.
#
# Implemenation note: MediaWiki doesn't return 404 for non-existent pages
# if there's any sort of query string, hence the need for the HEAD request.
#
# (c) Cliff Wells, 2012 <cliff@nginx.com>
#

import os
import time
from datetime import datetime, timedelta
import httplib

# assume that SVN is updated less than 30 minutes prior to now
cutoff = datetime.now () - timedelta (minutes=30)

changes = []
for root, folders, files in os.walk ('nginx.org/xml/en/docs/http/'):
    for filename in files:

        # only XML files...
        basename, ext = os.path.splitext (filename)
        if ext != '.xml': continue

        # only files changed within last <cutoff> minutes
        st = os.stat (os.path.join (root, filename))    
        mtime = datetime.fromtimestamp (st.st_mtime)
        if mtime < cutoff:
            continue

        # convert filename to wiki page style
        wikipage = '/' + ''.join ([part.capitalize () for part in basename.split ('_')[1:]])

        connection = httplib.HTTPConnection ('wiki.nginx.org')
        connection.request ('HEAD', wikipage)
        if connection.getresponse().status == 200:
            # purge the wm cache
            connection.request ('GET', '{0}?action=purge'.format (wikipage))
            print ("PURGED: {0}".format (wikipage))
        else:
            # page missing
            print ("MISSING: {0}".format (wikipage))
        connection.close ()
