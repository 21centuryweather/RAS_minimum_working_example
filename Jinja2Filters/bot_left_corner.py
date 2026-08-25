#!/usr/bin/env python
import numpy as np

def bot_left_corner(npts, delta, offset, centre=False, blc=False, do_rotate = False, ENDGame = False):
    """Computes the bottom left-hand corner of a model domain.
        
       Arguments:
         npts      -- number of grid points (ny, nx) in (latitude, longitude)                 
         delta     -- grid spacing (dy, dx) in degrees of (latitude, longitude)       
         offset    -- offset in degrees for this domain from (the region) centre 
       Keyword arguments:
         centre    -- coordinates (latitude, longitude) of the centre of 
                      the domain
         blc       -- coordinates (latitude, longitude) of the centre of 
                      the domain

         do_rotate -- if this is true a coordinate system with a rotated
                      pole will be adopted
         ENDGame   -- if this is true then an ENDGame-compatible grid is 
                      assumed (offset by half a grid point in each direction
                      from a New Dynamics grid)  
       Returns:
         The (latitude, longitude) coordinates of the bottom left-hand 
         corner of the domain described by the input parameters.       
    """
    if centre:
        if ENDGame:
            bot_left_lat = -0.5 * (npts[0] + 1) * delta[0]
        else:
            bot_left_lat = -0.5 * npts[0] * delta[0]

        if do_rotate:
            if centre[0] >= 0.0:
                if ENDGame:
                    bot_left_lon = 360.0 - 0.5 * (npts[1] + 1) * delta[1]
                else:
                    bot_left_lon = 360.0 - 0.5 * npts[1] * delta[1]
            else:
                if ENDGame:
                    bot_left_lon = 540.0 - 0.5 * (npts[1] + 1) * delta[1]
                else:
                    bot_left_lon = 540.0 - 0.5 * npts[1] * delta[1]
        else:
            bot_left_lat = centre[0] + bot_left_lat
            if ENDGame:             
                bot_left_lon = centre[1] - 0.5 * (npts[1] + 1) * delta[1]
            else:
                bot_left_lon = centre[1] - 0.5 * npts[1] * delta[1]
        
        bot_left_lat = bot_left_lat +offset[0]
        bot_left_lon = bot_left_lon +offset[1]

        if bot_left_lon >= 360.0:
            bot_left_lon = bot_left_lon - 360.0
        if bot_left_lon < 0.0:
            bot_left_lon = bot_left_lon + 360.0

    else:
        # blc option
        if ENDGame:
            bot_left_lat = blc[0]
            bot_left_lon = blc[1]
        else:
            bot_left_lat = blc[0] + 0.5*delta[0]
            bot_left_lon = blc[1] + 0.5*delta[1]
        
    # Return 32 bit precision
    return (np.float32(bot_left_lat), np.float32(bot_left_lon))
