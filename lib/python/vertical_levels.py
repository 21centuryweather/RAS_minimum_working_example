#!/usr/bin/env python

# Dictionary describing the vertical level sets available in the nesting suite.
# nlevs is the total number of levels, aero_bl_levs is the number of boundary
# layer levels over which aerosol is distributed (if Cusack climatological
# aersols are used), and rhcrit is the associated critical relative humidity
# profile.
# New level sets can be added by extending this dictionary and updating the
# suite metadata to include the new level set name.
levels = {             
         "L70_40km": {"nlevs": 70, "aero_bl_levs": 30, "top_in_m":40000},
         "L70_80km": {"nlevs": 70, "aero_bl_levs": 20, "top_in_m":80000},
         "L80_38p5km": {"nlevs": 80, "aero_bl_levs": 25, "top_in_m":38500},
         "L118_78km": {"nlevs": 118, "aero_bl_levs": 29, "top_in_m":78000},
         "L120_40km": {"nlevs": 120, "aero_bl_levs": 53, "top_in_m":40000},
         "L140_40km": {"nlevs": 140, "aero_bl_levs": 68, "top_in_m":40000},
         "L90_40km": {"nlevs": 90, "aero_bl_levs": 30, "top_in_m":40000}
         }






