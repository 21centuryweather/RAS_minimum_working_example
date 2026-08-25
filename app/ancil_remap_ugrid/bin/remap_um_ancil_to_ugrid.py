#!/usr/bin/env python
# *****************************COPYRIGHT*******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file LICENCE
# which you should have received as part of this distribution.
# *****************************COPYRIGHT*******************************
import iris
import numpy as np
import netCDF4 as nc
import os

def remap_um_ugrid(src_data):
    """
    Remap regional UM ancillary data to UGRID format.
    
    Parameters:
    src_data (iris.cube.Cube): The source data to remap.
    
    Returns:
    numpy.ndarray: The remapped data.
    """
    # Get the number of dimensions of the data
    num_dims = src_data.ndim

    # Handle 2D, 3D, and 4D cases differently
    if num_dims == 2:
        # 2D data: Apply flip and reshape
        return np.flipud(src_data.data).reshape(-1)
    
    elif num_dims == 3:
        # 3D data: Flip along the last axis and flatten
        # Example: Assume the shape is (time, latitude, longitude)
        dshape = np.shape(src_data.data)
        flipped_data = np.flip(src_data.data,axis=1)
        reshaped_data = flipped_data.reshape(int(dshape[0]), -1)
        return np.squeeze(reshaped_data)  # Keep first dimension, flatten the rest
    
    elif num_dims == 4:
        # 4D data: Flip along the last two axes and flatten
        # Example: Assume the shape is (time, level, latitude, longitude)
        dshape = np.shape(src_data.data)
        flipped_data = np.flip(src_data.data,axis=2)
        reshaped_data = flipped_data.reshape(int(dshape[0]),int(dshape[1]), -1)
        return np.squeeze(reshaped_data)
    
    else:
        raise ValueError(f"Unsupported number of dimensions: {num_dims}")

def get_cube_names(cubes):
    # For each cube, use cube.var_name if it exists, otherwise use cube.name()
    #names= [cube.var_name if hasattr(cube, 'var_name') else cube.name() for cube in cubes]
    names = [cube.var_name if (hasattr(cube, 'var_name') and cube.var_name is not None)
    else cube.name() 
    for cube in cubes
    ]
    return names


def find_max_dimensions(cubes):
    """
    Find the maximum number of dimensions across all cubes in a CubeList.
    
    Parameters:
    cubes (iris.cube.CubeList): List of cubes to check.
    
    Returns:
    int: Maximum number of dimensions found.
    """
    max_dims = 0  # Initialize with 0

    for cube in cubes:
        num_dims = cube.ndim  # Get the number of dimensions for the current cube
        if num_dims > max_dims:
            max_dims = num_dims  # Update if this cube has more dimensions
    
    return max_dims

def get_mesh_dimensions(source_file):
    #From the input mesh_file get the dimensions for UGRID
    with nc.Dataset(source_file, 'r') as src_ds:
        dim0_size = src_ds.dimensions['ndynamics_face'].size
        num_node_size = src_ds.dimensions['ndynamics_node'].size
        num_vertices_size = src_ds.dimensions['Four'].size
    return dim0_size, num_node_size, num_vertices_size


def get_mesh_values(source_file, varname):
    #get the data values for mesh related variables
    with nc.Dataset(source_file, 'r') as src_ds:
        return src_ds.variables[varname][:]


def create_outfile_name(file_path,outfile_path):
    #create an output filename based on UM ancil filename 
    #TODO add an LFRIC output path as well currently its PWD

    #Remove .nc (e.g. sea-chlorophyll)
    file_path=file_path.split('.nc')[0]
    
    files = os.path.basename(file_path)
    file_name=os.path.join(outfile_path, files)
    return f"{file_name}.ugrid.nc"

