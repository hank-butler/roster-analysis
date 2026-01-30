import player_valuation as pev

# if pev.PlayerAsset:
    # print("Successfully imported: {pev.PlayerAsset}")

'''
Creating test roster with 3 IND Colts players
Michael Pittman, Jr.
DeForest Buckner
Quenton Nelson
'''

test_roster = [
    pev.PlayerAsset(
        player_id="pittman001",
        name="Michael Pittman Jr.",
        position="WR",
        team="IND",
        age=28,
        cap_hit_2026=29_000_000,
        years_remaining=1,
        guaranteed_money=0,
        total_contract_value=29_000_000,
        epa_total=12.4,
        snaps_played=950,
        games_missed=0
    ),
    pev.PlayerAsset(
        player_id="buckner001",
        name="DeForest Buckner",
        position="DL",
        team="IND",
        age=32,
        cap_hit_2026=26_600_000,
        years_remaining=2,
        guaranteed_money=10_000_000,
        total_contract_value=50_000_000,
        epa_total=8.2,
        snaps_played=680,
        games_missed=10
    ),
    pev.PlayerAsset(
        player_id="nelson001",
        name="Quenton Nelson",
        position="OG",
        team="IND",
        age=28,
        cap_hit_2026=24_200_000,
        years_remaining=3,
        guaranteed_money=0,
        total_contract_value=70_000_000,
        epa_total=15.6,
        snaps_played=1050,
        games_missed=2
    )
]

model = pev.PlayerValuationModel()
valued_roster = model.value_roster(test_roster)

analyzer = pev.PortfolioAnalyzer(valued_roster)

print("IND COLTS - Sample Roster Valuation")

for player in valued_roster:
    # print(player)
    print(f"\n{player.name} ({player.position}, Age: {player.age})")