"""Parsing and solution generation for
   Solomons Benchmark for the Vehicles Benchmark Problem with Time Windows.

See http://web.cba.neu.edu/~msolomon/problems.htm
"""

import numpy as np
import os

def parse_problem(filename, tfac = 1):
    with open(filename) as csvfile:
        lines = csvfile.readlines()
        demand = []
        coord = [] 
        ready = [] 
        due = [] 
        service = []
        for line in lines:
            row = line.split()
            if len(row) == 2 and row[0][0].isdigit():
                number = int(row[0])
                capacity = int(row[1])                
            if len(row) < 5 or not row[0][0].isdigit():
                continue
            coord.append(np.array([tfac*float(row[1]), tfac*float(row[2])])) 
            demand.append(float(row[3]))
            ready.append(tfac*float(row[4]))
            due.append(tfac*float(row[5]))
            service.append(tfac*float(row[6]))
    n = len(demand)
    dtimes = np.zeros((n,n))
    for i in range(n):
        for j in range(n):
            dtimes[i,j] = np.linalg.norm(coord[i] - coord[j])
    return number, capacity, dtimes, np.array(demand), np.array(ready),\
                np.array(due), np.array(service)
    
def parse_solution(filename):
    with open(filename) as csvfile:
        lines = csvfile.readlines()
        routes = []
        for line in lines:
            row = line.split()                
            if len(row) < 4 or not row[1][0].isdigit():
                continue
            routes.append([int(r) for r in row[3:]])
    return routes

class Benchmark():
    def __init__(self, problem, tfac = 1):
        self.problem = problem
        filename = 'problems/' + problem + '.txt'
        self.vnumber, self.capacity, self.dtime, self.demand, self.ready,\
            self.due, self.service = parse_problem(filename, tfac)
        self.number = len(self.demand) - 1
    
    def evaluate(self, filename):
        routes = parse_solution(filename)
        visited = sum([len(r) for r in routes])
        n = len(self.demand) - 1
        vehicle_i = 0 # vehicle index
        customer_i = 0  # customer for vehicle index
        sum_dtime = 0
        last_customer = 0
        sum_demand = 0
        time = 0
        switch = False
        for i in range(0, n + 1):
            customer = routes[vehicle_i][customer_i] if i < n else 0
            demand = self.demand[customer]
            ready = self.ready[customer]
            due = self.due[customer]
            service = self.service[customer]
            if switch:
                dtime = self.dtime[last_customer, 0]
                sum_dtime += dtime
                time = 0 # vehicle starts at time 0
                sum_demand = 0
                last_customer = 0
            if sum_demand + demand > self.capacity or \
                    time + self.dtime[last_customer, customer] > due:
                # capacity overload or due time missed?
                print("error", last_customer, customer, self.dtime[last_customer, customer], \
                      sum_demand + demand, self.capacity, time + self.dtime[last_customer, customer], due) 
            dtime = self.dtime[last_customer, customer]
            time += dtime 
            if time < ready: # wait until ready
                time = ready
            time += service
            sum_demand += demand
            sum_dtime += dtime
            last_customer = customer
            customer_i += 1
            switch = False
            if i < n and customer_i >= len(routes[vehicle_i]):
                # route ends, use new vehicle
                vehicle_i += 1
                customer_i = 0
                switch = True
        return vehicle_i, sum_dtime, visited, routes
    
    def dump_opt(self, seq, y, problem, opt_name=''):
        lines = []
        from datetime import datetime
        lines.append('Instance Name : ' + self.problem + '\n')
        lines.append('Date : ' + str(datetime.today().date()) + '\n')
        lines.append('Solution\n')
        n = len(seq)
        seq += 1
        sum_dtime = 0
        last = 0
        vehicles = 1
        sum_demand = 0
        time = 0
        tour = []
        for i in range(0, n+1):
            customer = seq[i] if i < n else 0
            demand = self.demand[customer]
            ready = self.ready[customer]
            due = self.due[customer]
            service = self.service[customer]
            if sum_demand + demand > self.capacity or \
                        time + self.dtime[last, customer] > due: 
                dt = self. dtime[last, 0]
                sum_dtime += dt
                time = 0
                lines.append('Route ' + str(vehicles) + ' : ' + ' '.join(map(str, tour)) + '\n')
                sum_demand = 0
                vehicles += 1
                tour = []
                last = 0
            dt = self.dtime[last, customer]
            time += dt 
            if time < ready:
                time = ready
            time += service
            sum_demand += demand
            sum_dtime += dt
            if customer != 0:
                tour.append(customer)
            last = customer
        print ("vehicles ", vehicles-1, "demands", sum_demand, "dtime", sum_dtime)
        filename = 'solutions/' + opt_name + '_' + problem + '.txt'
        with open(filename, 'w') as f:
            f.writelines(lines)
        print(''.join(lines))

    def dump_or(self, data, manager, routing, solution, opt_name='or-tools'):
        lines = []
        from datetime import datetime
        lines.append('Instance Name : ' + self.problem + '\n')
        lines.append('Date : ' + str(datetime.today().date()) + '\n')
        lines.append('Solution\n')
        routes = []
        for vehicle_id in range(data['num_vehicles']):
            route = []
            index = routing.Start(vehicle_id)
            while not routing.IsEnd(index):
                if index != routing.Start(vehicle_id):
                    route.append(manager.IndexToNode(index))
                index = solution.Value(routing.NextVar(index))
            if routing.IsEnd(index) and len(route) > 0:
                routes.append(route)
        n = self.number
        ri = 0
        ci = 0
        sum_dtime = 0
        last = 0
        vehicles = 1
        sum_demand = 0
        time = 0
        tour = []
        switch = False
        for i in range(0, n+1):
            customer = routes[ri][ci] if i < n else 0
            demand = self.demand[customer]
            ready = self.ready[customer]
            service = self.service[customer]
            if switch:
                dt = self.dtime[last, 0]
                sum_dtime += dt
                time = 0
                lines.append('Route ' + str(vehicles) + ' : ' + ' '.join(map(str, tour)) + '\n')
                sum_demand = 0
                vehicles += 1
                tour = []
                last = 0
            dt = self.dtime[last, customer]
            time += dt 
            if time < ready:
                time = ready
            time += service
            sum_demand += demand
            sum_dtime += dt
            if customer != 0:
                tour.append(customer)
            last = customer
            ci += 1
            switch = False
            if i < n and ci >= len(routes[ri]):
                ri += 1
                ci = 0
                switch = True
        visited = sum([len(r) for r in routes])
        print ("vehicles ", vehicles-1, "demands", sum_demand, "dtime", sum_dtime, "visited", visited)
        filename = 'solutions/' + opt_name + '_' + self.problem + '.txt'
        with open(filename, 'w') as f:
            f.writelines(lines)
        print(''.join(lines))
    
