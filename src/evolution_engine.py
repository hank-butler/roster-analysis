import random
from typing import List, Dict, Tuple, Callable
from dataclasses import dataclass, field
from copy import deepcopy
import numpy as np
import pandas as pd
from tqdm import tqdm

from player_valuation import PlayerAsset, PlayerValuationModel, PortfolioAnalyzer

@dataclass
class RosterConstraints:
    """
    Setting up constraints for NFL active roster. Current active roster size is 53 players

    Base Salary Cap default value from https://overthecap.com/salary-cap-space
    """
    max_roster_size: int = 53
    min_roster_size: int = 53
    salary_cap: float = 295_500_000

    # Position requirements (min, max)
    position_limits: Dict[str, Tuple[int, int]] = field(default_factory=lambda: {
        'QB': (2, 3),
        'RB': (3, 5),
        'WR': (5, 7),
        'TE': (2, 4),
        'OT': (4, 6),
        'OG': (4, 6),
        'C': (2, 3),
        'EDGE': (4, 6),
        'DL': (4, 6),
        'LB': (4, 6),
        'CB': (4, 6),
        'S': (3, 5),
        'K': (1, 1),
        'P': (1, 1),
        'LS': (1, 1)
    })

class Chromosome:
    """
    Using the evolution algorithm, need to represent the chromosomes and genes.

    A Chromosome represents one possible roster configuration.

    Genes = player selections
    """

    def __init__(self, players: List[PlayerAsset]):
        self.players = players
        self.fitness = None,
        self._analyzer = None

    def __len__(self):
        return len(self.players)
    
    @property
    def analyzer(self) -> PortfolioAnalyzer:
        """
        Load analzyer lazily
        """
        if self._analyzer is None:
            self._analyzer = PortfolioAnalyzer(self.players)
        return self._analyzer
    
    def total_cap(self) -> float:
        """
        Total Cap hit of roster as a float
        """
        return sum(p.cap_hit_2026 for p in self.players)
    
    def position_counts(self) -> Dict[str, int]:
        """
        Count players by position

        Returns a dictionary with player pos as key, count of players by position as int as value
        """
        counts = {}
        for player in self.players:
            counts[player.position] = counts.get(player.position, 0) + 1 # if position key doesn't exist yet, return 0
        return counts
    
    def is_valid(self, constraints: RosterConstraints) -> bool:
        """
        Method to ensure roster constraints are met

        Returns True if met, False otherwise
        """
        if len(self.players) < constraints.min_roster_size:
            return False
        if len(self.players) > constraints.max_roster_size:
            return False
        
        if self.total_cap() > constraints.salary_cap:
            return False
        
        # Check position requirements
        pos_counts = self.position_counts()
        for positition, (min_count, max_count) in constraints.position_limits.items():
            count = pos_counts.get(position, 0)
            if count < min_count or count > max_count:
                return False
        
        return True
    
    def clone(self) -> 'Chromosome':
        """
        Creates a deep copy of the Chromosome instance
        """
        return Chromosome([deepcopy(p) for p in self.players])

