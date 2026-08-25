#!/usr/bin/env python
'''
Script to regrid netcdf UKCA ancillary files from source grid to model 
grid. For now this includes emissions and oxidants. 
The '_ct' in the name refers to a 'cut-out' method (see below) rather than
default linear regridding.

Command line arguments:
    fname_destgrid - pp or nc file containing destination grid.  All fields in 
                     this file must be on the same grid, as the code uses the
                     first cube it finds (which may not be first in file)

Outputs:
    All ancil files required for a UKCA offline oxidants or StratTrop job, 
    written to $PWD/regrid_to_{destfilename}/. Within that directory the
    directory structure follows that of the source data, so that the result can
    easily be copied to e.g. $UMDIR/ancil.

Method:
    * The functions regrid_emissions() and regrid_oxidants() specify exactly 
      which source files are to be regridded. This reduces flexibility when 
      adding new files, but is a safety check that the expected files are all
      present.
    * The target grid is read from the first cube in fname_destgrid.
    * If the target grid is 3-dimensional and the vertical grids are different,
      the source data will be regridded vertically as well.
    * Files are regridded using Iris AreaWeighted regridding to conserve global
      total emissions. If the destination grid is a nest/ rotated grid, the data
      is 'cut-out' from the source using real lat/lon coordinates
    
'''
import argparse
import os
from re import search as rsearch
import iris
import numpy as np
from scipy.interpolate import griddata
import scipy.spatial.qhull as qhull

from sys import stdout as sysout
from sys import path as syspath

#from IPython import embed       #Insert embed() to enable a breakpoint

# syspath.append('/data/users/hadzm/code/ncancil/r1850_ukca_ncdf_nwp/ukca_netcdf')
# import ukca_netcdf.ancil_metadata as ancil_metadata 
# --- not neccesary to import as local_atts defined below

class RegridError(Exception):
    pass

def regrid_files(source_files, destgrid, source_root, output_root, caltype):
    '''
    Regrid all source files to destgrid. Preserve source directory structure
    for output files.
    
    This is pretty much a generic regridder, but does need to know about which
    attributes must remain as local variable attributes (so uses information 
    from ancil_metadata module).

    Arguments:
        source_files - a list of filenames to regrid, paths relative to
                       source_root
        destgrid - an iris cube on the destination grid
        source_root - root directory for source files
        output_root - root directory for output files
        caltype     - Calendar type of output file

    Method:
        Load all cubes from file.
        Regrid one at a time and save in a cubelist.
        Save cubelist to netCDF3 file.
        Re-read file and convert time axis to desired calendar

    '''
    # from ancil:contrib/ChemAeroEmissions/ancil_metadata
    # Attributes that are 'local' to variables and should not
    # appear as Global attributes in output file
    local_atts = ['tracer_name',
                  'vertical_scaling',
                  'lowest_level',
                  'highest_level',
                  'hourly_scaling']

    # note: it is not memory-efficient to keep all cubes "alive" in list before
    # writing, but I can't see how to write one at a time. For oxidants all
    # files have only one cube so is not an issue, but might prevent us lumping
    # aerosol clims into a single file. Also there might be a desire to lump
    # the oxidants similarly (though the files are ~7GB at N768 so
    # perhaps not).

    # Determine number of output levels for possible vertical regridding
    # Requires that the target grid has level_height information
    # First try the default Z coordinate, if this is just level number
    # search for level_ht, else set levels = 1
    #print(destgrid)
    dest_z, = destgrid.coords(dim_coords=True, axis = 'Z')
    dest_lev = len(dest_z.points)
    if dest_z.points[-1] == dest_lev:   # just level no.
       try:
          dest_z = destgrid.coord('level_height')
          dest_lev = len(dest_z.points)
       except:
          dest_lev = 1

    #print('Destination grid - Z ',dest_z,dest_lev)

    # Determine horizontal coordinates, incase only vertical interpolation
    # is required.
    dest_xcoord = destgrid.coord(dim_coords=True, axis = 'X')
    dest_lon = destgrid.coord(dim_coords=True, axis = 'X').points
       #dest_lat and dest_lon are 1D vectors
    n_dlon = len(dest_lon)
    dest_ycoord = destgrid.coord(dim_coords=True, axis = 'Y')
    dest_lat = destgrid.coord(dim_coords=True, axis = 'Y').points
    n_dlat = len(dest_lat)


    polelat = getattr(dest_ycoord.coord_system, 'grid_north_pole_latitude', 90)
    polelon = getattr(dest_xcoord.coord_system, 'grid_north_pole_longitude', 0)
    print('polelat/lon = ',polelat,polelon)

    #replicate the 1D arrays into 2D arrays using the shapes of the other array (e.g. shape of lat for the lon replication)
    lat2d=np.tile(dest_lat,[n_dlon,1])
    lon2d=np.tile(dest_lon,[n_dlat,1])
    lon2d_2=lon2d
    lat2d_2=np.transpose(lat2d)

    #unrotate the nested grid
    ulons, ulats = iris.analysis.cartography.unrotate_pole(lon2d_2,lat2d_2,polelon,polelat)

    #convert to 1d arrays :-
    #lats = lat2d_2.flatten()
    #lons = lon2d_2.flatten()
    #Convert to -180 to +180 longitudes for consistency with global and to avoid issues near 0 degE
    #iwrap=np.where(lons>180)
    #lons[iwrap]=lons[iwrap]-360

    #convert to 1d arrays :-
    lats = ulats.flatten()
    lons = ulons.flatten()
    #Convert to 0 to 360 longitudes for consistency with global and to avoid issues near 0 degE
    iwrap=np.where(lons<0.0)
    lons[iwrap]=lons[iwrap]+360

    # 'Cutout' method - for LAM target grids on rotated poles, cut-out the
    #  corresponding area from Global domain. 
    # Use iris.analysis.unrotate_pole to convert to real coordinates
    #l_dest_rotated = False
