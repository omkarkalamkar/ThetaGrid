"""
Real-time VIX LEAPS Position Monitor
Tracks the NIFTY 30000 PE Dec 2027 position and provides alerts
Can be integrated with ThetaGrid backend
"""
import math
import json
from datetime import datetime, date

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

class VIXLEAPSPosition:
    """Monitor a VIX LEAPS put selling position"""
    
    def __init__(self, spot_entry, strike, premium_entry, expiry_date, entry_vix, quantity=1):
        self.spot_entry = spot_entry
        self.strike = strike
        self.premium_entry = premium_entry
        self.expiry_date = expiry_date
        self.entry_vix = entry_vix
        self.quantity = quantity
        self.lot_size = 50
        
        self.entry_date = datetime.now().date()
        
    def days_to_expiry(self, current_date=None):
        """Calculate days remaining to expiry"""
        if current_date is None:
            current_date = datetime.now().date()
        return (self.expiry_date - current_date).days
    
    def current_value(self, current_spot, current_vix):
        """Calculate current put value"""
        dte = self.days_to_expiry()
        if dte <= 0:
            return max(0, self.strike - current_spot)
        
        time_years = dte / 365.0
        return black_scholes_put(current_spot, self.strike, time_years, current_vix/100.0)
    
    def unrealized_pnl(self, current_spot, current_vix):
        """Calculate unrealized P&L"""
        current_put_value = self.current_value(current_spot, current_vix)
        pnl_per_contract = self.premium_entry - current_put_value
        pnl_total = pnl_per_contract * self.quantity * self.lot_size
        pnl_percent = (pnl_per_contract / self.premium_entry) * 100
        
        return {
            'current_put_value': round(current_put_value, 2),
            'pnl_per_contract': round(pnl_per_contract, 2),
            'pnl_total': round(pnl_total, 2),
            'pnl_percent': round(pnl_percent, 2),
            'entry_premium': self.premium_entry,
            'current_premium': round(current_put_value, 2)
        }
    
    def breakeven_price(self):
        """Calculate breakeven spot price at expiry"""
        return self.strike - self.premium_entry
    
    def risk_metrics(self, current_spot, current_vix):
        """Calculate risk metrics"""
        dte = self.days_to_expiry()
        time_years = max(0.001, dte / 365.0)
        vol = current_vix / 100.0
        
        # Greeks
        d1 = (math.log(current_spot / self.strike) + (0.07 + 0.5 * vol**2) * time_years) / (vol * math.sqrt(time_years))
        
        delta = -norm_cdf(-d1)
        gamma = norm_pdf(d1) / (current_spot * vol * math.sqrt(time_years))
        theta = (-(current_spot * norm_pdf(d1) * vol) / (2 * math.sqrt(time_years)) 
                 - 0.07 * self.strike * math.exp(-0.07 * time_years) * norm_cdf(-d1 + vol * math.sqrt(time_years)))
        vega = current_spot * norm_pdf(d1) * math.sqrt(time_years) * 0.01
        
        # For short position, invert signs
        return {
            'delta': round(-delta, 4),
            'gamma': round(-gamma, 6),
            'theta_daily': round(-theta/365, 2),
            'vega': round(-vega, 2),
            'days_held': (datetime.now().date() - self.entry_date).days,
            'days_remaining': dte,
            'time_elapsed_pct': round(((datetime.now().date() - self.entry_date).days / 
                                      ((self.expiry_date - self.entry_date).days)) * 100, 1)
        }
    
    def alerts(self, current_spot, current_vix):
        """Generate alerts based on current conditions"""
        alerts = []
        pnl = self.unrealized_pnl(current_spot, current_vix)
        risk = self.risk_metrics(current_spot, current_vix)
        breakeven = self.breakeven_price()
        
        # Profit alerts
        if pnl['pnl_percent'] >= 70:
            alerts.append({"level": "SUCCESS", "message": f"🎉 Excellent profit: {pnl['pnl_percent']:.1f}%. Consider taking profits!"})
        elif pnl['pnl_percent'] >= 50:
            alerts.append({"level": "INFO", "message": f"✅ Strong profit: {pnl['pnl_percent']:.1f}%. Target achieved."})
        elif pnl['pnl_percent'] >= 30:
            alerts.append({"level": "INFO", "message": f"💚 Good profit: {pnl['pnl_percent']:.1f}%. On track."})
        
        # Loss alerts
        if pnl['pnl_percent'] <= -50:
            alerts.append({"level": "CRITICAL", "message": f"🚨 SEVERE LOSS: {pnl['pnl_percent']:.1f}%. Consider exit or hedge!"})
        elif pnl['pnl_percent'] <= -30:
            alerts.append({"level": "WARNING", "message": f"⚠️  Heavy loss: {pnl['pnl_percent']:.1f}%. Monitor closely!"})
        elif pnl['pnl_percent'] <= -20:
            alerts.append({"level": "WARNING", "message": f"⚠️  Significant loss: {pnl['pnl_percent']:.1f}%. Stop loss zone."})
        
        # VIX alerts
        if current_vix < 13:
            alerts.append({"level": "INFO", "message": f"📉 VIX very low ({current_vix:.1f}%). Target achieved - consider profit taking."})
        elif current_vix > 22:
            alerts.append({"level": "WARNING", "message": f"📈 VIX spike ({current_vix:.1f}%). Monitor for crisis conditions."})
        elif current_vix < 15 and current_vix > self.entry_vix:
            alerts.append({"level": "INFO", "message": f"VIX normalized to {current_vix:.1f}% from {self.entry_vix:.1f}%. Thesis playing out."})
        
        # Spot alerts
        distance_to_breakeven = ((current_spot - breakeven) / current_spot) * 100
        if current_spot < breakeven:
            alerts.append({"level": "CRITICAL", "message": f"💥 BELOW BREAKEVEN! Spot: ₹{current_spot:,.0f}, BE: ₹{breakeven:,.0f}"})
        elif distance_to_breakeven < 5:
            alerts.append({"level": "WARNING", "message": f"⚠️  Near breakeven: {distance_to_breakeven:.1f}% cushion remaining."})
        
        # Time alerts
        if risk['days_remaining'] < 30:
            alerts.append({"level": "WARNING", "message": f"⏰ Less than 30 days to expiry. Gamma risk increasing!"})
        elif risk['days_remaining'] < 60:
            alerts.append({"level": "INFO", "message": f"⏰ Less than 60 days remaining. Consider exit strategy."})
        
        # Delta alerts
        if abs(risk['delta']) > 0.85:
            alerts.append({"level": "WARNING", "message": f"High delta ({risk['delta']:.2f}). Nearly same as short futures."})
        
        return alerts
    
    def to_dict(self, current_spot, current_vix):
        """Export complete position state as dict"""
        pnl = self.unrealized_pnl(current_spot, current_vix)
        risk = self.risk_metrics(current_spot, current_vix)
        alerts = self.alerts(current_spot, current_vix)
        
        return {
            'position': {
                'strike': self.strike,
                'entry_premium': self.premium_entry,
                'entry_spot': self.spot_entry,
                'entry_vix': self.entry_vix,
                'entry_date': self.entry_date.isoformat(),
                'expiry_date': self.expiry_date.isoformat(),
                'quantity': self.quantity,
                'lot_size': self.lot_size,
                'breakeven': round(self.breakeven_price(), 2)
            },
            'current': {
                'spot': current_spot,
                'vix': current_vix,
                'put_value': pnl['current_put_value'],
                'date': datetime.now().isoformat()
            },
            'pnl': pnl,
            'risk': risk,
            'alerts': alerts
        }


