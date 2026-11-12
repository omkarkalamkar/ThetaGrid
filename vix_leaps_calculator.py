"""
VIX-Inflated LEAPS Put Selling Calculator
Analyzes deep ITM put selling strategies when VIX is elevated
"""
import math
import random
from datetime import datetime, timedelta

# Simple normal distribution approximation
def norm_cdf(x):
    """Cumulative distribution function for standard normal"""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def norm_pdf(x):
    """Probability density function for standard normal"""
    return math.exp(-0.5 * x**2) / math.sqrt(2 * math.pi)

class VIXLEAPSCalculator:
    """Calculator for VIX-inflated LEAPS put selling analysis"""
    
    def __init__(self, spot, strike, premium, dte, current_vix, risk_free_rate=0.07):
        self.spot = spot
        self.strike = strike
        self.premium = premium
        self.dte = dte
        self.dte_years = dte / 365.0
        self.current_vix = current_vix / 100.0  # Convert to decimal
        self.risk_free_rate = risk_free_rate
        
    def calculate_intrinsic_value(self):
        """Calculate intrinsic value for ITM put"""
        return max(0, self.strike - self.spot)
    
    def calculate_time_value(self):
        """Calculate time value (extrinsic value)"""
        intrinsic = self.calculate_intrinsic_value()
        return self.premium - intrinsic
    
    def black_scholes_put(self, spot, strike, time_years, volatility, r):
        """Calculate theoretical put price using Black-Scholes"""
        if time_years <= 0:
            return max(0, strike - spot)
        
        d1 = (math.log(spot / strike) + (r + 0.5 * volatility**2) * time_years) / (volatility * math.sqrt(time_years))
        d2 = d1 - volatility * math.sqrt(time_years)
        
        put_price = strike * math.exp(-r * time_years) * norm_cdf(-d2) - spot * norm_cdf(-d1)
        return put_price
    
    def calculate_greeks(self, volatility=None):
        """Calculate option Greeks"""
        if volatility is None:
            volatility = self.current_vix
            
        t = self.dte_years
        if t <= 0:
            return {'delta': -1.0 if self.spot < self.strike else 0.0, 'gamma': 0, 'theta': 0, 'vega': 0}
        
        d1 = (math.log(self.spot / self.strike) + (self.risk_free_rate + 0.5 * volatility**2) * t) / (volatility * math.sqrt(t))
        d2 = d1 - volatility * math.sqrt(t)
        
        # Put Greeks
        delta = -norm_cdf(-d1)
        gamma = norm_pdf(d1) / (self.spot * volatility * math.sqrt(t))
        theta = (-(self.spot * norm_pdf(d1) * volatility) / (2 * math.sqrt(t)) 
                 - self.risk_free_rate * self.strike * math.exp(-self.risk_free_rate * t) * norm_cdf(-d2))
        theta_daily = theta / 365.0
        vega = self.spot * norm_pdf(d1) * math.sqrt(t) * 0.01  # Per 1% change in IV
        
        return {
            'delta': round(delta, 4),
            'gamma': round(gamma, 6),
            'theta': round(theta, 2),
            'theta_daily': round(theta_daily, 2),
            'vega': round(vega, 2)
        }
    
    def calculate_vix_impact(self, target_vix_levels):
        """Calculate P&L impact from VIX changes"""
        results = []
        
        for target_vix in target_vix_levels:
            target_vol = target_vix / 100.0
            new_premium = self.black_scholes_put(
                self.spot, self.strike, self.dte_years, target_vol, self.risk_free_rate
            )
            pnl = self.premium - new_premium
            pnl_percent = (pnl / self.premium) * 100
            
            results.append({
                'target_vix': target_vix,
                'new_premium': round(new_premium, 2),
                'pnl': round(pnl, 2),
                'pnl_percent': round(pnl_percent, 2)
            })
        
        return results
    
    def time_decay_analysis(self, days_forward=None):
        """Analyze theta decay over time"""
        if days_forward is None:
            days_forward = min(self.dte, 180)  # Max 180 days or till expiry
        
        results = []
        days = list(range(0, days_forward + 1, 7))  # Weekly snapshots
        
        for day in days:
            remaining_dte = self.dte - day
            if remaining_dte < 0:
                break
                
            time_years = remaining_dte / 365.0
            premium_at_day = self.black_scholes_put(
                self.spot, self.strike, time_years, self.current_vix, self.risk_free_rate
            )
            pnl = self.premium - premium_at_day
            
            results.append({
                'day': day,
                'remaining_dte': remaining_dte,
                'premium': round(premium_at_day, 2),
                'pnl': round(pnl, 2),
                'pnl_percent': round((pnl / self.premium) * 100, 2)
            })
        
        return pd.DataFrame(results)
    
    def spot_scenario_analysis(self, spot_range_percent=20):
        """Analyze P&L across different spot prices"""
        spot_min = self.spot * (1 - spot_range_percent / 100)
        spot_max = self.spot * (1 + spot_range_percent / 100)
        spot_levels = np.linspace(spot_min, spot_max, 21)
        
        results = []
        
        for spot_level in spot_levels:
            # At expiry (no time value)
            expiry_value = max(0, self.strike - spot_level)
            pnl_at_expiry = self.premium - expiry_value
            
            # Current (with time value remaining)
            current_premium = self.black_scholes_put(
                spot_level, self.strike, self.dte_years, self.current_vix, self.risk_free_rate
            )
            current_pnl = self.premium - current_premium
            
            results.append({
                'spot': round(spot_level, 2),
                'spot_change_%': round(((spot_level - self.spot) / self.spot) * 100, 2),
                'expiry_value': round(expiry_value, 2),
                'pnl_at_expiry': round(pnl_at_expiry, 2),
                'current_premium': round(current_premium, 2),
                'current_pnl': round(current_pnl, 2)
            })
        
        return pd.DataFrame(results)
    
    def monte_carlo_simulation(self, num_simulations=10000, vix_mean_reversion_target=14, 
                               vix_mean_reversion_speed=0.3):
        """
        Monte Carlo simulation for final P&L distribution
        Includes spot movement AND VIX mean reversion
        """
        results = []
        
        # Annualized volatility
        annual_vol = self.current_vix
        
        for _ in range(num_simulations):
            # Simulate spot price at expiry (geometric Brownian motion)
            drift = self.risk_free_rate - 0.5 * annual_vol**2
            shock = annual_vol * np.sqrt(self.dte_years) * np.random.randn()
            final_spot = self.spot * np.exp(drift * self.dte_years + shock)
            
            # Simulate VIX mean reversion
            # VIX tends to revert to long-term mean over time
            vix_shock = np.random.randn() * 0.05  # Random noise
            time_factor = 1 - np.exp(-vix_mean_reversion_speed * self.dte_years)
            final_vix = (self.current_vix * 100) * (1 - time_factor) + vix_mean_reversion_target * time_factor + vix_shock * 100
            final_vix = max(8, min(35, final_vix))  # Bound between 8-35
            
            # Put value at expiry
            put_value = max(0, self.strike - final_spot)
            
            # P&L
            pnl = self.premium - put_value
            
            results.append({
                'final_spot': final_spot,
                'final_vix': final_vix,
                'put_value': put_value,
                'pnl': pnl
            })
        
        df = pd.DataFrame(results)
        
        # Calculate statistics
        stats = {
            'mean_pnl': df['pnl'].mean(),
            'median_pnl': df['pnl'].median(),
            'std_pnl': df['pnl'].std(),
            'prob_profit': (df['pnl'] > 0).sum() / num_simulations * 100,
            'prob_max_profit': (df['pnl'] >= self.premium * 0.8).sum() / num_simulations * 100,
            'percentile_5': df['pnl'].quantile(0.05),
            'percentile_25': df['pnl'].quantile(0.25),
            'percentile_75': df['pnl'].quantile(0.75),
            'percentile_95': df['pnl'].quantile(0.95),
            'mean_final_spot': df['final_spot'].mean(),
            'mean_final_vix': df['final_vix'].mean()
        }
        
        return df, stats
    
    def calculate_breakeven(self):
        """Calculate breakeven spot price at expiry"""
        # For short put: Breakeven = Strike - Premium Collected
        breakeven = self.strike - self.premium
        breakeven_move_percent = ((breakeven - self.spot) / self.spot) * 100
        
        return {
            'breakeven': round(breakeven, 2),
            'breakeven_move_%': round(breakeven_move_percent, 2)
        }
    
    def vix_mean_reversion_scenarios(self):
        """Calculate different VIX mean reversion scenarios"""
        scenarios = [
            {'name': 'Fast Reversion (3 months)', 'target_vix': 14, 'days': 90},
            {'name': 'Normal Reversion (6 months)', 'target_vix': 14, 'days': 180},
            {'name': 'Slow Reversion (9 months)', 'target_vix': 15, 'days': 270},
            {'name': 'No Reversion (VIX stays high)', 'target_vix': self.current_vix * 100, 'days': self.dte}
        ]
        
        results = []
        
        for scenario in scenarios:
            days = min(scenario['days'], self.dte)
            remaining_dte = self.dte - days
            time_years_remaining = remaining_dte / 365.0
            
            target_vol = scenario['target_vix'] / 100.0
            
            # Premium at that point
            premium_at_day = self.black_scholes_put(
                self.spot, self.strike, time_years_remaining, target_vol, self.risk_free_rate
            )
            
            pnl = self.premium - premium_at_day
            
            results.append({
                'scenario': scenario['name'],
                'days_elapsed': days,
                'vix_at_point': scenario['target_vix'],
                'premium': round(premium_at_day, 2),
                'pnl': round(pnl, 2),
                'pnl_percent': round((pnl / self.premium) * 100, 2)
            })
        
        return pd.DataFrame(results)
    
    def combined_vix_time_decay(self, vix_target=14, days_forward=180):
        """Analyze combined effect of VIX normalization + time decay"""
        results = []
        days = list(range(0, min(days_forward, self.dte) + 1, 14))  # Bi-weekly
        
        current_vix_decimal = self.current_vix * 100
        
        for day in days:
            remaining_dte = self.dte - day
            if remaining_dte < 0:
                break
            
            # Exponential VIX mean reversion
            time_factor = 1 - np.exp(-0.3 * (day / 365.0))
            vix_at_day = current_vix_decimal * (1 - time_factor) + vix_target * time_factor
            
            time_years = remaining_dte / 365.0
            premium_at_day = self.black_scholes_put(
                self.spot, self.strike, time_years, vix_at_day / 100.0, self.risk_free_rate
            )
            
            pnl = self.premium - premium_at_day
            
            results.append({
                'day': day,
                'vix': round(vix_at_day, 2),
                'remaining_dte': remaining_dte,
                'premium': round(premium_at_day, 2),
                'pnl': round(pnl, 2),
                'pnl_percent': round((pnl / self.premium) * 100, 2)
            })
        
        return pd.DataFrame(results)