#    try:

    print('min/max destlat/lon = ',min(dest_lat),max(dest_lat),min(dest_lon),max(dest_lon))

#    print('dest_lat.shape,dest_lon.shape = ',dest_lat.shape,dest_lon.shape)
    print('lat2d_2.shape,lon2d_2.shape = ',lat2d_2.shape,lon2d_2.shape)


#    ulons, ulats = iris.analysis.cartography.unrotate_pole (lon2d_2,lat2d_2,
#                       polelon,polelat)

    #Rotate the global coordinates to match those of the rotated nest (done later)
    #... doing it this way round since it means that the nest will be centred at zero deg longitude
    # and so we are unlikely to have interpolation issues at the edges of the global domain




    #DPG - previously ulons and ulats were expected to be 1D arrays, but with unrotated coords as in a nested LAM they will be 2D. So, use .flatten() to roll-out the arrays into 1D arrays of size nlat*nlon    
#    cutout_grid = [ ('longitude',ulons.flatten()),('latitude',ulats.flatten()) ]
    #DPG - using griddata instead now as I don't think that irregular grids are supported in iris interpolate
    #N.B. - this previously worked ok for square arrays, but it would have been taking out square regions in lat/lon space rather than the distorted region of a nest with a rotated pole. This might be ok if the nest was near the equator, but not a higher latitudes. And with non-square arrays it failed.

    l_dest_rotated = True  # crude way of determining if rotated pole (==LAM)
#    except:
#       print('No Pole-Lat/Long found -assuming global-to-global regrid')

    for fname in source_files:
        fname_in = os.path.join(source_root, fname)
        fname_out = os.path.join(output_root, fname)

        print('Regridding', fname_in)

        # Make output directory for this file. Allow the directory to exist
        # from a previous iteration.
        outdir = os.path.dirname(fname_out)
        try:
            os.makedirs(outdir)
        except OSError:
            # Most likely OSError due to dir existing already from previous
            # iteration in this loop. Ignore such a case, but check dir does
            # exist and re-raise if not (e.g. could be permission denied).
            if not os.path.exists(outdir):
                raise
        #sysout.write(" Loading source data \n")
        #sysout.flush()
        cubes = iris.load(fname_in)
        ocubes = []


        icube=-1
        for cube in cubes:
            icube=icube+1
    
            #           if icube==0:
