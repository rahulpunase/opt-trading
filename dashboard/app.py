import os
from datetime import date

import httpx
import streamlit as st

API_BASE = os.getenv("API_BASE", "http://localhost:8000")

st.set_page_config(page_title="Kite Trader Dashboard", layout="wide")
st.title("Kite Trader — Multi-Strategy Dashboard")
st.caption(f"Date: {date.today().strftime('%d %b %Y')}")


def fetch(path: str):
    try:
        r = httpx.get(f"{API_BASE}{path}", timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error ({path}): {e}")
        return None


# Portfolio summary
portfolio = fetch("/portfolio")
if portfolio:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Daily P&L", f"₹{portfolio['daily_pnl']:,.2f}")
    col2.metric("Daily Loss Cap", f"₹{portfolio['daily_loss_cap']:,.2f}")
    col3.metric("Margin Used", f"{portfolio['margin_used_pct']:.1f}%")
    col4.metric("Strategies Running", len(portfolio["strategies_running"]))

st.divider()

# Strategies table
st.subheader("Strategies")
strategies = fetch("/strategies")
if strategies:
    for s in strategies:
        with st.expander(f"{s['name']} | trades={s['trades_today']} | positions={s['open_positions']}"):
            col1, col2, col3 = st.columns(3)
            col1.write(f"**Paper trade:** {s['paper_trade']}")
            col2.write(f"**Enabled:** {s['enabled']}")
            col3.write(f"**Open positions:** {s['open_positions']}")

            positions_data = fetch(f"/strategy/{s['name']}/positions")
            if positions_data and positions_data.get("positions"):
                st.json(positions_data["positions"])
            else:
                st.write("No open positions.")

st.divider()

# Strategy control
st.subheader("Strategy Control")
strategy_name = st.text_input("Strategy name")
col1, col2, col3 = st.columns(3)

if col1.button("Start"):
    if strategy_name:
        try:
            r = httpx.post(f"{API_BASE}/strategy/start", json={"name": strategy_name}, timeout=10)
            st.success(r.json())
        except Exception as e:
            st.error(str(e))

if col2.button("Stop"):
    if strategy_name:
        try:
            r = httpx.post(f"{API_BASE}/strategy/stop", json={"name": strategy_name}, timeout=10)
            st.success(r.json())
        except Exception as e:
            st.error(str(e))

if col3.button("Pause"):
    if strategy_name:
        try:
            r = httpx.post(f"{API_BASE}/strategy/pause", json={"name": strategy_name}, timeout=10)
            st.success(r.json())
        except Exception as e:
            st.error(str(e))

st.divider()
if st.button("Refresh"):
    st.rerun()
