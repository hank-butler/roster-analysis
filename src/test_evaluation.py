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
    print(f"\nCap Hit: ${player.cap_hit_2026:>12,.0f}")
    print(f"\nFair Value: ${player.fair_value:>12,.0f}")
    print(f"\nDifference: ${player.cap_hit_2026 - player.fair_value:>12,.0f}")
    print(f"\nEfficiency: {player.efficiency_ratio:>12.2f}")
    print(f"\nRisk Score: {player.risk_score:>12.2f}")

    if player.cap_hit_2026 > player.fair_value * 1.15:
        pct_over = ((player.cap_hit_2026 / player.fair_value) - 1) * 100
        print(f"Overvalued by: {pct_over:.1f}%")
    elif player.cap_hit_2026 < player.fair_value * 0.85:
        pct_under = ((player.fair_value / player.cap_hit_2026) - 1) * 100
        print(f"Undervalued by: {pct_under:.1f}%")

print("\n" + "="*50)
print("PORTFOLIO SUMMARY")
print("="*50)

summary = analyzer.summary_report()

print(f"\nTotal Value: ${summary['total_value']:>12,.0f}")
print(f"\nTotal Cost: ${summary['total_cost']:>12,.0f}")
print(f"\nEfficiency: {summary['efficiency']:>12.2%}")
print(f"\nPorfolio Risk: {summary['risk']:>12.2f}")
print(f"\nSharpe Ratio: {summary['sharpe_ratio']:>12.2f}")

print("\nPosition Allocation")
for pos, pct in sorted(summary['position_allocation'].items()):
    print(f"{pos:>6}: {pct:>6.1f}%")

print("\n"+"="*50)
print("OVERVALUED PLAYERS")
print("="*50)

overvalued = analyzer.identify_overvalued()

if len(overvalued) > 0:
    print(overvalued[['name', 'position', 'cap_hit', 'fair_value', 'overvalued_by', 'pct_overvalued']])
else:
    print("No significantly overvalued players")

