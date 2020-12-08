from pacman import Directions
from game import Agent
import api
import random
import game
import util

CORNER_VAL = 100.0
FOOD_VAL = 10.0
CAPSULE_VAL = 50.0
GHOST_VAL = -500.0
EDIBLE_GHOST_VAL = 200.0
SMALL_GAMMA = 0.7
MEDIUM_GAMMA = 0.9
SMALL_BUFFER = 2
MEDIUM_BUFFER = 3
ADJ_TEMPLATE = {"N": (0,1), "S": (0,-1), "E": (1,0), "W": (-1,0)}

class MDPAgent(Agent):
    """
    Initialise important variables for use through the object
    @param self: the class itself
    """
    def __init__(self):
        # Initialise dictionaries used in value iteration 
        self.rewardDict = {}
        self.stateDict = {}
        self.utilDict = {}
        # initialise map variable to store each coordinate in the grid
        self.map = set()
        # initialise variables to store API values
        self.walls = set()
        self.ghostLocs = None
        self.pacman = self.food = self.capsules = self.ghostStates = None
        # initialise variables to store the layout's maximum width and height 
        self.maxW = self.maxH = -1
        # initialise discount factor and ghost buffer values with default values
        # when layout other than smallGrid or mediumClassic is used
        self.discountFactor = 0.7
        self.ghostBuffer = 2
        # counter to keep track of how many games have been played
        self.games = 1
    
    """
    Populate the map and set unique values if layout is smallGrid or mediumClassic
    @param self: the class itself
    @param state: the current game state
    """
    def registerInitialState(self, state):
        self.walls = set(api.walls(state))
        self.populateGrid(state)
        if (self.maxW, self.maxH) == (19,10):
            self.discountFactor = MEDIUM_GAMMA
            self.ghostBuffer = MEDIUM_BUFFER
        elif (self.maxW, self.maxH) == (6,6):
            self.discountFactor = SMALL_GAMMA
            self.ghostBuffer = SMALL_BUFFER
    
    """
    Populate a map of the layout through finding out the maximum height and width
    @param self: the class itself
    @param state: the current game state
    """
    def populateGrid(self, state):
        corners = api.corners(state)
        # work out maximum width and height of map
        for c in corners:
            if c[0] > self.maxW: self.maxW = c[0]
            if c[1] > self.maxH: self.maxH = c[1]
        width = range(0, self.maxW)
        height = range(0, self.maxH)
        self.map = set((x, y) for x in width for y in height)

    """
    Populate the states dictionary where each state is a key, and its possible future states its value
    @param self: the class itself
    """
    def mapNeighbourStates(self):
        states = dict.fromkeys(self.rewardDict.keys())
        for k in states.keys():
            adjs = self.findNeighbours(k)
            states[k] = {
                "N": [adjs["N"], adjs["E"], adjs["W"]],
                "S": [adjs["S"], adjs["E"], adjs["W"]],
                "E": [adjs["E"], adjs["N"], adjs["S"]],
                "W": [adjs["W"], adjs["N"], adjs["S"]]
            }
        self.stateDict = states

    """
    Calculate a given state, c's, adjacent states
    @param self: the class itself
    @param c: a tuple representing the state
    @return a dictionary containing the adjacent states of c
    """
    def findNeighbours(self, c):
        adj, walls = ADJ_TEMPLATE, self.walls
        nc = (c[0]+adj["N"][0], c[1]+adj["N"][1])
        sc = (c[0]+adj["S"][0], c[1]+adj["S"][1])
        ec = (c[0]+adj["E"][0], c[1]+adj["E"][1])
        wc = (c[0]+adj["W"][0], c[1]+adj["W"][1])
        if nc in walls: nc = c
        if sc in walls: sc = c
        if ec in walls: ec = c
        if wc in walls: wc = c
        return {"N": nc, "S": sc, "E": ec, "W": wc}
    
    """
    Reset the values of several variables to their initial state
    @param self: the class itself
    @param state: the current game state
    """
    def final(self, state):
        self.rewardDict = self.stateDict = self.utilDict = {}
        self.pacman = self.food = self.capsules = self.ghostStates = None
        self.games += 1
        print "round: "+str(self.games)

    """
    Decides which action pacman must take next
    @param self: the class itself
    @param state: the current game state
    @return the direction pacman must take
    """
    def getAction(self, state):
        self.updateValues(state)
        self.mapRewards()
        if not self.stateDict: self.mapNeighbourStates()
        convergedUtilities = self.valueIteration()
        nextMove = self.findNextMove(convergedUtilities)
        legal = api.legalActions(state)
        return api.makeMove(nextMove, legal)
    
    """
    Updates several variables representing information about the world at pacman's current state
    @param self: the class itself
    @param state: the current game state
    """
    def updateValues(self, state):
        self.pacman = api.whereAmI(state)
        self.food = api.food(state)
        self.capsules = api.capsules(state)
        self.ghostStates = api.ghostStates(state)

    """
    Initialise dictionary for rewards used in value iteration
    @param self: the class itself
    """
    def mapRewards(self):
        food, capsules, ghosts = self.food, self.capsules, self.ghostStates
        self.rewardDict = {k: -1.0 for k in self.map if k not in self.walls}
        foodDict = {k: FOOD_VAL for k, v in self.rewardDict.items() if k in food}
        capsuleDict = {k: CAPSULE_VAL for k, v in self.rewardDict.items() if k in capsules}
        corners = self.findReachableCorners()
        cornerDict = {k: CORNER_VAL for k, v in self.rewardDict.items() if k in corners}
        self.rewardDict.update(foodDict)
        self.rewardDict.update(capsuleDict)
        self.rewardDict.update(cornerDict)
        for g in ghosts:
            if g[0] in self.rewardDict.keys():
                if g[1] == 0:
                    self.rewardDict[g[0]] = ghostReward = GHOST_VAL
                elif g[1] == 1:
                    self.rewardDict[g[0]] = ghostReward = EDIBLE_GHOST_VAL
                self.findGhosts()
                ghostNeighbours = self.findGhostNeighbours(g[0], {}, self.ghostBuffer, 0)
                ghostRadius = self.mapGhostNeighbourRewards(ghostNeighbours)
                self.rewardDict.update(ghostRadius)

    """
    Calculates and returns the four traversable corners of the current layout
    @param self: the class itself
    @param state: the current game state
    @return a list of tuples that represent the four traversable corners
    """
    def findReachableCorners(self):
        maxW, maxH, walls, food = self.maxW, self.maxH, self.walls, self.food
        innerCorner = {"UL": (1,1), "UR": (-1,1), "BL": (1,-1), "BR": (-1,-1)}
        corners = {"UL": (0,0), "UR": (maxW,0), "BL": (0, maxH), "BR": (maxW, maxH)}
        result = []
        for k in innerCorner.keys():
            temp = tuple(map(sum, zip(innerCorner[k], corners[k])))
            if temp not in walls and temp in food:
                result.append(temp)
        return result

    """
    Sets ghost locations for current step
    @param self: the class itself
    """
    def findGhosts(self):
        ghosts = []
        for g in self.ghostStates:
            ghosts.append(g[0])
        self.ghostLocs = ghosts

    """
    Calculates and returns the parameter c's neighbours, with k,v -> radius integer, states list
    @param self: the class itself
    @param c: tuple representing ghost position 
    @param n: list representing current neighbours found 
    @param buff: integer representing ghost buffer
    @param count: integer representing how many times this function has been ran
    @return dictionary containing neighbours of the ghost found in the specified radius
    """
    def findGhostNeighbours(self, c, n, buff, count):
        a, pacman, ghosts, walls = ADJ_TEMPLATE, self.pacman, self.ghostLocs, self.walls
        # if this is the first call, initialise n as a dictionary
        if count == 0:
            for i in range(0, buff):
                n[i+1] = []
        if buff > 0:
            for i in a.values():
                new = (i[0]+c[0], i[1]+c[1])
                if new not in walls and new != pacman and new not in ghosts:
                    if new not in n[buff]:
                        n[buff].append(new)
                    n = self.findGhostNeighbours(new, n, buff-1, count+1)
        return n

    """
    Calculates and assigns the reward value according to the radius value
    @param self: the class itself
    @param neighbours: dictionary where radius values are mapped to the states found in it
    @return dictionary containing the reward values of each state within parameter neighbours
    """
    def mapGhostNeighbourRewards(self, neighbours):
        reward = {}
        count = 1.0
        # neighbours dictionary keys are in ascending order
        # even if there are re-occurring states at greater radius, the reward value is not assigned to a lower value 
        for radius in neighbours.values():
            count = count + 1.0
            for n in radius:
                if n not in reward.keys():
                    reward[n] = round(GHOST_VAL*(1/count))
        return reward
    
    """
    Value iteration of the MDP-Solver
    Calculates and returns the converged utilities
    @param self: the class itself
    @return dictionary representing the converged utilities of the current step
    """
    def valueIteration(self):
        stability = 0.001
        self.utilDict = {k: 0 for k in self.map if k not in self.walls}
        states, rewards, utils = self.stateDict, self.rewardDict, self.utilDict
        while True:
            delta = 0
            for square, utility in utils.items():
                tmp_utils = {}
                for direction, state in states[square].items():
                    nextUtil = (0.8*utils[state[0]] + 0.1*utils[state[1]] + 0.1*utils[state[2]])
                    tmp_utils[direction] = nextUtil
                utils[square] = rewards[square] + self.discountFactor* max(tmp_utils.values())
                delta = max(delta, abs(utils[square] - utility))
            if delta < stability:
                return utils
    
    """
    Calculates pacman's current adjacent states
    And returns the direction that leads to the adjacent state with the maximum expected utility
    @param self: the class itself
    @param utils: dictionary representing the converged utilities
    @return Direction enum indicating where pacman should move next 
    """
    def findNextMove(self, utils):
        # find optimal utility's coordinate
        pac, adj = self.pacman, ADJ_TEMPLATE
        neighbours = [n for n in self.findNeighbours(pac).values() if n!= pac]
        neighbourUtils = [utils[i] for i in neighbours]
        optUtil = neighbours[neighbourUtils.index(max(neighbourUtils))]
        # translate coordinate into direction
        nextMove = adj.keys()[adj.values().index((optUtil[0]-pac[0], optUtil[1]-pac[1]))]
        directionDict = {"N": Directions.NORTH, "S": Directions.SOUTH, "E": Directions.EAST, "W": Directions.WEST}
        return directionDict[nextMove]