def monitor_position(current_spot, current_vix):
    """Main monitoring function - call this from your backend"""
    
    # Define the position
    position = VIXLEAPSPosition(
        spot_entry=25045,
        strike=30000,
        premium_entry=3290,
        expiry_date=date(2027, 12, 27),
        entry_vix=17.42,
        quantity=1  # Number of lots
    )
    
    # Get position state
    state = position.to_dict(current_spot, current_vix)
    
    # Print summary
    print("\n" + "=" * 80)
    print("VIX LEAPS POSITION MONITOR")
    print("=" * 80)
    print(f"\n📍 POSITION: Short {position.quantity} lot NIFTY {position.strike} PE {position.expiry_date.strftime('%b %Y')}")
    print(f"  Entry: ₹{position.premium_entry:,} @ Spot ₹{position.spot_entry:,} | VIX {position.entry_vix}%")
    print(f"  Current: ₹{state['pnl']['current_premium']:,} @ Spot ₹{current_spot:,} | VIX {current_vix}%")
    print(f"  Breakeven: ₹{state['position']['breakeven']:,}")
    
    print(f"\n💰 P&L:")
    pnl_emoji = "🟢" if state['pnl']['pnl_percent'] > 0 else "🔴"
    print(f"  {pnl_emoji} Per Contract: ₹{state['pnl']['pnl_per_contract']:,} ({state['pnl']['pnl_percent']:.1f}%)")
    print(f"  {pnl_emoji} Total ({position.quantity} lot): ₹{state['pnl']['pnl_total']:,}")
    
    print(f"\n📊 RISK METRICS:")
    print(f"  Delta: {state['risk']['delta']:.4f} | Gamma: {state['risk']['gamma']:.6f}")
    print(f"  Theta: +₹{state['risk']['theta_daily']:.2f}/day | Vega: +₹{state['risk']['vega']:.2f} per 1% VIX drop")
    print(f"  Days Held: {state['risk']['days_held']} | Remaining: {state['risk']['days_remaining']} ({state['risk']['time_elapsed_pct']:.1f}% elapsed)")
    
    if state['alerts']:
        print(f"\n🔔 ALERTS ({len(state['alerts'])}):")
        for alert in state['alerts']:
            print(f"  [{alert['level']}] {alert['message']}")
    else:
        print(f"\n✅ No alerts. Position healthy.")
    
    print("\n" + "=" * 80)
    
    return state


if __name__ == "__main__":
    # Test with current market conditions
    CURRENT_SPOT = 25045  # Update with live data
    CURRENT_VIX = 17.42   # Update with live data
    
    state = monitor_position(CURRENT_SPOT, CURRENT_VIX)
    
    # Can also export to JSON for API endpoint
    print("\n📤 JSON Export (for API):")
    print(json.dumps(state, indent=2))