def create_dimensions_in_netcdf(cubes, ds):
    """
    Check if the dimensions 'time', 'model_level_number', or 'pseudo_level' exist in any of the cubes
    and create equivalent dimensions in the provided NetCDF Dataset.

    Parameters:
    cubes (iris.cube.CubeList): List of Iris cubes to check.
    ds (netCDF4.Dataset): An open NetCDF Dataset object to write dimensions and variables to.
    """
    # Loop through each cube and check for time, model_level_number, and pseudo_level
    for cube in cubes:
        # Check and create the 'time' dimension
        time_coord = cube.coords('time')
        if time_coord:
            time_points = time_coord[0].points
            time_units = time_coord[0].units
            try:
                time_bounds = time_coord[0].bounds
            except AttributeError:
                time_bounds = None

            # Create the time dimension and variable if it doesn't already exist
            if 'time' not in ds.dimensions:
                ds.createDimension('time', len(time_points))
                time_var = ds.createVariable('time', 'f8', ('time',))
                time_var[:] = time_points
                time_var.axis = "T"
                time_var.bounds = "time_bounds"
                time_var.units = time_units.origin
                time_var.standard_name = "time"
                time_var.calendar = time_units.calendar

                # Add bounds if they exist
                if time_bounds is not None:
                    if 'nbounds' not in ds.dimensions:
                        ds.createDimension('nbounds', 2)  # Assuming bounds have 2 values (start, end)
                        time_bounds_var = ds.createVariable('time_bounds', 'f8', ('time', 'nbounds'))
                        time_bounds_var[:, :] = time_bounds
                print("Time dimension added.")

        # Check and create the 'model_level_number' dimension
        model_level_coord = cube.coords('model_level_number')
        if model_level_coord:
            model_level_points = model_level_coord[0].points

            # Create the model level dimension and variable if it doesn't already exist
            if 'model_level_number' not in ds.dimensions:
                ds.createDimension('model_level_number', len(model_level_points))
                model_level_var = ds.createVariable('model_level_number', 'i8', ('model_level_number',))
                model_level_var[:] = model_level_points
                model_level_var.units = "1"
                model_level_var.standard_name = "model_level_number"
                model_level_var.axis = "Z"
                model_level_var.positive = "up"
                print("Model level dimension added.")

        # Check and create the 'pseudo_level' dimension
        pseudo_level_coord = cube.coords('pseudo_level')
        if pseudo_level_coord:
            pseudo_level_points = pseudo_level_coord[0].points

            # Create the pseudo level dimension and variable if it doesn't already exist
            if 'pseudo_level' not in ds.dimensions:
                ds.createDimension('pseudo_level', len(pseudo_level_points))
                pseudo_level_var = ds.createVariable('pseudo_level', 'f8', ('pseudo_level',))
                pseudo_level_var[:] = pseudo_level_points
                pseudo_level_var.units = "1"
                pseudo_level_var.standard_name = "pseudo_level"
                print("Pseudo level dimension added.")

        # Check and create the height dimensions.
        # Aerosol files have the correct coordinates, but ozone
        # from the CAP is garbled with level heights in sigma and 
        # sigma in level_pressure, so we check for this and adjust
        # if necessary, using generic code below.
        sigma_coord = cube.coords('sigma')
        level_height_coord = cube.coords('level_height')
        if not level_height_coord:
            level_height_coord = cube.coords('level_pressure')
            if sigma_coord:
                if (np.max(sigma_coord[0].points) > 1.0):
                    level_height_coord = cube.coords('sigma')
                    sigma_coord = cube.coords('level_pressure')
        
        if level_height_coord:
            level_height_points = level_height_coord[0].points
            try:
                level_height_bounds = level_height_coord[0].bounds
            except AttributeError:
                level_height_bounds = None

            # Create the level_height dimension and variable if it doesn't already exist
            if 'level_height' not in ds.variables:
                level_height_var = ds.createVariable('level_height', 'f8', ('model_level_number',))
                level_height_var[:] = level_height_points
                level_height_var.bounds = "level_height_bounds"
                level_height_var.units = "m"
                level_height_var.long_name = "level_height"
                level_height_var.positive = "up"

                # Add bounds if they exist
                if level_height_bounds is not None:
                    if 'nbounds' not in ds.dimensions:
                        ds.createDimension('nbounds', 2)  # Assuming bounds have 2 values (start, end)
                    level_height_bounds_var = ds.createVariable('level_height_bounds', 'f8', ('model_level_number', 'nbounds'))
                    level_height_bounds_var[:, :] = level_height_bounds[:, :]
                print("Level height dimension added.")

        if sigma_coord:
            sigma_points = sigma_coord[0].points
            try:
                sigma_bounds = sigma_coord[0].bounds
            except AttributeError:
                sigma_bounds = None

            # Create the sigma dimension and variable if it doesn't already exist
            if 'sigma' not in ds.variables:
                sigma_var = ds.createVariable('sigma', 'f8', ('model_level_number',))
                sigma_var[:] = sigma_points
                sigma_var.bounds = "sigma_bounds"
                sigma_var.units = "1"
                sigma_var.long_name = "sigma"

                # Add bounds if they exist
                if sigma_bounds is not None:
                    if 'nbounds' not in ds.dimensions:
                        ds.createDimension('nbounds', 2)  # Assuming bounds have 2 values (start, end)
                    sigma_bounds_var = ds.createVariable('sigma_bounds', 'f8', ('model_level_number', 'nbounds'))
                    sigma_bounds_var[:, :] = sigma_bounds[:, :]
                print("Sigma dimension added.")

    print(f"Dimensions added to NetCDF dataset.")

