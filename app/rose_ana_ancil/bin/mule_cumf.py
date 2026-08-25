#!/usr/bin/env python
# (c) Crown copyright Met Office. All rights reserved.
"""
Use "cumf" and Mule from the UM utilities to compare two fields
files, or PP files.

"""
import sys
import argparse
import um_utils.cumf
import mule
try:
    import mule
except IOError:
    sys.exit("Unable to import Mule. Ensure Scitools module is loaded")

parser = argparse.ArgumentParser(
    "Compare UM fields files or PP files", epilog=__doc__)
parser.add_argument("file1", type=str, help="First fields file.")
parser.add_argument("file2", type=str, help="Second fields file.")
args = parser.parse_args()

um_files = []
for infile in (args.file1, args.file2):
    if mule.pp.file_is_pp_file(infile):
        # Make an empty fieldsfile object and attach the pp file's
        # fields objects to it.
        umf = mule.FieldsFile()
        umf.fields = mule.pp.fields_from_pp_file(infile)
        umf._source_path = infile
    else:
        umf = mule.load_umfile(infile)

    um_files.append(umf)

compare = um_utils.cumf.UMFileComparison(um_files[0], um_files[1])

if compare.match:
    print("[INFO]: Files %s and %s compare." % (args.file1, args.file2))
else:
    um_utils.cumf.summary_report(compare)
    msg = "[FAIL]: Files %s and %s do not compare." % (args.file1, args.file2)
    sys.exit(msg)