class EvolutionEngine:
    """
    Genetic algorithm for roster optimization
    
    """
    def __init__(self,
                 current_roster: List[PlayerAsset],
                 available_players: List[PlayerAsset],
                 constraints: RosterConstraints,
                 valuation_model: PlayerValuationModel):
        
        self.current_roster = current_roster
        self.available_players = available_players
        self.constraints = constraints
        self.valuation_model = valuation_model

        # Evolutionary Parameters, generic for now to test out evo engine
        self.population_size = 100
        self.generations = 100
        self.mutation_rate = 0.15
        self.crossover_rate = 0.8
        self.tournament_size = 5
        self.elitism_count = 5

        # History Tracking
        self.history = []
        self.best_ever = None
        self.best_fitness_ever = -float('inf')

    def fitness_function(self, chromosome: Chromosome) -> float:
        """
        multi-objective fitness function

        Objectives:
        1. Maximize portfolio efficiency (40%)
        2. Minimize portfolio risk (25%)
        3. Maximize position balance (20%)
        4. Minimize wasted cap space (15%)
        """

        if not chromosome.is_valid(self.constraints):
            return -1000 # invalid rosters are definitionally not evolutionary fit
        
        analyzer = chromosome.analyzer

        # 1. Portfolio Efficiency (value per dollar)
        efficiency = analyzer.portfolio_efficiency()
        efficiency_score = min(efficiency / 1.5, 1.0)

        # 2. Risk score (lower is better)
        risk = analyzer.portfolio_risk()
        risk_score = 1 - risk # invert to make higher better

        # 3. Position balance (ensures not optimizing for single position, eg. 10 WR's')
        position_balance = self._calculate_position_balance(chromosome)

        # 4. Cap space utilization (use cap efficiently, but leave some breathing room)
        cap_used = chromosome.total_cap()
        cap_available = self.constraints.salary_cap
        utilization = cap_used / cap_available

        if 0.90 <= utilization <= 0.95:
            cap_score = 1.0
        elif utilization <= 0.90:
            cap_score = utilization / 0.90 # penalize for underutilization
        else:
            cap_score = max(0, 2 - utilization / 0.95) # penalize for overutilization

        # weighted combination based on calculations in method and arbitrary weights in objectives
        fitness = (
            0.40 * efficiency_score +
            0.25 * risk_score +
            0.20 * position_balance +
            0.15 * cap_score
        )

        return fitness

    def _calculate_position_balance(self, chromosome: Chromosome) -> float:
        """
        How well does a roster meet positional needs?

        Scored between 0.0-1.0, higher being better.
        """
        pos_counts = chromosome.position_counts()

        total_score = 0
        total_positions = 0

        for position, (min_count, max_count) in self.constraints.position_limits.items():
            count = pos_counts.get(position, 0)

            # ideal count is midpoint
            ideal_count = (min_count + max_count) / 2

            # score based on distance from ideal
            if count < min_count:
                score = 0 # below minimum is bad situation
            elif count > max_count:
                score = 0 # above maximum bad as well
            else:
                # linear score: 1.0 at ideal, 0.5 at min/max
                distance_from_ideal = abs(count - ideal_count)
                max_distance = ideal_count - min_count
                if max_distance > 0:
                    score = 1 - (distance_from_ideal / max_distance) *0.5
                else:
                    score = 1.0
            total_score += score
            total_positions += 1

        return total_score / total_positions if total_positions > 0 else 0
    
    def initialize_population(self) -> List[Chromosome]:
        """
        Create initial population of random valid rosters
        
        """

        population = []

        # including current roster
        population.append(Chromosome(self.current_roster))

        # Generate random rosters
        attempts = 0
        max_attempts = 10_000

        with tqdm(total=self.population_size, desc="Initializing population") as pbar:
            while len(population) < self.population_size and attempts < max_attempts:
                roster = self._generate_random_roster()
                chromosome = Chromosome(roster)

                if chromosome.is_valid(self.constraints):
                    population.append(chromosome)
                    pbar.update(1)

                attemps += 1

        if len(population) < self.population_size:
            print(f"Warning: generated {len(population)} valid rosters")

        return population
    
    def _generate_random_roster(self) -> List[PlayerAsset]:
        """
        Generate one random valid roster

        Returns a list of PlayerAssets
        """
        roster = []
        positions_filled = {
            pos: 0 for pos in self.constraints.position_limits.keys()
        }
        cap_used = 0

        available = self.available_players.copy()
        random.shuffle(available)

        for player in available:
            pos = player.position
            min_count, max_count = self.constraints.position_limits.get(pos, (0, 10))

            can_add = (
                positions_filled[pos] < max_count and
                cap_used + player.cap_hit_2026 <= self.constraints.salary_cap and
                len(roster) < self.constraints.max_roster_size
            )

            if can_add:
                roster.append(player)
                positions_filled[pos] += 1
                cap_used += player.cap_hit_2026

        # fill missing positions with cheap options
        for pos, (min_count, _) in self.constraints.position_limits.items():
            while positions_filled[pos] < min_count:
                # find cheapest players to fill until min count satisfied
                candidates = [p for p in available if p.position == p and p not in roster]
                if candidates:
                    cheapest = min(candidates, key=lambda p: p.cap_hit_2026)
                    if cap_used + cheapest.cap_hit_2026 <= self.constraints.salary_cap:
                        roster.append(cheapest)
                        positions_filled[pos] += 1
                        cap_used += cheapest.cap_hit_2026
                    else:
                        break
                else:
                    break

        return roster
    
    def tournament_selection(self, population: List[Chromosome], fitness_scores: List[float]) -> Chromosome:
        """
        Select parent using tournament selection

        args:
        population: List[Chromosome]'
        fitness_scores: List[floats]

        returns:
        Chromosome
        """
        tournament_indices = random.sample(range(len(population)), min(self.tournament_size, len(population)))

        best_idx = max(tournament_indices, key=lambda i: fitness_scores[i])

        return population[best_idx]
    
    def crossover(self, parent1: Chromosome, parent2: Chromosome) -> Tuple[Chromosome, Chromosome]:
        """
        Creates two offspring by combining parents.

        Args:
        parent1: Chromosome
        parent2: Chromosome

        Returns:
        Tuple of Chromosomes
        """
        if random.random() > self.crossover_rate:
            # no crossover, return clones
            return parent1.clone(), parent2.clone()
        
        # position aware crossover. For each position, randomly choose which parent to take player from
        child1_players = []
        child2_players = []

        all_positions = set(self.constraints.position_limits.keys())

        for position in all_positions:
            p1_at_pos = [p for p in parent1.players if p.position == position]
            p2_at_pos = [p for p in parent2.players if p.position == position]

            if random.random() < 0.5:
                child1_players.extend(p1_at_pos)
                child2_players.extend(p2_at_pos)
            else:
                child1_players.extend(p2_at_pos)
                child2_players.extend(p1_at_pos)

        return Chromosome(child1_players), Chromosome(child2_players)
    
    
                


