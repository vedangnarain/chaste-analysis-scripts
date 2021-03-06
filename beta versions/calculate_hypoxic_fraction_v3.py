#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Created on Sun May  9 22:09:58 2021

@author: Vedang Narain (vedang.narain@msdtc.ox.ac.uk)

Calculate Hypoxic Fraction (Dichotomous Network)

Tested in Python 3.7.4.

Version 3: Use contour plots.

"""

# =============================================================================
# LIBRARIES & INITIALISATION
# =============================================================================

# Initialise libraries
from collections import deque
import matplotlib.colors as colors
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np
import pandas as pd
import scipy
import time
import vtk
from vtk.util.numpy_support import vtk_to_numpy

# Starts stopwatch to clock execution time
start_time = time.time()

# =============================================================================
# FUNCTIONS
# =============================================================================

# Define a function to read a .vti file and return the field distribution
def get_vti_data(input_filename):
    
    # Import the file
    extension = input_filename.split('.').pop()
    reader = None
    if extension == 'vtk':
        reader = vtk.vtkDataSetReader() 
    elif extension == 'vti':
        reader = vtk.vtkXMLImageDataReader() 
    else:
        raise RuntimeError('Unknown File Type: %s ' % input_filename)
    reader.SetFileName( "%s" % (input_filename) ) 
    reader.Update()
    image_data = reader.GetOutput()
    
    # Extract the dimensions, spacing, and origin
    spacing = image_data.GetSpacing()
    
    # Extract the point values 
    field_point_data = image_data.GetPointData() 
    field_values = vtk_to_numpy(field_point_data.GetArray(0)) 
    
    # Get the coordinates of each point
    position_list = deque()
    for index in range(len(field_values)):  # do something 
        position = image_data.GetPoint(index)
        position_list.append(position)
    position_array = np.array(position_list)
    
    # Return the field distribution
    distribution_array = np.column_stack((position_array,field_values))
    distribution = pd.DataFrame(data=distribution_array[:,[0,1,3]], columns=["x", "y", "oxygen"])
    return distribution, spacing#, dimensions, origin

# Define a function to return a field and basic stats for display
def get_field(paraview_data):
    
    # Change the data type
    paraview_data = paraview_data.astype('float32')
    
    # Generates pair plots
    #sns.pairplot(dataset[['x', 'y', 'conc']], diag_kind="kde")
    
    # Calculate concentration statistics
    O2_stats = paraview_data['oxygen'].describe()
    
    # Downsample data if needed
    paraview_data = paraview_data[::int(1)]
    
    # Convert dataframe into NumPy matrix
    mat = paraview_data.to_numpy()
    
    # Get the x and y axes
    x = np.unique(mat[:,0])
    y = np.unique(mat[:,1])
    
    # Create a mesh from the x and y axes 
    X,Y = np.meshgrid(x, y)
    
    # Interpolate the concentration values over the mesh
    Z = scipy.interpolate.griddata((mat[:,0], mat[:,1]), mat[:,2], (X,Y), method='nearest')

    # Return the oxygen stats
    return Z, O2_stats

# Define a function to get the middle portion of the field
def get_middle_portion(node_file_path, field_dataset, middle_generation_number):
    reader = vtk.vtkXMLPolyDataReader()
    reader.SetFileName(node_file_path)
    reader.Update()
    polydata = reader.GetOutput()
    points = polydata.GetPoints()
    array = points.GetData()
    point_coordinates = vtk_to_numpy(array)
    generation_coordinates = np.unique(point_coordinates[:,0])
    x_start = generation_coordinates[middle_generation_number-1]
    x_end = generation_coordinates[-middle_generation_number]
    field_dataset = field_dataset[(field_dataset['x'] >= int(x_start)) & (field_dataset['x'] <= int(x_end))]
    return field_dataset
#    return vessel_network, oxygen_distribution, middle_x

# Define a function to read a file and return the hypoxic fraction
def get_hypoxic_fraction(solver_name, alpha_value, radius_threshold, hypoxic_threshold, plot=0):    
    
    # Set the file path
    file_path = '/Users/vedang/Simulations/Haematocrit Solver Comparisons/TestDichotomousNetwork4SolversAlpha1.4/' \
    + solver_name + 'Haematocrit/Alpha' + alpha_value + '/LambdaEquals4/RadiusThresholdEquals' \
    + radius_threshold + 'um/oxygen_solution_0.vti'
    
    # Import the data for the network
    field_data, field_spacing = get_vti_data(file_path)
    
    # Get the distribution in the middle of the field (replace with designated file)
    middle_field = get_middle_portion('/Users/vedang/Simulations/Haematocrit Solver Comparisons/TestDichotomousNetwork4SolversAlpha1.4/ConstantHaematocrit/Alpha1/LambdaEquals4/RadiusThresholdEquals0um/FinalHaematocrit.vtp', field_data, 6)
    
    # Plot the O2 distribution
    if plot==1:
        # Get the O2 mesh for plots and stats
        O2_field, O2_stats = get_field(middle_field)
        fig = plt.figure()
        ax = plt.axes()
        colour_map = plt.cm.get_cmap('jet')
        plt.suptitle('O$_2$ distribution generated by the ' + solver_name + ' solver in the dichotomous vessel network with ?? = ' + alpha_value + ' and radius threshold = ' + radius_threshold + '  ??m (1 unit = ' + str(field_spacing [0]) + ' ??m)')
        ref_map = ax.imshow(O2_field, cmap=colour_map, origin='lower')
        fig.colorbar(ref_map, ax=ax, label='nM')
        plt.show()
    
    # Calculate the number of points below hypoxic threshold    
    hypoxic_points = (middle_field['oxygen'] < hypoxic_threshold).sum()
    
    # Get the number of total points
    number_of_points = 1
    for dim in np.shape(middle_field['oxygen']): number_of_points *= dim
    
    # Calculate the hypoxic fraction
    hypoxic_fraction = hypoxic_points/number_of_points
    
    # Return the hypoxic fraction
    return hypoxic_fraction

# Define a function to return the hypoxic fraction data for a solver
def get_hypoxic_fraction_stats(solver_name, alpha_list, radius_threshold_list, hypoxic_threshold):
    table = np.array([])
    for alpha_value in alpha_list:
        alpha_table = np.array([])
        for radius_threshold in radius_threshold_list:
            hypoxic_fraction = get_hypoxic_fraction(solver_name, alpha_value, radius_threshold, hypoxic_threshold)
            table_entry = np.array([float(alpha_value), float(radius_threshold), hypoxic_fraction])
            alpha_table = np.vstack([alpha_table, table_entry]) if alpha_table.size else table_entry
        table = np.hstack([table, alpha_table]) if table.size else alpha_table
    return table

# Define a function to plot a 3D plot for the hypoxic fraction
def plot_solver_stats(solver_data, solver_name, hypoxic_threshold):
    fig = plt.figure()
    ax = fig.gca(projection='3d')
    plt.gca().invert_xaxis()
    plt.suptitle(solver_name + ' haematocrit solver in the dichotomous vessel network (hypoxic threshold = ' + str(hypoxic_threshold) + ' nM )')
    ax.plot(solver_data[:,0], solver_data[:,1], solver_data[:,2])
    ax.plot(solver_data[:,3], solver_data[:,4], solver_data[:,5])
    ax.plot(solver_data[:,6], solver_data[:,7], solver_data[:,8])
    ax.plot(solver_data[:,9], solver_data[:,10], solver_data[:,11])
    ax.plot(solver_data[:,12], solver_data[:,13], solver_data[:,14])
    ax.set_xlabel('??')
    ax.set_ylabel('radius threshold (??m)')
    ax.set_zlabel('hypoxic fraction')
    ax.view_init(elev=40., azim=60)
    plt.show()
    
## Define a function to plot a contour plot for the hypoxic fraction
#def plot_contours(solver_data, solver_name, hypoxic_threshold, resolution=10):
#
#    # Prepare arrays
#    alphas = np.hstack([solver_data[:,0], solver_data[:,3], solver_data[:,6], solver_data[:,9], solver_data[:,12]])
#    thresholds = np.hstack([solver_data[:,1], solver_data[:,4], solver_data[:,7], solver_data[:,10], solver_data[:,13]])
#    oxygen_points = np.hstack([solver_data[:,2], solver_data[:,5], solver_data[:,8], solver_data[:,11], solver_data[:,14]])   
#    
#    # Get the x and y axes
#    x = np.unique(alphas)
#    y = np.unique(thresholds)
#    
#    # Create a mesh from the x and y axes 
#    X,Y = np.meshgrid(x, y)
#    
#    # Interpolate the concentration values over the mesh
#    Z = scipy.interpolate.griddata((alphas, thresholds), oxygen_points, (X,Y), method='nearest')
#    
#    # Plot the figure
#    fig = plt.figure()
#    ax = plt.axes()
#    plt.suptitle(solver_name + ' haematocrit solver in the dichotomous vessel network (hypoxic threshold = ' + str(hypoxic_threshold) + ' nM )')
#    ref_map = ax.contourf(X, Y, Z, resolution, cmap='RdGy')
#    ax.set_xlabel('??')
#    ax.set_ylabel('radius threshold (??m)')
#    fig.colorbar(ref_map, ax=ax, label= 'hypoxic fraction')
#    plt.show()
    
# Define a function to get data for a contour plot for the hypoxic fraction
def get_xyz(solver_data, solver_name, hypoxic_threshold):

    # Prepare arrays
    alphas = np.hstack([solver_data[:,0], solver_data[:,3], solver_data[:,6], solver_data[:,9], solver_data[:,12]])
    thresholds = np.hstack([solver_data[:,1], solver_data[:,4], solver_data[:,7], solver_data[:,10], solver_data[:,13]])
    oxygen_points = np.hstack([solver_data[:,2], solver_data[:,5], solver_data[:,8], solver_data[:,11], solver_data[:,14]])   
    
    # Get the x and y axes
    x = np.unique(alphas)
    y = np.unique(thresholds)
    
    # Create a mesh from the x and y axes 
    X,Y = np.meshgrid(x, y)
    
    # Interpolate the concentration values over the mesh
    Z = scipy.interpolate.griddata((alphas, thresholds), oxygen_points, (X,Y), method='nearest')
    
    # Return the arrays
    return X, Y, Z

# Define a function to plot the colour maps
def compare_contours(solver_name, alpha_list, radius_threshold_list, hypoxic_threshold_list):
    
    # Set the figure layout
    fig, axs = plt.subplots(2,3, figsize=(20, 10))
    fig.subplots_adjust(hspace = .5, wspace=.25)
    plt.suptitle(solver_name + ' haematocrit solver in the dichotomous vessel network')
    
    # Plot the contour maps
    axs = axs.ravel()
    for i in range(6):
        solver_data = get_hypoxic_fraction_stats(solver_name, alpha_list, radius_threshold_list, hypoxic_threshold_list[i])
        X, Y, Z = get_xyz(solver_data, solver_name, hypoxic_threshold_list[i])
        if i not in [0, 5]:  # if it's not the first or last plot, use it to map the colourbar
            ref_map = axs[i].contourf(X, Y, Z, resolution, cmap='RdGy', norm=norm, origin='lower') 
        else:
            axs[i].contourf(X, Y, Z, resolution, cmap='RdGy', norm=norm, origin='lower')
        axs[i].set_title('hypoxic threshold = ' + str(hypoxic_threshold_list[i]) + ' nM')
        axs[i].set_xlabel('??')
        axs[i].set_ylabel('radius threshold (??m)')
    fig.colorbar(ref_map, ax=axs, label='hypoxic fraction')
    plt.show()

# =============================================================================
# HYPOXIC FRACTION DATA
# =============================================================================

# Enter details to allow looping over folders
solver_list = ['Constant', 'Pries', 'Memory', 'Betteridge']
alpha_list = ['1', '1.1', '1.2', '1.3', '1.4']
max_radius = 35  #50
radius_threshold_list = [str(x) for x in range(max_radius + 1)]
#hypoxic_threshold = 7331.5  #O2_stats['25%'] # set hypoxia threshold (<0.1% mmHg is radioresistance, <2% is hypoxia)
hypoxic_threshold_list = [20000, 22000, 24000, 26000, 28000, 30000]
#
#for hypoxic_threshold in hypoxic_threshold_list:
#
#    # Get the hypoxic fraction data for solvers
#    constant_data = get_hypoxic_fraction_stats(solver_list[0], alpha_list, radius_threshold_list, hypoxic_threshold)
#    #pries_data = get_hypoxic_fraction_stats(solver_list[1], alpha_list, radius_threshold_list, hypoxic_threshold)
#    #memory_data = get_hypoxic_fraction_stats(solver_list[2], alpha_list, radius_threshold_list, hypoxic_threshold)
#    #betteridge_data = get_hypoxic_fraction_stats(solver_list[3], alpha_list, radius_threshold_list, hypoxic_threshold)
#    
#    '''
#    # Plot the data in 3D 
#    plot_solver_stats(constant_data, solver_list[0], hypoxic_threshold)
#    plot_solver_stats(pries_data, solver_list[1], hypoxic_threshold)
#    plot_solver_stats(memory_data, solver_list[2], hypoxic_threshold)
#    plot_solver_stats(betteridge_data, solver_list[3], hypoxic_threshold)
#    '''
#    
#    # Plot the data as contour plots 
#    plot_contours(constant_data, solver_list[0], hypoxic_threshold)
#    #plot_contours(pries_data, solver_list[1], hypoxic_threshold)
#    #plot_contours(memory_data, solver_list[2], hypoxic_threshold)
#    #plot_contours(betteridge_data, solver_list[3], hypoxic_threshold)
#    
#    
# Normalise the colourbar
lower_bound = 0  # get the overall min.
upper_bound = 1  # get the overall max.
resolution = 10  # set the resolution
bounds = np.linspace(lower_bound, upper_bound, 10)  # set a range and resolution
norm = colors.BoundaryNorm(boundaries=bounds, ncolors=256)  # normalise    
    
# Plot for a varying hypooxic threshold
for solver_name in solver_list:
    compare_contours(solver_name, alpha_list, radius_threshold_list, hypoxic_threshold_list)    

# =============================================================================
# TOOLS
# =============================================================================

'''

hypoxic_threshold = 28000  #O2_stats['25%'] # set hypoxia threshold (<0.1% mmHg is radioresistance, <2% is hypoxia)
solver_name = 'Pries'
radius_threshold = str(6)
alpha_value = '1.1'

solver_data = get_hypoxic_fraction_stats(solver_name, alpha_list, radius_threshold_list, hypoxic_threshold)
plot_solver_stats(solver_data, solver_name, hypoxic_threshold)
get_hypoxic_fraction(solver_name, alpha_value, radius_threshold, hypoxic_threshold, plot=1) 

'''

# prints execution time
print("\n--- Execution Time: %s seconds ---" % (time.time() - start_time))
