"""Generate Solomons Benchmark solutions for the 
   Vehicles Benchmark Problem with Time Windows
   using https://github.com/google/or-tools.

See http://web.cba.neu.edu/~msolomon/problems.htm

Derived from the code at https://developers.google.com/optimization/routing/vrp

"""

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
# https://github.com/google/or-tools/blob/stable/ortools/constraint_solver/samples/cvrptw.py

from functools import partial
from multiprocessing import Pool, freeze_support
import os
from benchmark import Benchmark

# or-tools seems to convert the distance to integers, we mitigate 
# by multiplying with time_fac
time_fac = 500 
max_vehicles = 40

# hierarchical objective setting
#fixed_cost_all_vehicles = 1000000

# single objective setting
fixed_cost_all_vehicles = 1000
 
def print_solution(data, manager, routing, solution):
    """Prints solution on console."""
    print(f'Objective: {solution.ObjectiveValue()}')
    time_dimension = routing.GetDimensionOrDie('Time')
    total_time = 0
    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        plan_output = 'Route for vehicle {}:\n'.format(vehicle_id)
        while not routing.IsEnd(index):
            time_var = time_dimension.CumulVar(index)
            plan_output += '{0} Time({1},{2}) -> '.format(
                manager.IndexToNode(index), solution.Min(time_var),
                solution.Max(time_var))
            index = solution.Value(routing.NextVar(index))
        time_var = time_dimension.CumulVar(index)
        plan_output += '{0} Time({1},{2})\n'.format(manager.IndexToNode(index),
                                                    solution.Min(time_var),
                                                    solution.Max(time_var))
        plan_output += 'Time of the route: {}min\n'.format(
            solution.Min(time_var))
        print(plan_output)
        total_time += solution.Min(time_var)
    print('Total time of all routes: {}min'.format(total_time))

def solve(problem, max_time = 1000):
    """Solve the VRP with time windows."""
    # Instantiate the data problem.
    data = {}
    
    bench = Benchmark(problem, time_fac)
    num_locations = bench.number + 1
    data['time_matrix'] = bench.dtime
    data['num_vehicles'] = max_vehicles
    data['depot'] = 0
    data['time_windows'] = [(int(bench.ready[i]), int(bench.due[i])) for i in range(num_locations)]
    data['demands'] = bench.demand
    data['vehicle_capacities'] = [bench.capacity]*data['num_vehicles']
    
    # Create the routing index manager.
    manager = pywrapcp.RoutingIndexManager(len(data['time_matrix']),
                                           data['num_vehicles'], data['depot'])

    # Create Benchmark Model.
    routing = pywrapcp.RoutingModel(manager)

    def demand_callback(from_index):
        """Returns the demand of the node."""
        # Convert from routing variable Index to demands NodeIndex.
        from_node = manager.IndexToNode(from_index)
        return data['demands'][from_node]
    
    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        0,  # null capacity slack
        data['vehicle_capacities'],  # vehicle maximum capacities
        True,  # start cumul to zero
        'Capacity')

    # Create and register a transit callback.
    def time_callback(from_index, to_index):
        """Returns the travel time between the two nodes."""
        # Convert from routing variable Index to time matrix NodeIndex.
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        dtime = bench.service[from_node] + bench.dtime[from_node][to_node]
        return dtime

    transit_callback_index = routing.RegisterTransitCallback(time_callback)

    # Define cost of each arc.
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Add Time Windows constraint.
    time = 'Time'
    routing.AddDimension(
        transit_callback_index,
        3000000,  # allow waiting time
        3000000,  # maximum time per vehicle
        False,  # Don't force start cumul to zero.
        time)
    time_dimension = routing.GetDimensionOrDie(time)
    # Add time window constraints for each location except depot.
    for location_idx, time_window in enumerate(data['time_windows']):
        if location_idx == data['depot']:
            continue
        index = manager.NodeToIndex(location_idx)
        time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])
    # Add time window constraints for each vehicle start node.
    depot_idx = data['depot']
    for vehicle_id in range(data['num_vehicles']):
        index = routing.Start(vehicle_id)
        time_dimension.CumulVar(index).SetRange(
            data['time_windows'][depot_idx][0],
            data['time_windows'][depot_idx][1])

    # Instantiate route start and end times to produce feasible times.
    for i in range(data['num_vehicles']):
        routing.AddVariableMinimizedByFinalizer(
            time_dimension.CumulVar(routing.Start(i)))
        routing.AddVariableMinimizedByFinalizer(
            time_dimension.CumulVar(routing.End(i)))

    routing.SetFixedCostOfAllVehicles(fixed_cost_all_vehicles)
    # Setting first solution heuristic.
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
    search_parameters.time_limit.seconds = max_time
    search_parameters.log_search = False
    # Solve the problem.
    solution = routing.SolveWithParameters(search_parameters)

    # Print solution on console.
    if solution:
        print_solution(data, manager, routing, solution)
        bench.dump_or(data, manager, routing, solution, opt_name='or-tools')

# lets solve 12 problems in parallel

def opt_dir(dir, max_time = 3*3600, workers=12):
    freeze_support()
    files = os.listdir(dir)
    files.sort()
    problems = [file.split('.')[0] for file in files]
    with Pool(processes=workers) as pool:
        pool.map(partial(solve, max_time = max_time), problems)

def main():
    opt_dir('problems', max_time = 30)
    #opt_dir('problems', max_time = 3*3600)
    #solve('r101', max_time = 30)

if __name__ == '__main__':
    main()