import random
from player_valuation import PlayerAsset, PlayerValuationModel, PortfolioAnalyzer
from evolution_engine import RosterConstraints, EvolutionEngine, Chromosome

colts_roster = [
    PlayerAsset(
        player_id="pittman001", name="Michael Pittman Jr.", position="WR", team="IND",
        age=28, cap_hit_2026=29_000_000, years_remaining=1, guaranteed_money=0,
        total_contract_value=29_000_000, epa_total=12.4, snaps_played=950, games_missed=0
    ),
    PlayerAsset(
        player_id="buckner001", name="DeForest Buckner", position="DL", team="IND",
        age=32, cap_hit_2026=26_600_000, years_remaining=2, guaranteed_money=10_000_000,
        total_contract_value=50_000_000, epa_total=8.2, snaps_played=680, games_missed=10
    ),
    PlayerAsset(
        player_id="nelson001", name="Quenton Nelson", position="OG", team="IND",
        age=28, cap_hit_2026=24_200_000, years_remaining=3, guaranteed_money=0,
        total_contract_value=70_000_000, epa_total=15.6, snaps_played=1050, games_missed=2
    ),
    # Add more players...
]

print("Creating synthetic player dataset for testing")

# Position distribution that satisfies constraints and sums to 53
# Existing real players: WR(1), DL(1), OG(1)
roster_positions = (
    ['QB'] * 2 + ['RB'] * 3 + ['WR'] * 5 + ['TE'] * 3 +
    ['OT'] * 5 + ['OG'] * 4 + ['C'] * 2 +
    ['EDGE'] * 5 + ['DL'] * 4 + ['LB'] * 5 + ['CB'] * 5 + ['S'] * 4 +
    ['K'] * 1 + ['P'] * 1 + ['LS'] * 1
)

# Remove positions already filled by the 3 real players
roster_positions.remove('WR')
roster_positions.remove('DL')
roster_positions.remove('OG')

for i, pos in enumerate(roster_positions):
    colts_roster.append(PlayerAsset(
        player_id=f"colts_{len(colts_roster)}",
        name=f"Colts Player {len(colts_roster)}",
        position=pos,
        team='IND',
        age=random.randint(22, 32),
        cap_hit_2026=random.uniform(900_000, 4_500_000),
        years_remaining=random.randint(1, 4),
        guaranteed_money=random.uniform(0, 2_000_000),
        total_contract_value=random.uniform(3_000_000, 15_000_000),
        epa_total=random.uniform(-3, 15),
        snaps_played=random.randint(200, 1100),
        games_missed=random.randint(0, 8)
    ))

# Generate free agents with guaranteed position coverage for the evo engine
fa_positions = (
    ['QB'] * 8 + ['RB'] * 12 + ['WR'] * 18 + ['TE'] * 10 +
    ['OT'] * 14 + ['OG'] * 14 + ['C'] * 8 +
    ['EDGE'] * 14 + ['DL'] * 14 + ['LB'] * 14 + ['CB'] * 14 + ['S'] * 12 +
    ['K'] * 4 + ['P'] * 4 + ['LS'] * 4
)

free_agents = []
for i, pos in enumerate(fa_positions):
    free_agents.append(PlayerAsset(
        player_id=f"fa_{i}",
        name=f"Free Agent {i}",
        position=pos,
        team="FA",
        age=random.randint(23, 31),
        cap_hit_2026=random.uniform(900_000, 8_000_000),
        years_remaining=random.randint(2, 4),
        guaranteed_money=random.uniform(0, 4_000_000),
        total_contract_value=random.uniform(3_000_000, 25_000_000),
        epa_total=random.uniform(-2, 18),
        snaps_played=random.randint(400, 1100),
        games_missed=random.randint(0, 4)
    ))

all_available = colts_roster + free_agents

print("Valuing all players...")
model = PlayerValuationModel()
valued_colts = model.value_roster(colts_roster)
valued_free_agents = model.value_roster(free_agents)
valued_all = valued_colts + valued_free_agents