#Create an interpolator for faster repetition of interpolation onto new grid.
#interpolator = iris.analysis.Nearest(extrapolation_mode='nan').interpolator(cube, coords)
#               interpolator = iris.analysis.Linear().interpolator(cube, ['latitude', 'longitude'])

           # Check to see if horizontal regridding is required
            l_horiz = True
            src_lon = cube.coord(dim_coords=True, axis='X').points
            n_slon = len(src_lon)
            src_lat = cube.coord(dim_coords=True, axis='Y').points
            n_slat = len(src_lat)
            src_z,   = cube.coords(dim_coords=True, axis = 'Z')
            src_lev = len(src_z.points)
            src_t,   = cube.coords(dim_coords=True, axis = 'T')
            n_t = len(src_t.points)


       #Make the source grid 2D
            lat2d_src=np.tile(src_lat,[n_slon,1])
            lon2d_src=np.tile(src_lon,[n_slat,1])
            lon2d_src_2=lon2d_src
            lat2d_src_2=np.transpose(lat2d_src)

           #convert lon to run from 0 to 360 with no minus values
            iwrap=np.where(lon2d_src_2<0.0)
            lon360 = lon2d_src_2
            lon360[iwrap]=lon360[iwrap]+360
           #Copy the lat lon data to the left and right to avoid wrap around issues
            lat_global = np.concatenate((lat2d_src_2, lat2d_src_2, lat2d_src_2), axis=1)
            lon_global = np.concatenate((lon360 - 360.0, lon360, lon360 + 360.0), axis=1)

           #Rotate the global coordinates to match those of the rotated nest
           #... doing it this way round since it means that the nest will be centred at zero deg longitude
           # and so we are unlikely to have interpolation issues at the edges of the global domain
           #rlons, rlats = iris.analysis.cartography.rotate_pole (lon2d_src_2,lat2d_src_2,polelon,polelat)

       #Create a 2xN array containing pairs of all the coordinates for the global (now rotated) grid.
           #points_lat=rlats.flatten()
           #points_lon=rlons.flatten()

            points_lat=lat_global.flatten()
            points_lon=lon_global.flatten()

            points = np.vstack((points_lat,points_lon))
            points = np.transpose(points)


           #DPG - For a MUCH faster method, precompute the things needed for the interpolation since the input and output grids remain the same each time - once this is done the intepolation for new data is done very quickly!
            points_new = np.transpose(np.vstack((lats,lons))) #new points which we will interpolate onto
            vtx, wts = interp_weights(points, points_new, 2) #Create the arrays needed to interpolate onto our grid - only need to do once if the input and output grids remain the same.
            if n_slon == n_dlon and n_slat == n_dlat:    
                # dims equal -check sample points
                if src_lon[0] - dest_lon[0] < 0.00001 and \
                        src_lon[n_slon-1] - dest_lon[n_dlon-1] < 0.00001 and \
                        src_lat[0] - dest_lat[0] < 0.00001 and \
                        src_lat[n_slat-1] - dest_lat[n_slat-1] < 0.00001:
                    l_horiz = False
 
            if l_horiz :
                sysout.write(" Performing Horiz remapping \n")
                sysout.flush()

                try:
                    guess_horizontal_bounds(cube)
                except ValueError:
                    # assume error is just because coords have bounds already
                    pass

              # Force source cube to have same coordinate system as grid cube
              # (cleaner way to do it would be to set grid_mapping in netcdf?)
                cs = destgrid.coord_system()
                cube.coord(axis='x').coord_system = cs
                cube.coord(axis='y').coord_system = cs
              # If non-rotated Global grid use Area weighted else linear/ cutout
                if not l_dest_rotated:
                    print('first regrid')
                    ocube = cube.regrid(destgrid, iris.analysis.AreaWeighted())
                 #sysout.write("Area-weighted remapping \n")
                else: 
                 # Either rotated grid or LAM
                 #
                 # The preferred method is 'cutout', but 'Linear' or' 
                 # 'Area-weighted' (whichever works) is run first to create
                 # the destination cube. The data is then replaced by that
                 # from the cutout method
                 #try:
                 #    ocube = cube.regrid(destgrid, iris.analysis.AreaWeighted())
                 #except:
         #Create cube, but this is slow
                    ocube = cube.regrid(destgrid, iris.analysis.Linear())
                    
                icopy_cube=0  #Think this is problematic since some of the destgrid cubes are NetCDF3. Also, the level numbers may be different and so the new cubes will only contain data up to 70 levels and may go out of bounds.
                if icopy_cube==1:
                    #DPG - Can just copy the cube, which is much faster since will overwrite the data anyway :-
                    ocube = destgrid.copy()
            #But the name and units are different...
                    long_name=cube.long_name
                    units = cube.units
                    name = cube.name
                    st_name = cube.standard_name
                    var_name = cube.var_name    
                    atts = cube.attributes    
                    
                #ocube.rename(long_name)
                    ocube.long_name = long_name
                    ocube.units = units
                    ocube.name = name
                    ocube.standard_name = st_name
                    ocube.var_name = var_name
                    ocube.attributes = atts
                    
                 # overwrite with 'cutout' data --levelwise for optimum memory usage
                for iL in range(src_lev):
            #cutout_grid is made using unrotated grid.
                    #ocube2 = cube[:,l,:,:].interpolate(cutout_grid,iris.analysis.Linear()) #Linear takes too long... consider creating an interpolator to speed up repeatability?
                    ##ocube2 = cube[:,l,:,:].interpolate(cutout_grid,iris.analysis.Nearest())
                    
