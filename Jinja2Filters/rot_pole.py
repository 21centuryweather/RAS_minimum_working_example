#!/usr/bin/env python

def rot_pole(centre, do_rotate = False):
    """Computes the North pole coordinates for a model domain.

       Arguments:
         centre -- coordinates (latitude, longitude) of the centre of 
                   the domain   
       Keyword arguments:
         do_rotate -- if this is true a coordinate system with a rotated
                      pole will be adopted
       Returns:
         The (latitude, longitude) coordinates of the North pole of the  
         domain with the specified centre.         
    """
    if do_rotate:
        if centre[0] >= 0.0:
            pole_lat = 90.0 - centre[0]
            pole_lon = centre[1] + 180.0
            if pole_lon >= 360.0:
                pole_lon = pole_lon - 360.0
            if pole_lon < 0.0:
                pole_lon = pole_lon + 360.0
        else:
            pole_lat = 90.0 + centre[0]
            pole_lon = centre[1]
            if pole_lon >= 360.0:
                pole_lon = pole_lon - 360.0
            if pole_lon < 0.0:
                pole_lon = pole_lon + 360.0
    else:
        pole_lat = 90.0
        pole_lon = 180.0
    
    return (pole_lat, pole_lon)