def create_dimlist(cube):
    """
    Create a NetCDF , ignoring 'x' and 'y' dimensions.
    
    Parameters:
    cube (iris.cube.Cube): The Iris cube from which to create the variable.
    """
    # Get all dimensions excluding 'x' and 'y' dimensions
    relevant_dims = []
    dim_names = []

    for coord in cube.coords(dim_coords=True):
        # Ignore 'x' and 'y' (or any dimensions representing spatial coordinates)
        if coord.standard_name not in ['grid_longitude', 'grid_latitude','longitude', 'latitude']:
            relevant_dims.append(coord)
            dim_names.append(coord.standard_name or coord.name())
    
    # Create dimensions in the NetCDF file if they don't exist
    for dim in relevant_dims:
        dim_name = dim.standard_name or dim.name()

    # Prepare the shape of the new variable based on the relevant dimension names
    var_shape = tuple(dim_name for dim_name in dim_names)

    print(var_shape)
    return(var_shape)
    
def get_attribute(inpfile, attrname, varname=None):
    """
    Retrieve an attribute from a NetCDF file.
    
    Parameters:
        inpfile (str): Path to the NetCDF file.
        attrname (str): The attribute name to retrieve.
        varname (str, optional): The variable name from which to retrieve the attribute.
            If provided, the function checks the variable's attributes; otherwise, it
            checks the global attributes.
    
    Returns:
        The attribute value if it exists, or None if not found.
    """
    # Open the dataset in read-only mode.
    dataset = nc.Dataset(inpfile, "r")
    
    if varname is not None:
        # Check whether the variable exists.
        if varname not in dataset.variables:
            dataset.close()
            raise ValueError(f"Variable '{varname}' not found in the dataset.")
        var = dataset.variables[varname]
        # Check and retrieve the variable attribute.
        if attrname in var.ncattrs():
            atri = var.getncattr(attrname)
        else:
            atri = None
    else:
        # Check and retrieve the global attribute.
        if attrname in dataset.ncattrs():
            atri = dataset.getncattr(attrname)
        else:
            atri = None

    dataset.close()
    return atri

def append_history(inpfile,outputfile,meshfile,basehist=None):
    import datetime
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    new_entry = f"created on {timestamp}: remap_um_ancil_to_ugrid.py {inpfile} {meshfile} {outputfile} "
    #print(new_entry)
    if basehist:
        updated_history = new_entry + "\n" + basehist
    else:
        updated_history = new_entry
    return updated_history
    
def is_netcdf(file_path):
    """
    Check if the provided file is a valid NetCDF file.

    Parameters:
        file_path (str): The path to the file to check.

    Returns:
        bool: True if the file is a valid NetCDF file, False otherwise.
    """
    try:
        # Try to open the file in read-only mode.
        with nc.Dataset(file_path, 'r') as ds:
            # If successful, it's a NetCDF file.
            return True
    except Exception as e:
        # If an exception is raised, the file is likely not a valid NetCDF file.
        # You might want to log or print the error in a real application.
        return False