# =============================================
# TEST 1: Chromosome basics
# =============================================
print("\n" + "="*50)
print("TEST 1: Chromosome Basics")
print("="*50)

chrom = Chromosome(valued_colts)
print(f"Roster size: {len(chrom)}")
print(f"Total cap hit: ${chrom.total_cap():>12,.0f}")

pos_counts = chrom.position_counts()
print("\nPosition counts:")
for pos, count in sorted(pos_counts.items()):
    print(f"  {pos:>4}: {count}")

# =============================================
# TEST 2: Roster constraint validation
# =============================================
print("\n" + "="*50)
print("TEST 2: Roster Constraint Validation")
print("="*50)

constraints = RosterConstraints()
print(f"Salary cap: ${constraints.salary_cap:>12,.0f}")
print(f"Roster size: {constraints.min_roster_size}-{constraints.max_roster_size}")

# 53-man roster with random positions won't meet position minimums, but test the method
is_valid = chrom.is_valid(constraints)
print(f"Is 53-man Colts roster valid? {is_valid}")

# =============================================
# TEST 3: Chromosome clone
# =============================================
print("\n" + "="*50)
print("TEST 3: Chromosome Clone")
print("="*50)

cloned = chrom.clone()
print(f"Original size: {len(chrom)}, Clone size: {len(cloned)}")
print(f"Same object? {chrom is cloned}")
print(f"Same players list? {chrom.players is cloned.players}")
print(f"Same first player object? {chrom.players[0] is cloned.players[0]}")

# =============================================
# TEST 4: Evolution Engine setup
# =============================================
print("\n" + "="*50)
print("TEST 4: Evolution Engine Setup")
print("="*50)

engine = EvolutionEngine(
    current_roster=valued_colts,
    available_players=valued_all,
    constraints=constraints,
    valuation_model=model
)

print(f"Population size: {engine.population_size}")
print(f"Generations: {engine.generations}")
print(f"Mutation rate: {engine.mutation_rate}")
print(f"Crossover rate: {engine.crossover_rate}")
print(f"Tournament size: {engine.tournament_size}")
print(f"Elitism count: {engine.elitism_count}")

# =============================================
# TEST 5: Fitness function
# =============================================
print("\n" + "="*50)
print("TEST 5: Fitness Function")
print("="*50)

fitness = engine.fitness_function(chrom)
print(f"Colts roster fitness: {fitness:.4f}")

# Test with a tiny invalid roster
tiny_chrom = Chromosome(valued_colts[:5])
tiny_fitness = engine.fitness_function(tiny_chrom)
print(f"Invalid (5 player) roster fitness: {tiny_fitness:.4f}")

# =============================================
# TEST 6: Position balance scoring
# =============================================
print("\n" + "="*50)
print("TEST 6: Position Balance")
print("="*50)

balance = engine._calculate_position_balance(chrom)
print(f"Colts roster position balance: {balance:.4f}")

# =============================================
# TEST 7: Population initialization
# =============================================
print("\n" + "="*50)
print("TEST 7: Population Initialization")
print("="*50)

# Use smaller population for testing speed
engine.population_size = 10
population = engine.initialize_population()
print(f"Population generated: {len(population)} chromosomes")

for i, ind in enumerate(population):
    valid = ind.is_valid(constraints)
    print(f"  Chromosome {i}: {len(ind)} players, cap=${ind.total_cap():>12,.0f}, valid={valid}")

# =============================================
# TEST 8: Tournament selection
# =============================================
print("\n" + "="*50)
print("TEST 8: Tournament Selection")
print("="*50)

fitness_scores = [engine.fitness_function(c) for c in population]
print(f"Fitness scores: {[f'{s:.4f}' for s in fitness_scores]}")

winner = engine.tournament_selection(population, fitness_scores)
print(f"Tournament winner: {len(winner)} players, cap=${winner.total_cap():>12,.0f}")

