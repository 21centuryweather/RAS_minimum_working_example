#!/usr/bin/env python

def get_parent(regn, model):  
    """Finds the parent model of a given model.

    Arguments:
      regn     -- a dictionary describing the geographical region
                  of interest
      model    -- a dictionary describing the desired model in
                  the region of interest
      Returns:
        A dictionary specifying the parent (resolution level and model 
        within that resolution level) of the supplied model 
    """
    # model["ic_lbc_src"] is a 2-element tuple. 
    # The first entry is the resolution level number of the model
    # supplying initial/boundary condition files to the given model 
    # (subtracting 1 then gives the index in the list of models at 
    # that resolution). 
    # The second entry specifies the number of the model within that 
    # resolution level that provides initial/boundary condition files 
    # to the given model.
    parent_resln = regn["reslns"][model["ic_lbc_src"][0] - 1]
    parent_model = parent_resln["models"][model["ic_lbc_src"][1] - 1]
    parent = {"resln": parent_resln,
              "model": parent_model}
    return parent
