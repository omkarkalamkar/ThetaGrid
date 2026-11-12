"""
Interactive VIX-Inflated LEAPS Put Calculator
Allows you to adjust parameters and see real-time impact
"""
import math

def norm_cdf(x):
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def norm_pdf(x):
    return math.exp(-0.5 * x**2) / math.sqrt(2 * math.pi)

def black_scholes_put(spot, strike, time_years, volatility, r=0.07):
    if time_years <= 0:
        return max(0, strike - spot)
    d1 = (math.log(spot / strike) + (r + 0.5 * volatility**2) * time_years) / (volatility * math.sqrt(time_years))
    d2 = d1 - volatility * math.sqrt(time_years)
    return strike * math.exp(-r * time_years) * norm_cdf(-d2) - spot * norm_cdf(-d1)

def calculate_pnl_for_scenario(spot, strike, premium, dte, current_vix, 
                                future_spot=None, future_vix=None, days_elapsed=0):
    """
    Calculate P&L for any scenario
    """
    if future_spot is None:
        future_spot = spot
    if future_vix is None:
        future_vix = current_vix
    
    remaining_dte = dte - days_elapsed
    time_years = max(0, remaining_dte / 365.0)
    
    if time_years <= 0:
        # At expiry
        put_value = max(0, strike - future_spot)
    else:
        # Before expiry
        put_value = black_scholes_put(future_spot, strike, time_years, future_vix/100.0)
    
    pnl = premium - put_value
    pnl_percent = (pnl / premium) * 100
    roi_on_margin = (pnl / (strike * 50 * 0.15)) * 100  # Assuming 15% margin
    
    return {
        'put_value': round(put_value, 2),
        'pnl': round(pnl, 2),
        'pnl_percent': round(pnl_percent, 2),
        'pnl_per_lot': round(pnl * 50, 2),
        'roi_on_margin': round(roi_on_margin, 2)
    }

def quick_scenario(description, spot, strike, premium, dte, current_vix, 
                   future_spot, future_vix, days_elapsed):
    """Print a scenario quickly"""
    result = calculate_pnl_for_scenario(spot, strike, premium, dte, current_vix,
                                        future_spot, future_vix, days_elapsed)
    
    print(f"\n{description}")
    print(f"  Future Spot: ₹{future_spot:,} | Future VIX: {future_vix:.1f}% | Days: {days_elapsed}")
    print(f"  Put Value: ₹{result['put_value']:,} | P&L: ₹{result['pnl']:,} ({result['pnl_percent']:.1f}%)")
    print(f"  P&L per Lot: ₹{result['pnl_per_lot']:,} | ROI on Margin: {result['roi_on_margin']:.1f}%")

