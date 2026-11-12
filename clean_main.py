import re

with open("backend/main.py", "r") as f:
    content = f.read()

# 1. Remove MockDataEngine class
content = re.sub(r'# ---------- Mock data generator ----------\nclass MockDataEngine:.*?mock_engine = MockDataEngine\(\)\n', '', content, flags=re.DOTALL)

# 2. Add global chains and setup market_state at top
setup_code = """
from persistence import update_persistence
p_data = update_persistence(None, None, None)
market_state["nifty"] = {"prev_close": p_data.get("NIFTY", 24770.0)}
market_state["sensex"] = {"prev_close": p_data.get("SENSEX", 81350.0)}
market_state["vix"] = {"prev_close": p_data.get("VIX", 12.85)}

global_chains = {"NIFTY": [], "SENSEX": []}
"""
content = re.sub(r'market_state: Dict\[str, Any\] = \{\}\n', 'market_state: Dict[str, Any] = {}\n' + setup_code, content)

# 3. Fix broadcast_loop
loop_fix = """
                from smartapi_client import live_engine, smart_client as sc
                data = {
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "demo_mode": False,
                    "nifty": {"prev_close": market_state["nifty"]["prev_close"]},
                    "sensex": {"prev_close": market_state["sensex"]["prev_close"]},
                    "vix": {"prev_close": market_state["vix"]["prev_close"]},
                    "gift_nifty": market_state.get("gift_nifty", {})
                }
                
                # NIFTY Live
"""
content = re.sub(r'                from smartapi_client import live_engine, smart_client as sc\n                data = mock_engine.tick\(is_live=True\)\n                data\["demo_mode"\] = False\n                \n                # NIFTY Live\n', loop_fix, content)

# 4. Replace mock_engine.nifty_prev_close with data["nifty"]["prev_close"] updates
content = re.sub(r'mock_engine\.nifty_prev_close = new_prev\.get\("NIFTY", mock_engine\.nifty_prev_close\)', 'market_state["nifty"]["prev_close"] = new_prev.get("NIFTY", market_state["nifty"]["prev_close"])', content)
content = re.sub(r'mock_engine\.sensex_prev_close = new_prev\.get\("SENSEX", mock_engine\.sensex_prev_close\)', 'market_state["sensex"]["prev_close"] = new_prev.get("SENSEX", market_state["sensex"]["prev_close"])', content)
content = re.sub(r'mock_engine\.vix_prev_close = new_prev\.get\("VIX", mock_engine\.vix_prev_close\)', 'market_state["vix"]["prev_close"] = new_prev.get("VIX", market_state["vix"]["prev_close"])', content)

# 5. Replace mock_engine.nifty_chain with global_chains["NIFTY"]
content = re.sub(r'mock_engine\.nifty_chain = live_chain', 'global_chains["NIFTY"] = live_chain', content)
content = re.sub(r'mock_engine\.sensex_chain = live_chain_s', 'global_chains["SENSEX"] = live_chain_s', content)
content = re.sub(r'mock_engine\.get_option_chain\(index\)', 'global_chains.get(index, [])', content)

# 6. Remove data = mock_engine.tick(is_live=False) block completely
content = re.sub(r'            else:\n                data = mock_engine\.tick\(is_live=False\)\n                data\["demo_mode"\] = True\n                # Replace with persistence values\n.*?\n                # Append straddle history', '            # Append straddle history', content, flags=re.DOTALL)

with open("backend/main.py", "w") as f:
    f.write(content)