def analyze_trade(spot, strike, premium, dte, current_vix):
    """Main analysis function"""
    
    calc = VIXLEAPSCalculator(spot, strike, premium, dte, current_vix)
    
    print("=" * 80)
    print(f"VIX-INFLATED LEAPS PUT SELLING ANALYSIS")
    print("=" * 80)
    print(f"\nTrade Details:")
    print(f"  Spot Price: ₹{spot:,.2f}")
    print(f"  Strike: ₹{strike:,.2f}")
    print(f"  Premium Collected: ₹{premium:,.2f}")
    print(f"  Days to Expiry: {dte} days ({dte/365:.2f} years)")
    print(f"  Current VIX: {current_vix:.2f}%")
    
    # Basic calculations
    intrinsic = calc.calculate_intrinsic_value()
    time_value = calc.calculate_time_value()
    breakeven = calc.calculate_breakeven()
    
    print(f"\n" + "=" * 80)
    print(f"VALUE DECOMPOSITION:")
    print("=" * 80)
    print(f"  Intrinsic Value: ₹{intrinsic:,.2f}")
    print(f"  Time Value: ₹{time_value:,.2f}")
    print(f"  Time Value %: {(time_value/premium)*100:.2f}%")
    print(f"  Breakeven at Expiry: ₹{breakeven['breakeven']:,.2f} ({breakeven['breakeven_move_%']:+.2f}% from spot)")
    
    # Greeks
    greeks = calc.calculate_greeks()
    print(f"\n" + "=" * 80)
    print(f"GREEKS (Short Position):")
    print("=" * 80)
    print(f"  Delta: {-greeks['delta']:.4f} (position gains ₹{-greeks['delta']:.2f} per ₹1 up move)")
    print(f"  Gamma: {-greeks['gamma']:.6f}")
    print(f"  Theta (Daily): ₹{-greeks['theta_daily']:.2f} (you GAIN this per day from decay)")
    print(f"  Vega: ₹{-greeks['vega']:.2f} per 1% VIX drop (you GAIN when VIX drops)")
    
    # VIX impact
    print(f"\n" + "=" * 80)
    print(f"VIX IMPACT ANALYSIS:")
    print("=" * 80)
    vix_levels = [10, 12, 14, 15, 16, current_vix, 20, 22, 25]
    vix_df = calc.calculate_vix_impact(vix_levels)
    print(vix_df.to_string(index=False))
    
    # VIX mean reversion scenarios
    print(f"\n" + "=" * 80)
    print(f"VIX MEAN REVERSION SCENARIOS (Spot Unchanged):")
    print("=" * 80)
    vix_scenarios = calc.vix_mean_reversion_scenarios()
    print(vix_scenarios.to_string(index=False))
    
    # Combined VIX + Time decay
    print(f"\n" + "=" * 80)
    print(f"COMBINED VIX NORMALIZATION + TIME DECAY (First 180 days):")
    print("=" * 80)
    combined_df = calc.combined_vix_time_decay(vix_target=14, days_forward=180)
    print(combined_df.to_string(index=False))
    
    # Spot scenario analysis
    print(f"\n" + "=" * 80)
    print(f"SPOT PRICE SCENARIO ANALYSIS (At Expiry):")
    print("=" * 80)
    spot_df = calc.spot_scenario_analysis(spot_range_percent=25)
    print(spot_df[['spot', 'spot_change_%', 'expiry_value', 'pnl_at_expiry']].to_string(index=False))
    
    # Monte Carlo
    print(f"\n" + "=" * 80)
    print(f"MONTE CARLO SIMULATION (10,000 scenarios):")
    print("=" * 80)
    _, mc_stats = calc.monte_carlo_simulation(num_simulations=10000)
    print(f"  Mean P&L: ₹{mc_stats['mean_pnl']:,.2f}")
    print(f"  Median P&L: ₹{mc_stats['median_pnl']:,.2f}")
    print(f"  Std Deviation: ₹{mc_stats['std_pnl']:,.2f}")
    print(f"  Probability of Profit: {mc_stats['prob_profit']:.2f}%")
    print(f"  Probability of >80% Max Profit: {mc_stats['prob_max_profit']:.2f}%")
    print(f"  5th Percentile (Worst Case): ₹{mc_stats['percentile_5']:,.2f}")
    print(f"  95th Percentile (Best Case): ₹{mc_stats['percentile_95']:,.2f}")
    print(f"  Expected Final Spot: ₹{mc_stats['mean_final_spot']:,.2f}")
    print(f"  Expected Final VIX: {mc_stats['mean_final_vix']:.2f}%")
    
    # ROI calculations
    print(f"\n" + "=" * 80)
    print(f"RETURN ON INVESTMENT:")
    print("=" * 80)
    lot_size = 50  # NIFTY lot size
    premium_collected = premium * lot_size
    margin_required = strike * lot_size * 0.15  # Approx 15% margin
    
    print(f"  Premium per lot: ₹{premium_collected:,.2f}")
    print(f"  Estimated Margin: ₹{margin_required:,.2f}")
    print(f"  ROI if max profit: {(premium_collected/margin_required)*100:.2f}%")
    print(f"  Annualized ROI: {(premium_collected/margin_required)*(365/dte)*100:.2f}%")
    
    print("\n" + "=" * 80)
    
    return calc


if __name__ == "__main__":
    # Your trade parameters
    SPOT = 25045
    STRIKE = 30000
    PREMIUM = 3290
    DTE = 413  # Days to Dec 27, 2027
    CURRENT_VIX = 17.42
    
    calc = analyze_trade(SPOT, STRIKE, PREMIUM, DTE, CURRENT_VIX)
