# -*- coding: utf-8 -*-

from __future__ import unicode_literals
from shapely.geometry import LineString

class Roadlist:

    def __init__(self, ridge_vertices, vertex_positions):
        self.vertex_positions = vertex_positions
        self.ridges = ridge_vertices
        self.intersection_map = self.generate_intersection_map(self.ridges)
        self.incomplete_roads = [[],[]] # Fully open, half open
        self.complete_roads = []
        # Initially add all segments to roads
        for ridge in self.ridges:
            self.add_segment_to_road(ridge)
        # After all segments are added, all roads should be at least partially closed
        # We can't complete a fully open road with another fully open road
        if self.incomplete_roads[0]:
            raise IncompleteRoadError
        # Cleanup incomplete roads
        self.close_remaining_roads()
        if self.incomplete_roads[1]:
            raise IncompleteRoadError

    def generate_intersection_map(self, endpoints):
        intersection_map = dict()
        for ridge in endpoints:
            if ridge[0] in intersection_map:
                intersection_map[ridge[0]] += 1 if intersection_map[ridge[0]] < 3 else 0
            else:
                intersection_map[ridge[0]] = 1
            if ridge[-1] in intersection_map:
                intersection_map[ridge[-1]] += 1 if intersection_map[ridge[-1]] < 3 else 0
            else:
                intersection_map[ridge[-1]] = 1
        return intersection_map

    def find_road_by_vertex(self, vertex):
        '''Finds which road segment a vertex belongs to

        Assumes that vertex can only belong to one road segment 

        :param vertex : Index of voronoi vertex
            :py:class: `int`
        

        :return: tuple indicating which list the road segment is in, 
        index of road segment in list, and index indicating which end
        of segment vertex belongs to.
        '''

        # Look in fully open roads
        fully_open_roads = self.incomplete_roads[0]
        half_open_roads = self.incomplete_roads[1]
        if fully_open_roads:
            for i, road in enumerate(fully_open_roads):
                if road[0] == vertex:
                    return (0, i, 0)
                elif road[-1] == vertex:
                    return (0, i, -1)
        if half_open_roads:
            for i, road in enumerate(half_open_roads):
                if road[0] == vertex:
                    return (1,i, 0)    
        return (-1,0,0)

    def add_segment_to_road(self, seg):
        intersection_values = [self.intersection_map[seg[0]],self.intersection_map[seg[-1]]]
        if intersection_values == [2,2]:
            # Both middle segments, try to connect both ends
            road_list, road, position = [],[],[]
            for vertex in seg:
                rl, r, p = self.find_road_by_vertex(vertex)
                road_list.append(rl)
                road.append(r)
                position.append(p)
            if road_list[0] != -1 and road_list[1] != -1:
                # Both segments can be connected
                # Pop the segments off their respective lists
                road1 = self.incomplete_roads[road_list[0]].pop(road[0])
                if road_list[0] == road_list[1]:
                    road[1] = road[1] if road[1] < road[0] else road[1]-1
                road2 = self.incomplete_roads[road_list[1]].pop(road[1])
                if position == [0,0]:
                    # Connecting front to front
                    current_road = road1[::-1] + road2
                elif position == [-1,-1]:
                    # Connecting back to back
                    current_road = road1 + road2[::-1]
                elif position == [0, -1]:
                    # Connecting front of first to back of second
                    current_road = road2 + road1
                elif position == [-1,0]:
                    # Connecting back of first to front of second
                    current_road = road1 + road2
                # Figure out which list this should be added to
                if road_list == [0,0]:
                    # Both fully open -> combination is fully open
                    self.incomplete_roads[0].append(current_road)
                    return
                elif road_list == [1,1]:
                    # Both roads half closed -> combination is fully closed
                    self.complete_roads.append(current_road)
                    return
                # One road was half closed -> combination is half closed
                # Need to maintain class invariant sort of half closed roads
                elif road_list == [0, 1]:
                    self.incomplete_roads[1].append(current_road)
                    return
                elif road_list == [1,0]:
                    if position[1] == -1:
                        self.incomplete_roads[1].append(current_road)
                        return
                    elif position[1] == 0:
                        self.incomplete_roads[1].append(current_road[::-1])
                    return
            elif road_list[0] == -1 and road_list[1] == -1:
                # Neither point can be added to an existing segment
                self.incomplete_roads[0].append(seg.copy())
                return
            elif road_list[0] == -1:
                # Second point can be connected
                if position[1] == 0:
                    self.incomplete_roads[road_list[1]][road[1]].insert(0,seg[0])
                    return
                else:
                    self.incomplete_roads[road_list[1]][road[1]].append(seg[0])
                    return
            elif road_list[1] == -1:
                if position[0] == 0:
                    self.incomplete_roads[road_list[0]][road[0]].insert(0,seg[1])
                    return
                else:
                    self.incomplete_roads[road_list[0]][road[0]].append(seg[1])
                    return

        elif 2 in intersection_values:
            seg = seg.copy()
            if intersection_values[1] == 2:
                seg = seg[::-1]
            # 0 can be connected, 1 is an end
            road_list, road, position = self.find_road_by_vertex(seg[0])
            if road_list == -1:
                # Not on any list yet
                self.incomplete_roads[1].append(seg)
                return
            else:
                current_road = self.incomplete_roads[road_list].pop(road)
                
                if position == 0:
                    current_road.insert(0, seg[1])
                    current_road = current_road[::-1] #Shift end to back of list
                else:
                    current_road.append(seg[1])
                if road_list == 0:
                    self.incomplete_roads[1].append(current_road)
                    return
                elif road_list == 1:
                    self.complete_roads.append(current_road)
                    return
        
        elif 1 in intersection_values:
            # This is a short segment with a dead end, ignore it
            pass
        elif 3 in intersection_values:
            # Short segment that connects two intersections
            # TODO: collapse the two intersection this segment joins into one point
            self.complete_roads.append(seg.copy())
        else:
            print("Logic Error")

    def filter_dead_ends(self):
        road_endpoints = endpoints(self.complete_roads)
        intersection_map = self.generate_intersection_map(road_endpoints)
        for road in self.complete_roads:
            if intersection_map[road[0]] == 1 or intersection_map[road[-1]] == 1:
                road_points = [self.vertex_positions[v] for v in road]
                road_geometry = LineString(road_points)
                if road_geometry.length < 20:
                    self.complete_roads.remove(road)


    def close_remaining_roads(self):
        if len(self.incomplete_roads[1])%2 != 0:
            # Cannot have an odd number of roads
            raise IncompleteRoadError
        while self.incomplete_roads[1]:
            current_road = self.incomplete_roads[1].pop(0)
            for i, road in enumerate(self.incomplete_roads[1]):
                if road[0] == current_road[0]:
                    current_road = road[::-1] + current_road
                    self.incomplete_roads[1].pop(i)
                    self.complete_roads.append(current_road)
                    break

def endpoints(roads):
    endpoints = []
    for road in roads:
        endpoints.append([road[0],road[-1]])
    return endpoints

def explode_ridges(ridges):
    result = []
    while ridges:
        ridge = ridges.pop(0)
        if len(ridge) > 2:
            exploded_ridge = []
            for i in range(1,len(ridge)):
                exploded_ridge.append((ridge[i-1],ridge[i]))
            result.extend(exploded_ridge)
        else:
            result.append(tuple(ridge))
    result = list(set(result)) # Remove duplicates
    result = [list(ridge) for ridge in result] #Cast back to list of lists
    return result

class IncompleteRoadError(Exception):
    """Error raised when a road cannot be completed
    """
    def __init__(self):
        super().__init__("Roads exist without endpoints")