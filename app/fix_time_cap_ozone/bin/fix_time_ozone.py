#!/usr/bin/env python
"""
This script modifies an error in the time of the Ozone ancillary
Replacing the Dec 1990 timestamps by Dec 1989.
"""
import mule
import os

def main():

    # Get environment variables
    ozone_file_in=os.environ.get("ozone_file_in")
    ozone_file_out=os.environ.get("ozone_file_out")

    # Load ancil file
    ozone_fld = mule.AncilFile.from_file(ozone_file_in)

    # Adjust the forecast reference time for each field
    for field in ozone_fld.fields:
        if field.lbyrd == 1990:
            field.lbyrd = 1989
        print(field.lbyrd)

    # Set level dependent constants to None or mule will not save the file
    ozone_fld.level_dependent_constants = None

    # Over-ride the mule validate function to avoid a validation failure for 
    # the stretched grid ozone file from CAP
    ozone_fld.validate = lambda *args, **kwargs: True

    # Save to a new file
    ozone_fld.to_file(ozone_file_out)

if __name__ == '__main__':
    main()
