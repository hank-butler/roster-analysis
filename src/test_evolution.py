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

while len(colts_roster) < 53:
    colts_roster.append(PlayerAsset(
        player_id=f"colts_{len(colts_roster)}",
        name=f"Colts Player {len(colts_roster)}",
        position=random.choice(['QB', 'RB', 'WR', 'TE', 'OT', 'OG', 'C', 'EDGE', 'DL', 'LB', 'CB', 'S', 'K', 'P', 'LS']),
        team='IND',
        age=random.randint(22,32),
        cap_hit_2026=random.uniform(900_000, 15_000_000),
        years_remaining=random.randint(1, 4),
        guaranteed_money=random.uniform(0, 5_000_000),
        total_contract_value=random.uniform(3_000_000, 40_000_000),
        epa_total=random.uniform(-3, 15),
        snaps_played=random.randint(200, 1100),
        games_missed=random.randint(0, 8)
    ))

print("Finished")