# =============================================
# TEST 9: Crossover
# =============================================
print("\n" + "="*50)
print("TEST 9: Crossover")
print("="*50)

# Find two valid parents from population
valid_parents = [p for p, f in zip(population, fitness_scores) if f > -1000]
if len(valid_parents) >= 2:
    parent1, parent2 = valid_parents[0], valid_parents[1]
    print(f"Parent 1: {len(parent1)} players, cap=${parent1.total_cap():>12,.0f}")
    print(f"Parent 2: {len(parent2)} players, cap=${parent2.total_cap():>12,.0f}")

    child1, child2 = engine.crossover(parent1, parent2)
    print(f"Child 1:  {len(child1)} players, cap=${child1.total_cap():>12,.0f}")
    print(f"Child 2:  {len(child2)} players, cap=${child2.total_cap():>12,.0f}")
else:
    print("Not enough valid parents for crossover test")

# =============================================
# TEST 10: Mutation
# =============================================
print("\n" + "="*50)
print("TEST 10: Mutation")
print("="*50)

if valid_parents:
    original = valid_parents[0]
    # Force mutation by temporarily setting rate to 1.0
    original_rate = engine.mutation_rate
    engine.mutation_rate = 1.0

    mutated = engine.mutate(original)
    print(f"Original: {len(original)} players, cap=${original.total_cap():>12,.0f}")
    print(f"Mutated:  {len(mutated)} players, cap=${mutated.total_cap():>12,.0f}")
    print(f"Same object? {original is mutated}")

    # Check how many players differ
    original_ids = set(p.player_id for p in original.players)
    mutated_ids = set(p.player_id for p in mutated.players)
    diff = original_ids.symmetric_difference(mutated_ids)
    print(f"Player differences: {len(diff)} player(s) changed")

    engine.mutation_rate = original_rate
else:
    print("No valid chromosomes for mutation test")

# =============================================
# TEST 11: Full evolution run (small scale)
# =============================================
print("\n" + "="*50)
print("TEST 11: Full Evolution Run")
print("="*50)

engine_full = EvolutionEngine(
    current_roster=valued_colts,
    available_players=valued_all,
    constraints=constraints,
    valuation_model=model
)

# Small parameters for a test run
engine_full.population_size = 20
engine_full.generations = 10

best_roster, history = engine_full.evolve()

print(f"\nEvolution results:")
print(f"Best fitness: {engine_full.best_fitness_ever:.4f}")
print(f"Generations run: {len(history)}")
print(f"Best roster size: {len(best_roster)}")
print(f"Best roster cap: ${best_roster.total_cap():>12,.0f}")

print("\nBest roster position counts:")
for pos, count in sorted(best_roster.position_counts().items()):
    print(f"  {pos:>4}: {count}")

print("\nFitness history:")
for gen_data in history:
    print(f"  Gen {gen_data['generation']:>3d}: "
          f"Best={gen_data['best_fitness']:.4f}, "
          f"Avg={gen_data['avg_fitness']:.4f}, "
          f"Diversity={gen_data['diversity']:.4f}")

# Portfolio analysis of best roster
print("\n" + "="*50)
print("BEST ROSTER PORTFOLIO ANALYSIS")
print("="*50)

best_analyzer = PortfolioAnalyzer(best_roster.players)
summary = best_analyzer.summary_report()

print(f"Total Value:  ${summary['total_value']:>12,.0f}")
print(f"Total Cost:   ${summary['total_cost']:>12,.0f}")
print(f"Efficiency:   {summary['efficiency']:>12.2%}")
print(f"Risk:         {summary['risk']:>12.2f}")
print(f"Sharpe Ratio: {summary['sharpe_ratio']:>12.2f}")

print("\nPosition allocation:")
for pos, pct in sorted(summary['position_allocation'].items()):
    print(f"  {pos:>4}: {pct:>6.1f}%")

print("\n" + "="*50)
print("ALL TESTS COMPLETE")
print("="*50)