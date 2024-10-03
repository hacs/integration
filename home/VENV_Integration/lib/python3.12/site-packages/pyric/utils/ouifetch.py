#!/usr/bin/env python

""" ouifetch.py: get ouis data from IEEE

Copyright (C) 2016  Dale V. Patterson (wraith.wireless@yandex.com)

This program is free software:you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation,either version 3 of the License,or (at your option) any later
version.

Redistribution and use in source and binary forms,with or without modifications,
are permitted provided that the following conditions are met:
 o Redistributions of source code must retain the above copyright notice,this
   list of conditions and the following disclaimer.
 o Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
 o Neither the name of the orginal author Dale V. Patterson nor the names of any
   contributors may be used to endorse or promote products derived from this
   software without specific prior written permission.

Fetchs and stores oui data from IEEE

"""
from __future__ import print_function  # python 2to3 compability

__name__ = 'ouifetch'
__license__ = 'GPLv3'
__version__ = '0.0.2'
__date__ = 'July 2016'
__author__ = 'Dale Patterson'
__maintainer__ = 'Dale Patterson'
__email__ = 'wraith.wireless@yandex.com'
__status__ = 'Production'

try:
    # load urllib related for python 2
    # noinspection PyCompatibility
    from urllib2 import Request as url_request
    # noinspection PyCompatibility
    from urllib2 import urlopen as url_open
    # noinspection PyCompatibility
    from urllib2 import URLError as url_error
except ImportError:
    # noinspection PyCompatibility,PyUnresolvedReferences
    from urllib.request import Request as url_request
    # noinspection PyCompatibility,PyUnresolvedReferences
    from urllib.request import urlopen as url_open
    # noinspection PyUnresolvedReferences
    from urllib import error as url_error
import os,sys,datetime,time
import pyric

OUIURL = 'http://standards-oui.ieee.org/oui.txt'
OUIPATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),'data/oui.txt')

def load(opath=None):
    """
     parse oui.txt file
     :param opath: path of oui text file
     :returns: oui dict {oui:manuf} for each oui in path or empty dict
    """
    fin = None
    ouis = {}

    if not opath: opath = OUIPATH

    try:
        fin = open(opath)
        for line in fin.readlines()[1:]:
            o,m = line.strip().split('\t')
            ouis[o.lower()] = m[0:100]
        fin.close()
    except IndexError:
        pass
    except IOError as e:
        raise pyric.error(e.errno,e.strerror)
    finally:
        if fin and not fin.closed: fin.close()
    return ouis


def fetch(opath=None,verbose=False):
    """
     retrieves oui.txt from IEEE and writes to data file
     :param opath: fullpath of oui.txt
     :param verbose: write updates to stdout
    """
    # determine if data path is legit
    if opath is None: opath = OUIPATH
    if not os.path.isdir(os.path.dirname(opath)):
        print("Path to data is incorrect {0}".format(opath))
        sys.exit(1)

    # fetch oui file from ieee
    fout = None

    # set up url request
    req = url_request(OUIURL)
    req.add_header('User-Agent',"PyRIC +https://github.com/wraith-wireless/PyRIC/")
    try:
        # retrieve the oui file and parse out generated date
        if verbose: print('Fetching ', OUIURL)
        res = url_open(req)
        if verbose: print("Parsing OUI file")

        if verbose: print("Opening data file {0} for writing".format(opath))
        fout = open(opath,'w')
        gen = datetime.datetime.utcnow().isoformat() # use current time as the first line
        fout.write(gen+'\n')

        # pull out ouis
        t = time.time()
        cnt = 0
        for l in res:
            if '(hex)' in l:
                # extract oui and manufacturer
                oui,manuf = l.split('(hex)')
                oui = oui.strip().replace('-',':')
                manuf = manuf.strip()
                if manuf.startswith("IEEE REGISTRATION AUTHORITY"):
                    manuf = "IEEE REGISTRATION AUTHORITY"

                # write to file & update count
                fout.write('{0}\t{1}\n'.format(oui,manuf))
                cnt += 1
                if verbose: print("{0}:\t{1}\t{2}".format(cnt,oui,manuf))
        print("Wrote {0} OUIs in {1:.3} secs".format(cnt,time.time()-t))
    except url_error as e:
        print("Error fetching oui file: {0}".format(e))
    except IOError as e:
        print("Error opening output file {0}".format(e))
    except Exception as e:
        print("Error parsing oui file: {0}".format(e))
    finally:
        if fout: fout.close()

#if __name__ == '__main__':
#    # create arg parser and parse command line args
#    print "OUI Fetch {0}".format(__version__)
#    argp = ap.ArgumentParser(description="IEEE OUI fetch and parse")
#    argp.add_argument('-p','--path',help="Path to write parsed file")
#    argp.add_argument('-v','--verbose',action='store_true',help="Display operations to stdout")
#    argp.add_argument('--version',action='version',version="OUI Fetch {0}".format(__version__))
#    args = argp.parse_args()
#    verbose = args.verbose
#    path = args.path

    # execute
#    fetch(path,verbose)
