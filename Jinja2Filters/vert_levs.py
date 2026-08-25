#!/usr/bin/env python

import os
from copy import deepcopy

# TODO - future versions of cylc should support a lib/python directory.
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lib', 'python'))

from vertical_levels import levels

def vert_levs(name):
    """Returns details of a vertical level set.

       Arguments:
         name -- the name of the desired vertical level set 
       Returns:
         A dictionary containing the number of levels, number of
         non-local boundary layer levels and RH_crit profile for 
         the specified vertical level set
    """
    # Return the vertical level information for the desired level set.

    # Alter a copy (this code gets revisited in a suite reload.)
    levs = deepcopy(levels)
    return levs[name]
