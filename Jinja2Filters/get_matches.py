#!/usr/bin/env python

def get_matches(list1, list2, complement = False):
    """Finds matching or non-matching items in two lists.
        
       Arguments:
         list1 -- a list
         list2 -- another list
       Keyword arguments:
         complement -- if this is true, the items in list1 not in 
                       list2 are returned  
       Returns:
         A list of the items in list1 that are in (or not in) list2.           
    """
    if complement:
        matches = [item for item in list1 if item not in list2]
    else:
        matches = [item for item in list1 if item in list2]
    return matches