#                    for lat, lon in zip(latitudes, longitudes):
#                       result = interpolator([lat, lon])

             #ocube.data[:,l,:,:] = ocube2.data

                    #New method using griddata
            #Using iris interpolate as below fails for some reason. Takes a long time and then just says "Killed". Think it may be because it cannot deal with an irregular grid?
                    #scipy.interpolate.griddata works and is faster.

            #additional loop over time
                    for it in range(n_t):
                        dat_reg = cube[it,iL,:,:].data
                       #replicate the data to the left and right for wraparound
                        dat_reg = np.concatenate((dat_reg, dat_reg, dat_reg), axis=1)
                        values = dat_reg.flatten()
               #Slower method using griddata 
                       #dat_out = griddata(points, values, (lats, lons), method='linear')
                       #dat_out = dat_out.reshape(n_dlat,n_dlon)

               #MUCH faster method using cached vts and wts
                        dat_out = interpolate(values, vtx, wts)
                        dat_out = dat_out.reshape(n_dlat,n_dlon)

                        #fix any nans at the poles !PRF
                        fillv=np.mean(dat_out[~np.isnan(dat_out)])
                        dat_out[np.isnan(dat_out)]=fillv


               #Write back into the cube
                        ocube.data[it,iL,:,:] = dat_out

                 #ocube2='a'  # Free memory
            else:
                sysout.write(" Grids identical - no Horizontal remapping \n")
                sysout.flush()
                ocube = cube           
           # End if horizontal required
            
           # If target grid/ cube is 3-dimensional and levels are different,
           # then carry out vertical interpolation
           
           # Debug ###
           #print('Cube ',ocube.long_name,' vert_in ', src_lev ,' vert_out ',dest_lev)
           # Check that levels are different, and also that grids are 
           # not uni-level, which does not make sense for interpolation
           # Dest_lev is also set to 1 above if no hybrid_height values are found
            l_vert_interp = False
            if dest_lev != 1:  
              
              # If level are different, or are same but can be L70-80km and L70-40km
                if (src_lev != 1 and dest_lev != src_lev) or \
                        (dest_lev == src_lev and \
                             np.abs(src_z.points[src_lev-1] \
                                        - dest_z.points[dest_lev-1]) > 1.0e-3) :

                    if src_lev == src_z.points[-1]: # level numbers only
                        try:                         # search for level_height
                            src_z   = ocube.coord('level_height')
                            src_lev = len(src_z.points)
                        except:    
                       # flag up error saying levels are different but
                       # no height information found
                            sysout.write(" In/out levels differ but no height information.\n")
                            sysout.write(" Src and Dest files must contain 'level_height' coord" + \
                                             " or hybrid_ht as Z axis.\n")
                            sysout.flush()   
                            raise RegridError(" Height information missing.")

                        # If height information found, do vertical interpolation
                    l_vert_interp = True

            if l_vert_interp == True:   
                sysout.write(" Performing Vert remapping \n")
                sysout.flush()
              
              #print('In levels = ',src_z.points)
                ht_out = [('level_height',dest_z.points)]
                ocube = (ocube.interpolate(ht_out,iris.analysis.Linear()))
            else:    # no vertical interpolation
                pass

           # Convert to float32 (cube.regrid returns doubles)
            ocube.data = ocube.data.astype(np.float32, copy=False)
            ocubes.append(ocube)
           #print(ocubes[0])

        # Write file, ensuring that tracer_name etc remain as variables atts
        # not global atts (via local_keys kwrd).
        cube='b'
        cubes='c'  # free memory before the write
        sysout.write(" Writing cube to "+fname_out+"\n")
        sysout.flush()

        iris.save(ocubes, fname_out, zlib=True, complevel=4,
                  netcdf_format='NETCDF4_CLASSIC',unlimited_dimensions=[],
                  local_keys=local_atts)

        #iris.save(ocubes, fname_out,netcdf_format='NETCDF3_CLASSIC')


        ocubes='d'
        ocube='e' 
   
        sysout.write(" Converting data to "+caltype+" calendar.\n")
        convert_file_calendar(fname_out,new_calendar=caltype.lower())