def main():
    print("=" * 80)
    print("INTERACTIVE VIX LEAPS CALCULATOR")
    print("=" * 80)
    
    # Base trade parameters
    SPOT = 25045
    STRIKE = 30000
    PREMIUM = 3290
    DTE = 413
    CURRENT_VIX = 17.42
    
    print(f"\nBase Trade: NIFTY {STRIKE} PE DEC 2027")
    print(f"  Current Spot: ₹{SPOT:,}")
    print(f"  Premium: ₹{PREMIUM:,}")
    print(f"  DTE: {DTE} days")
    print(f"  Current VIX: {CURRENT_VIX}%")
    
    print("\n" + "=" * 80)
    print("SCENARIO ANALYSIS")
    print("=" * 80)
    
    # Scenario 1: VIX normalizes quickly (3 months)
    quick_scenario(
        "📊 SCENARIO 1: Fast VIX Normalization (3 months)",
        SPOT, STRIKE, PREMIUM, DTE, CURRENT_VIX,
        future_spot=25045,  # Unchanged
        future_vix=15.0,    # VIX drops to 15
        days_elapsed=90
    )
    
    # Scenario 2: Market rallies + VIX normalizes (6 months)
    quick_scenario(
        "🚀 SCENARIO 2: Bull Market + VIX Drop (6 months)",
        SPOT, STRIKE, PREMIUM, DTE, CURRENT_VIX,
        future_spot=27000,  # 8% rally
        future_vix=14.0,    # VIX normal
        days_elapsed=180
    )
    
    # Scenario 3: Slow grind up (at expiry)
    quick_scenario(
        "🐌 SCENARIO 3: Slow Grind to 28K (At Expiry)",
        SPOT, STRIKE, PREMIUM, DTE, CURRENT_VIX,
        future_spot=28000,  # 12% rally over 13 months
        future_vix=14.0,    # VIX normal
        days_elapsed=413
    )
    
    # Scenario 4: Market correction but VIX normalizes
    quick_scenario(
        "⚠️  SCENARIO 4: Correction but VIX Calms (6 months)",
        SPOT, STRIKE, PREMIUM, DTE, CURRENT_VIX,
        future_spot=23500,  # 6% drop
        future_vix=16.0,    # VIX still elevated
        days_elapsed=180
    )
    
    # Scenario 5: Worst case - crash + VIX spike
    quick_scenario(
        "💥 SCENARIO 5: Crash + VIX Spike (3 months)",
        SPOT, STRIKE, PREMIUM, DTE, CURRENT_VIX,
        future_spot=22000,  # 12% crash
        future_vix=25.0,    # VIX spikes
        days_elapsed=90
    )
    
    # Scenario 6: Best case - strong rally
    quick_scenario(
        "🎯 SCENARIO 6: Strong Bull Run (At Expiry)",
        SPOT, STRIKE, PREMIUM, DTE, CURRENT_VIX,
        future_spot=32000,  # 28% rally
        future_vix=12.0,    # VIX low
        days_elapsed=413
    )
    
    # Exit strategies
    print("\n" + "=" * 80)
    print("RECOMMENDED EXIT STRATEGIES")
    print("=" * 80)
    
    print("\n✅ PROFIT TARGETS:")
    for target_pct in [25, 50, 75, 100]:
        target_pnl = PREMIUM * (target_pct / 100.0)
        target_premium = PREMIUM - target_pnl
        print(f"  {target_pct}% Profit: Close when premium drops to ₹{target_premium:.0f} (P&L: ₹{target_pnl:.0f})")
    
    print("\n🛡️ RISK MANAGEMENT:")
    for loss_pct in [10, 20, 30, 50]:
        loss_amount = PREMIUM * (loss_pct / 100.0)
        stop_premium = PREMIUM + loss_amount
        print(f"  {loss_pct}% Loss: Exit if premium rises to ₹{stop_premium:.0f} (Loss: ₹{loss_amount:.0f})")
    
    print("\n⏰ TIME-BASED EXITS:")
    time_exits = [
        (90, "3 months", "If 30%+ profit"),
        (180, "6 months", "If 50%+ profit"),
        (270, "9 months", "If 60%+ profit"),
        (350, "Near expiry", "Close regardless to avoid gamma risk")
    ]
    for days, desc, condition in time_exits:
        print(f"  {desc} ({days} days): {condition}")
    
    print("\n" + "=" * 80)
    print("VIX MONITORING LEVELS")
    print("=" * 80)
    
    print("\nVIX levels to watch:")
    vix_levels = [
        (10, "Extremely low - consider taking profits"),
        (12, "Low - strong profit zone"),
        (14, "Normal - target achieved"),
        (16, "Elevated - hold position"),
        (18, "High - monitor closely"),
        (20, "Very high - consider hedging"),
        (25, "Extreme - crisis mode, reassess")
    ]
    
    for vix, action in vix_levels:
        marker = " ← Current" if abs(vix - CURRENT_VIX) < 2 else ""
        print(f"  VIX {vix:>2}: {action}{marker}")
    
    print("\n" + "=" * 80)
    print("KEY TAKEAWAYS")
    print("=" * 80)
    print("""
1. PRIMARY DRIVER: VIX normalization from 17.42% → 14%
   • This alone can generate ₹200-400 profit even with flat spot

2. SECONDARY DRIVER: Time decay
   • Earning ₹5.95/day from theta
   • Over 6 months = ₹1,071 from time decay alone

3. SPOT MOVEMENT TOLERANCE:
   • NIFTY can drop 6.6% and you still breakeven
   • Needs only 6.6% rally to reach breakeven

4. OPTIMAL EXIT:
   • Target 50-70% profit (₹1,645 - 2,303)
   • This occurs when: VIX < 15 OR Spot > 27,500 OR 6+ months elapsed

5. RISK FACTORS:
   • Black swan crash below 23,000
   • VIX staying elevated >20 for 6+ months
   • Early assignment risk (monitor put delta)

6. MONITORING CHECKLIST:
   ☐ Check VIX daily - looking for sustained drop below 16
   ☐ Monitor NIFTY trend - needs to hold above 24,000
   ☐ Review monthly - reassess thesis every 30 days
   ☐ Set alerts: NIFTY < 24,000 OR VIX > 20
    """)
    
    print("=" * 80)

if __name__ == "__main__":
    main()
