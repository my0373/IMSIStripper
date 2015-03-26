#!/usr/bin/env python
import sys, os, re, gzip
from optparse import OptionParser

version="2.0"

def printdebug(message):
    print "DEBUG:%s" % message
    
def exitscript(status=0):
    
    ## Define hash of error codes and simple messages.
    ## Functions are still expected to give some userful information.
    exitmatrix = {0:"Exiting successfully.",
                  1:"No input file supplied.",
                  2:"No output directory supplied",
                  3:"No output filename supplied",
                  4:"Relative filename does not exist",
                  5:"Absolute filename does not exist",
                  6:"File has a zero filesize",
                  8:"Unable to write to output file",
                  10:"Unknown Error",
                  }
    
    ## Print the appropriate message
    if status > 0:
        print "ERROR:%s" % exitmatrix[status]
    else:
        print exitmatrix[status]
    
    ## Let the user know what we exited with
    print "Exiting with status %d" % status
    
    ##?Exit with that status
    sys.exit(status)
    
def validateRawFile(rawfile,options):
    '''
    Here we validate, and collect information about the file.
    We perform a number of tests on the filename, and collect some information about the file.
    
    1) Does the file exist.
    2) Make sure the file has no write locks on it.
    2) Can we read it.
    3) Determine, and store the full path to the file.
    4) Determine filesize, and make sure it has a non-zero filesize.
    '''
    
    ##?Create an empty dictionary, this will hold the information about the file.
    rawFileDict = {}
    
    ## This is the filename as passed to the script, probably a relative path.
    rawFileDict["relpath"] = options.INPUT_FILE
    
    ## Get the absolute path for the file.
    rawFileDict["fullpath"] = os.path.abspath(options.INPUT_FILE)
    
    ## Check the reative file path exists.
    rawFileDict["relpathexists"] = os.path.isfile(rawFileDict["relpath"])
    
    if not rawFileDict["relpathexists"]:
        exitscript(4)
    
    ## Check the full path exists
    rawFileDict["fullpathexists"] = os.path.isfile(rawFileDict["fullpath"])
    
    if not rawFileDict["fullpathexists"]:  
        exitscript(5)
    

    '''
    The next steps are to check to see if the file is compressed.
    This may affect the behaviour of the script in future, so we will
    just set a flag for now.
    
    We only care about compressed files, so anything that doesn't
    match is treated as an uncompressed file.
    '''
    ## Funky python to reverse a string, and make it lowercase.    
    tmpextension = rawFileDict["fullpath"][::-1].lower()
    

    ## Is compressed.
    if tmpextension[0:3][::-1] == ".gz":
        rawFileDict["fileextension"] = "gz"
        rawFileDict["compressed"] = True
    
    ## Is not compressed
    else:
        rawFileDict["fileextension"] = "uncompressed"
        rawFileDict["compressed"] = False
    
    ## Check the size of the file.
    rawFileDict["filesize"] = os.path.getsize(rawFileDict["fullpath"])
    
    if rawFileDict["filesize"] == 0:
        exitscript(6)
        
    '''
    If we have made it this far, we have a file with a positive file size, that exists and is readable.
    We return a ditionary of this information, so we can start looking at the file.
    '''
        
    return rawFileDict 

def main(options):
    '''
    The main control function of the script.
    
    parameters: rawfile - The name of the raw file we are going to parse.
    '''
    if options.DEBUG:
        printdebug("Attempting to valiate file %s" % options.INPUT_FILE)
        
    rawfiledict = validateRawFile(options.INPUT_FILE,options)
    
    if options.DEBUG:
        printdebug("File %s has been validated." % options.INPUT_FILE)

    if options.DEBUG:
        printdebug("Attempting to read file %s" % rawfiledict["fullpath"])
    
    ## Do the heavy lifting and get the imsis, as a dictionary to avoid
    ## duplicates and use memory more efficiently.
    imsidict = getIMSIFromFile(rawfiledict,options)
    
    if options.DEBUG:
        printdebug("IMSI List created and duplicates discarded")
    ## Write the dictinary to disk.
    if writeIMSIToFile(imsidict,rawfiledict,options):
        exitscript()
    else:
        exitscript(10)
    
def writeIMSIToFile(imsidict,rawfiledict,options):
    
    
    ## Take the filename and output directory from the options.
    
    outputfile = os.path.join(options.OUTPUT_DIR,options.OUTPUT_FILE)
    
    if options.DEBUG:
        printdebug("Attempting to write results to file %s " % (outputfile))
    
    try:
        
        ## Open the file for writing
        outputfh = open(outputfile,'wa')

    except IOError,e:
        exitscript(8)
    
    ## Generate a list of IMSI's
    outputlines = ["%s\n" % k for k,v in imsidict.iteritems()]
    lenlines = len(outputlines)
    
    ## Write the lines in bulk to speed it up.
    outputfh.writelines(outputlines)
    

    ## Close the file.
    outputfh.close()
    
    if options.DEBUG:
        printdebug("Written %d imsis to file %s" % (lenlines,outputfile))
    
    ## Return True so we know it was all good.
    return True
    
def getIMSIFromFile(rawfiledict,options):
    '''
    This function just strips IMSI's from the supplied file.
    '''
    
    imsidict = {}
    
    ##?If the file is gzip compressed, we use gzip to open the file.
    if rawfiledict["compressed"]:
        rawfh = gzip.open(rawfiledict["fullpath"],'r')
        if options.DEBUG:
            printdebug("File %s is compressed" % options.INPUT_FILE)
        
    ## Otherwise we use the standard python open.
    else:
        rawfh = open(rawfiledict["fullpath"],'r')
        if options.DEBUG:
            printdebug("File %s is uncompressed" % options.INPUT_FILE)
    
    ## Load the file line into memory as a list.
    lines = rawfh.readlines()

    ## Release the file.
    rawfh.close()
    
    ## This is a complied regular expression. It is faster to compile it before we use it.
    splitre = re.compile(r'[;@]')
    
    ## This is a list comprehension, it allows us to efficiently look through all the lines in memory
    ## Once we match the conditions below, only the matching results will be returned as a list.
    matchimsis = [re.split(splitre,line)[2][1::] for line in lines if "DIAMETER_AUTHORIZATION_REJECTED" in line and ";SWm;" in line]
    
    for imsi in matchimsis: 
        imsidict[imsi] = None
    
    return imsidict
    
    
def initOptParser():
    parser = OptionParser()
    parser.add_option("-i", "--input", dest="INPUT_FILE",
                      help="read logs from file")
    parser.add_option("-o", "--outdir", dest="OUTPUT_DIR",
                      help="write output to directory")
    parser.add_option("-f", "--outfile", dest="OUTPUT_FILE",
                      help="output file name")
    parser.add_option("-d", "--debug",
                  action="store_true", dest="DEBUG", default=False,
                  help="get extra debug output")


    (options, args) = parser.parse_args()
    
    if not options.INPUT_FILE:
        exitscript(1)
    if not options.OUTPUT_DIR:
        exitscript(2)
    if not options.OUTPUT_FILE:
        exitscript(3)
    return options
 

if __name__ == '__main__':
    ## Generate an options object
    options = initOptParser()
    
    main(options)
        