def evaluate_dir(dir):
    files = os.listdir(dir)
    files.sort()
    vmap = {}
    dmap = {}
    vkmap = {}
    dkmap = {}    
    for file in files:
        problem = file.split('.')[0]
        bench = Benchmark(problem) 
        vehicles, sum_dtime, visited, routes = bench.evaluate(dir + '/' + file)
        #print(file, vehicles, sum_dtime)
        vmap[problem] = vehicles
        dmap[problem] = sum_dtime
        key = problem[:3] if problem.startswith('rc') else problem[:2]
        if not key in vkmap:
            vkmap[key] = []
            dkmap[key] = []
        vkmap[key].append(vehicles)
        dkmap[key].append(sum_dtime)
    for key in vkmap:
        vkmap[key] = sum(vkmap[key])/len(vkmap[key])
        dkmap[key] = sum(dkmap[key])/len(dkmap[key])
    return vmap, dmap, vkmap, dkmap

def summary(dirs):
    maps = []
    for dir in dirs:
        vmap, dmap, vkmap, dkmap = evaluate_dir(dir)
        maps.append([dir, vmap, dmap, vkmap, dkmap])
    keys = [k.upper() for k in vkmap.keys()]
    print('|' + 'optimizer' + '|' +  '|'.join(keys))
    for i in range(len(maps)):
        dir = maps[i][0]
        vkmap = maps[i][3]
        vals = '|'.join([str(round(vkmap[k],2)) for k in vkmap])
        print('|' + dir + '|' + vals)
    vals = '|'.join([str(round(100*(maps[1][3][k] / maps[0][3][k] - 1),2)) for k in vkmap])
    print('|' + '%difference' + '|' + vals)
    print('|' + 'optimizer' + '|' +  '|'.join(keys))
    for i in range(len(maps)):
        dir = maps[i][0]
        dkmap = maps[i][4]
        vals = '|'.join([str(round(dkmap[k],1)) for k in dkmap])
        print('|' + dir + '|' + vals)
    vals = '|'.join([str(round(100*(maps[1][4][k] / maps[0][4][k] - 1),2)) for k in vkmap])
    print('|' + '%difference' + '|' + vals)

def compare(dir1, dir2):
    vmap1, dmap1, _, _ = evaluate_dir(dir1)
    vmap2, dmap2, _, _ = evaluate_dir(dir2)
    probs = list(vmap2.keys())
    probs.sort()
    print('|problem |vehicles | distance | % vehicles difference | % distance difference')
    for problem in probs:
        v1 = vmap1[problem] if problem in vmap1 else None
        v2 = vmap2[problem]
        d1 = dmap1[problem] if problem in dmap1 else None
        d2 = dmap2[problem]
        vperc = "???" if v1 is None else str(round(100*(v2 / v1 - 1), 2))
        dperc = "???" if d1 is None else str(round(100*(d2 / d1 - 1), 2))
        print('|' + problem + '|' + str(v2) + '|' + str(round(d2,1)) + '|' + vperc + '|' + dperc)

            
if __name__ == '__main__':
    summary(['sintef', 'or_vnum'])
    summary(['sintef', 'or_no_vnum'])
    summary(['or_no_vnum', 'crfm_bite'])
    compare('sintef', 'or_vnum')
    compare('sintef', 'or_no_vnum')
    compare('or_no_vnum', 'crfm_bite')
