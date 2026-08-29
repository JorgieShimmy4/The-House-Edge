"""Worked examples. Run: python demo.py"""

from betting import (american_to_decimal, analyse_bet, analyse_parlay, hold,
                     kelly_stake, pickem_table, remove_vig,
                     roi_confidence_interval, simulate_bankroll)

line = "-" * 66

print(line); print("SINGLE BET  |  coin flip at -110"); print(line)
r = analyse_bet(0.50, american=-110)
print(f"  breakeven win rate     {r.breakeven_probability:>10.2%}")
print(f"  your probability       {r.probability:>10.2%}")
print(f"  edge                   {r.edge:>+10.2%}")
print(f"  EV per unit staked     {r.ev:>+10.2%}")
print(f"  std dev per unit       {r.std_dev:>10.4f}")
print(f"  recommended stake      ${kelly_stake(r, 1000):>9.2f}  (bankroll $1,000)")

print()
print(line); print("SINGLE BET  |  you think it's 56% at -110"); print(line)
r = analyse_bet(0.56, american=-110)
print(f"  edge                   {r.edge:>+10.2%}")
print(f"  EV per unit staked     {r.ev:>+10.2%}")
print(f"  full Kelly             {r.kelly_fraction:>10.2%} of bankroll")
print(f"  quarter Kelly stake    ${kelly_stake(r, 1000):>9.2f}")

print()
print(line); print("MARKET  |  stripping the vig from a two-way line"); print(line)
book = [american_to_decimal(-110), american_to_decimal(-110)]
fair = remove_vig(book)
print(f"  raw implied            {1/book[0]:.4f} + {1/book[1]:.4f} = {1/book[0]+1/book[1]:.4f}")
print(f"  de-vigged              {fair[0]:.4f} + {fair[1]:.4f} = {sum(fair):.4f}")
print(f"  house hold             {hold(book):>10.2%}")

print()
print(line); print("PICK'EM  |  $50 entry, two coin-flip legs, 3x payout"); print(line)
p = analyse_parlay([0.5, 0.5], 3.0)
print(f"  probability of hitting {p.hit_probability:>10.2%}")
print(f"  fair payout            {p.fair_multiplier:>9.1f}x")
print(f"  offered payout         {p.offered_multiplier:>9.1f}x")
print(f"  EV                     {p.ev:>+10.2%}   (${50*p.ev:+.2f} on $50)")
print(f"  house hold             {p.hold:>10.2%}")

print()
print(line); print("PICK'EM  |  hold by leg count"); print(line)
print(f"  {'legs':>5} {'hit %':>9} {'fair':>8} {'offered':>9} {'hold':>9} {'EV':>9}")
for row in pickem_table({2: 3.0, 3: 5.0, 4: 10.0, 5: 20.0, 6: 25.0}):
    print(f"  {row.legs:>5} {row.hit_probability:>9.2%} {row.fair_multiplier:>7.0f}x "
          f"{row.offered_multiplier:>8.0f}x {row.hold:>9.1%} {row.ev:>+9.1%}")
print("  payouts are illustrative; verify against the operator")

print()
print(line); print("BANKROLL  |  $1,000, flat $50 bets at -110, 200 bets"); print(line)
s = simulate_bankroll(1000.0, 0.50, american_to_decimal(-110),
                      stake=50.0, n_bets=200, n_paths=10_000, seed=1)
print(f"  median final           ${s.median_final:>9,.0f}")
print(f"  5th percentile         ${s.percentile_5:>9,.0f}")
print(f"  95th percentile        ${s.percentile_95:>9,.0f}")
print(f"  ended up               {s.profitable_rate:>10.1%} of paths")
print(f"  went bust              {s.ruin_rate:>10.1%} of paths")

print()
print(line); print("TRACK RECORD  |  +4% ROI over 200 bets. Are you good?"); print(line)
lo, hi = roi_confidence_interval(0.04, bet_std_dev=1.0, n_bets=200)
print(f"  observed ROI           {0.04:>+10.1%}")
print(f"  95% interval           {lo:>+9.1%} to {hi:+.1%}")
print("  the interval spans zero, so this record cannot distinguish")
print("  a winning bettor from a losing one")
lo, hi = roi_confidence_interval(0.04, bet_std_dev=1.0, n_bets=5000)
print(f"\n  same ROI, 5,000 bets   {lo:>+9.1%} to {hi:+.1%}")