def make_ugrid_ancil(output_file, varnames, mesh_file, source_file,ndims):
    #create the ugrid ancilfile
    print(f"Creating output file {output_file}")        
    with nc.Dataset(output_file, 'w', format='NETCDF4') as ds:
        dim0_size, num_node_size, num_vertices_size = get_mesh_dimensions(mesh_file)
        if ndims>2 :
            #if the UM variable is not 2D then it will check for model_level_number, time or pseudo_level 
            #create dimensions for that bases on the input cube
            create_dimensions_in_netcdf(iris.load(source_file), ds)

        # Creating mesh dimensions for UGRID ancil file based on input mesh
        ds.createDimension('dim0', dim0_size)
        ds.createDimension('num_node', num_node_size)
        ds.createDimension('num_vertices', num_vertices_size)
        # Mesh y coordinates
        dynamics_face_y = ds.createVariable('dynamics_face_y', 'f8', ('dim0',))
        dynamics_face_y[:] = get_mesh_values(mesh_file, 'dynamics_face_y')
        dynamics_face_y.units = "degrees_north"
        dynamics_face_y.standard_name = "latitude"
        dynamics_face_y.long_name = "latitude of 2D face centres"
        # Mesh x coordinate
        dynamics_face_x = ds.createVariable('dynamics_face_x', 'f8', ('dim0',))
        dynamics_face_x[:] = get_mesh_values(mesh_file, 'dynamics_face_x')
        dynamics_face_x.units = "degrees_east"
        dynamics_face_x.standard_name = "longitude"
        dynamics_face_x.long_name = "longitude of 2D face centres"
        # Mesh topology
        dynamics = ds.createVariable('dynamics', 'i4')
        dynamics[:] = get_mesh_values(mesh_file, 'dynamics')
        dynamics.cf_role = "mesh_topology"
        dynamics.topology_dimension = 2
        dynamics.node_coordinates = "dynamics_node_y dynamics_node_x"
        dynamics.face_coordinates = "dynamics_face_y dynamics_face_x"
        dynamics.face_node_connectivity = "dynamics_face_nodes"
        dynamics.face_dimension = "dim0"
        dynamics.long_name = "Topology data of 2D unstructured mesh"
        # Node coordinates y
        dynamics_node_y = ds.createVariable('dynamics_node_y', 'f8', ('num_node',))
        dynamics_node_y[:] = get_mesh_values(mesh_file, 'dynamics_node_y')
        dynamics_node_y.standard_name = "latitude"
        dynamics_node_y.long_name = "latitude of 2D mesh nodes."
        dynamics_node_y.units = "degrees_north"
        # Node coordinates x
        dynamics_node_x = ds.createVariable('dynamics_node_x', 'f8', ('num_node',))
        dynamics_node_x[:] = get_mesh_values(mesh_file, 'dynamics_node_x')
        dynamics_node_x.standard_name = "longitude"
        dynamics_node_x.long_name = "longitude of 2D mesh nodes."
        dynamics_node_x.units = "degrees_east"
        # Face node connectivity
        dynamics_face_nodes = ds.createVariable('dynamics_face_nodes', 'i4', ('dim0', 'num_vertices'))
        dynamics_face_nodes[:] = get_mesh_values(mesh_file, 'dynamics_face_nodes')
        #dynamics_face_nodes.grid_staggering = 6
        dynamics_face_nodes.Conventions = "UGRID-1.0"
        dynamics_face_nodes.cf_role = "face_node_connectivity"
        dynamics_face_nodes.start_index = 1
        dynamics_face_nodes.long_name = "Maps every quadrilateral face to its four corner nodes."
     
        for var_name in varnames:
            cube = iris.load_cube(source_file, var_name) 
            if ndims>2:
                var_shape = create_dimlist(cube)
                var_shape = var_shape + ('dim0',)
                # forecast_period_coord = cube.coords('forecast_period')
                # if forecast_period_coord:
                #     if not 'forecast_period' in ds.variables:
                #         forecast_period_points = forecast_period_coord[0].points
                #         forecast_period_var = ds.createVariable('forecast_period', 'f8', ('time',))
                #         forecast_period_var[:] = forecast_period_points
                #         forecast_period_var.units = forecast_period_coord[0].units.origin
                #         forecast_period_var.standard_name = "forecast_period"

                forecast_reference_time_coord = cube.coords('forecast_reference_time')
                if forecast_reference_time_coord:
                    if not 'forecast_reference_time' in ds.variables:
                        forecast_reference_time_points = forecast_reference_time_coord[0].points
                        forecast_reference_time_var = ds.createVariable('forecast_reference_time', 'f8', ('time',))
                        forecast_reference_time_var[:] = forecast_reference_time_points
                        forecast_reference_time_var.units = forecast_reference_time_coord[0].units.origin
                        forecast_reference_time_var.standard_name = "forecast_reference_time"

                # Add auxiliary coordinates to the coordinates of the variable.
                # We check that they exist. Correcting for problems with
                # ozone is not strictly necessary, but ensures that we
                # point to the right data.
                sigma_coord = cube.coords('sigma')
                level_height_coord = cube.coords('level_height')
                if not level_height_coord:
                    level_height_coord = cube.coords('level_pressure')
                if sigma_coord:
                    if (np.max(sigma_coord[0].points) > 1.0):
                        level_height_coord = cube.coords('sigma')
                        sigma_coord = cube.coords('level_pressure')

                var = ds.createVariable(var_name, 'f8', var_shape, fill_value=-32768.0*32768.0)
                data = remap_um_ugrid(cube)
                var[:] = data
            else:
                var = ds.createVariable(var_name, 'f8', ('dim0',), fill_value=-32768.0*32768.0)
                data = remap_um_ugrid(cube)
                var[:] = data
            
            var.location = "face"
            var.mesh = "dynamics"
            var.online_operation = "once"
            if ndims==2:
                var.coordinates = "dynamics_face_x dynamics_face_y"
            elif ndims>2 and sigma_coord and level_height_coord:
                var.coordinates = "forecast_reference_time sigma level_height dynamics_face_x dynamics_face_y"
            elif ndims>2:
                var.coordinates = "forecast_reference_time dynamics_face_x dynamics_face_y"
            #Check if source file is netcdf then we can add additional cube identifiers in this method.
            if is_netcdf(source_file):
                #Checking whether a long_name exists in the UM ancilliary and if it does then add it to the UGRID file
                ln = get_attribute(source_file,'long_name',var_name)
                if ln:
                    var.setncattr('long_name',ln)
                #Check whether a standard_name exists in the UM ancilliary file and adds  it to UGRID if it exists. 
                sn = get_attribute(source_file,'standard_name',var_name)
                if sn:
                    var.setncattr('standard_name',sn)
                #Adding the stash attribute 
                ums = get_attribute(source_file,'um_stash_source',var_name)
                if ums:
                    var.setncattr('um_stash_source',ums)
                stscode = get_attribute(source_file,'stashcode',var_name)
                if stscode:
                    var.setncattr('stashcode',stscode)

        #Add global attributes
        if is_netcdf(source_file):
            hist = get_attribute(source_file,'history')
            um_vers = get_attribute(source_file,'um_version')
            if um_vers:
                ds.setncattr('um_version',um_vers)
            if hist:
                updated_history = append_history(source_file,output_file,mesh_file,hist)
        else:
            updated_history = append_history(source_file,output_file,mesh_file)
            ds.setncattr('history',updated_history)
            ds.um_version = "9.0"
        ds.grid_staggering = "6"
        ds.source = "Data from Met Office Unified Model"
        ds.Conventions = "UGRID-1.0"