# End Def regrid_ancil

# ============== Calendar handling functions from =============
# ancil:trunk/contrib/ChemistryAerosolEmissions/ukca_netcdf/calendar_convert.py
#
# Python routines to convert calendar in a netcdf file.
# On Cray this requires 
# $ module load scitools
# to get the right version of python2.7 with cf_units

from netCDF4 import Dataset
from cf_units import num2date, date2num

time_vars = ['time']  #, 'forecast_reference_time']

def convert_file_calendar(filename, new_calendar='gregorian'):
    '''
    Convert time variables to requested calendar. Original calendar is taken
    from each variable's calendar attribute. Edits file in place using netCDF4
    module (not Iris).

    Arguments:
        filename - file to amend (caution: is edited in place)
        new_calendar - target calendar

    '''

    f = Dataset(filename,'a')
    periodic = True
    #periodic = (f.update_type == '2')  assume all periodic

    for var in time_vars:
        try:
            t = f.variables[var]
        except KeyError:
            #"var" not present, jump to next iteration
            continue

        # only convert if input data is on a different cal
        if t.calendar != new_calendar:
          t[:] = time_convert(t[:], t.units, t.calendar, new_calendar, periodic)
          try:
            tbnds = f.variables[t.bounds]
          except AttributeError:
            print('Note:', var, 'has no bounds')
          else:
            tbnds[:] = time_convert(tbnds[:], t.units, t.calendar,
                                    new_calendar, periodic)

          t.calendar = new_calendar

    f.close()
   

def time_convert(times, units, old_calendar, new_calendar, periodic):
    '''
    Convert times from one calendar to another.

    Arguments:
        times - list or numpy array of times
        units - units attribute in CF format, e.g. "hours since..."
        old_calendar - calendar for input times
        new_calendar - calendar for ourput times
        periodic - whether the file contains periodic data. If true, the year
                   will be adjusted to avoid problems in conversion.

    Returns:
        adjusted times in new calendar

    Method:
        Converts to datetime objects and back again using num2date and date2num
        from netCDF4 module. Also adjusts associated bounds variables.

    Warnings:
        This script does not work at python 2.7.9, which is the Cray version.
        It fails in date2num with an AttributeError (no replace method), which 
        suggests date2num doesn't work with netcdftime objects.

    '''
    
    dts = num2date(times[:], units, calendar=old_calendar)

    # Some periodic files have year=0. year is irrelevant but 0 can cause
    # problems, so set to modern year. Only check the first date. dts can be a
    # list or a list of numpy.ndarrays.
    # Should not be an issue for ancil sources to de-activated : MD
    #if periodic:
    #    try:
    #        year = dts[0].year
    #    except AttributeError:
    #        year = dts[0][0].year
    #    if year == 0:
    #        dts = change_year(dts, 1970)

    newtimes = date2num(dts, units, calendar=new_calendar)
    return newtimes

