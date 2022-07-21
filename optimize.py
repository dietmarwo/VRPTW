"""Generate Solomons Benchmark solutions for the 
   Vehicles Benchmark Problem with Time Windows
   using https://github.com/dietmarwo/fast-cma-es.

See http://web.cba.neu.edu/~msolomon/problems.htm
"""

import numpy as np
import os
from numba import njit
from fcmaes.optimizer import crfmnes_bite, wrapper
from fcmaes import retry
from scipy.optimize import Bounds
from benchmark import Benchmark

@njit(fastmath=True)
def fitness_(seq, capacity, dtime, demands, readys, dues, services):
    n = len(seq)
    seq += 1
    sum_demand = 0
    sum_dtime = 0
    time = 0
    last = 0
    vehicles = 1
    for i in range(0, n+1):
        customer = seq[i] if i < n else 0
        demand = demands[customer]
        ready = readys[customer]
        due = dues[customer]
        service = services[customer]
        if sum_demand + demand > capacity or \
                time + dtime[last, customer] > due: 
            # end vehicle tour, return to base
            dt = dtime[last, 0]
            sum_dtime += dt
            time = 0
            sum_demand = 0
            vehicles += 1
            last = 0
        # go to customer
        dt = dtime[last, customer]
        time += dt 
        if time < ready:
            time = ready
        time += service       
        sum_demand += demand
        sum_dtime += dt
        last = customer
    return np.array([float(vehicles), sum_dtime])
       
class Optimizer():
    def __init__(self, problem):
        self.problem = problem
        self.benchmark = Benchmark(problem)
        self.dim = len(self.benchmark.demand) - 1
        self.bounds = Bounds([0]*self.dim, [1]*self.dim)

    def fitness(self, x):
        fit = fitness_(np.argsort(x), self.benchmark.capacity, \
                    self.benchmark.dtime, self.benchmark.demand, \
                    self.benchmark.ready, self.benchmark.due, self.benchmark.service)   
        # increasing the vehicle weight doesn't help much with the hierarchical objective
        return 10*fit[0] + fit[1] 
       
def optimize_so(problem, opt, num_retries = 64):
    optimizer = Optimizer(problem) 
    ret = retry.minimize(wrapper(optimizer.fitness), 
                        optimizer.bounds, num_retries = num_retries, optimizer=opt)
    optimizer.benchmark.dump_opt(np.argsort(ret.x), ret.fun, problem, 'cont')

def opt_dir(dir):
    files = os.listdir(dir)
    files.sort()
    for file in files:
        problem = file.split('.')[0]
        # used to generate the results
        #optimize_so(problem, crfmnes_bite(10000000, popsize=500, M=6), num_retries = 64)
        # sufficient for the clustered problem instances
        optimize_so(problem, crfmnes_bite(1000000, popsize=500, M=6), num_retries = 64)
 
if __name__ == '__main__':
    opt_dir('problems')
     