def main(mesh_file, source_file, outfile_path):
    """
    Main function to generate UGRID ancillary files based on input mesh and source_file.
    
    Parameters:
    mesh_file (str): Path to the input mesh file.
    source_file (str): Path to the source_file file (UM ancillary file).
    outfile_path (str): Path to the output directory.
    """

    # Load the UGRID dataset (UM ancillary file)
    data_cube = iris.load(source_file)

    # Get the cube names from the input UM ancillary file
    varnames = get_cube_names(data_cube)

    # Find the maximum number of dimensions in the file
    ndim_file = find_max_dimensions(data_cube)

    # Generate the output file name and ensure output directory exists
    if not os.path.exists(outfile_path):
        os.makedirs(outfile_path)

    tempfile = create_outfile_name(source_file, outfile_path)

    print(f"Output will be in the directory: {outfile_path}")

    # Avoid conflicts with an existing file
    if os.path.exists(tempfile):
        os.remove(tempfile)

    # Create the UGRID ancillary file
    make_ugrid_ancil(tempfile, varnames, mesh_file, source_file, ndim_file)

if __name__ == "__main__":
    # Get environment variables
    mesh_file=os.environ.get("mesh_file")
    source_file=os.environ.get("source")
    outfile_path=os.environ.get("outdir")

    # Call the main function with parsed arguments
    main(mesh_file, source_file, outfile_path)