# ==============================================================

# the next 3 functions copied from ants.utils
def guess_horizontal_bounds(*cubes):
    for cube in cubes:
        x, y = horizontal_grid(cube)
        guess_bounds(x, strict=False)
        guess_bounds(y, strict=False)


def horizontal_grid(cube, dim_coords=None):
    return (cube.coord(axis='x', dim_coords=dim_coords),
            cube.coord(axis='y', dim_coords=dim_coords))


def guess_bounds(coord, strict=True):
    """
    Guess bounds wrapper around the iris guess bounds functionality.

    Additional capability from iris includes sensible guessing of latitude
    bounds to ensure they remain contiguous.

    Parameters
    ----------
    coord : :class:`iris.coord.Coord`
        Iris coordinate in which to guess its bounds.
    strict : bool
        Define whether an existing bounds on the coordinate should raise an
        exception (True - default iris/ants behaviour).

    """
    if not strict:
        if coord.has_bounds():
            return
    coord.guess_bounds()
    if 'latitude' in coord.name().lower():
        bounds = coord.bounds.copy()
        bounds[bounds > 90.] = 90.
        bounds[bounds < -90.] = -90.
        coord.bounds = bounds


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('filepaths', type=str, nargs='+',
                        help='Emissions filepaths, relative to source-root.')
    parser.add_argument('--source-root', type=str, required=True,
                        help='Source root.')
    parser.add_argument('--output-root', type=str, required=True,
                        help='Output filepath for pre-processed files')
    parser.add_argument('--destgrid-file', type=str, required=True,
                        help='Filename for target grid. PP or netCDF file')
    parser.add_argument('--calendar', type=str, required=True, default='360day',
                        help='Calendar type of output, "360day" or "Gregorian" ')


    # Note: Standard ENDGAME grid files can be found in
    # /data/cr1/hadtq/grids
    
    args = parser.parse_args()

    if args.calendar.lower() not in  ['360day', 'gregorian']:
       print('\nInvalid Calendar type specified : '+args.calendar+'\n')

    return args

#DPG - Interopolation functions - see https://stackoverflow.com/questions/20915502/speedup-scipy-griddata-for-multiple-interpolations-between-two-irregular-grids
#Allows caching of the arrays computed by the interpolation if using the same input and outut grids for many different field values.
def interp_weights(xyz, uvw, d):
   #xyz are the input coordinates in a (npts,d) array
   #uvw are the output (i.e., new) coordinates in a (npts, d) array
   #d is the number of dimensions in the data.
   tri = qhull.Delaunay(xyz)
   simplex = tri.find_simplex(uvw)
   vertices = np.take(tri.simplices, simplex, axis=0)
   temp = np.take(tri.transform, simplex, axis=0)
   delta = uvw - temp[:, d]
   bary = np.einsum('njk,nk->nj', temp[:, :d, :], delta)
   return vertices, np.hstack((bary, 1 - bary.sum(axis=1, keepdims=True)))

#def interpolate(values, vtx, wts):
#   return np.einsum('nj,nj->n', np.take(values, vtx), wts)


def interpolate(values, vtx, wts, fill_value=np.nan):
   ret = np.einsum('nj,nj->n', np.take(values, vtx), wts)
   ret[np.any(wts < 0, axis=1)] = fill_value
   return ret





if __name__ == '__main__':
    args = parse_args()

    # take the first cube from the grid file and use as target grid
    destgrid = iris.load(args.destgrid_file)[0]
    guess_horizontal_bounds(destgrid)

    regrid_files(args.filepaths, destgrid, args.source_root, args.output_root, 
                 args.calendar)
