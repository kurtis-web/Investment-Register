"""
Performance Page - Returns, benchmarks, and performance attribution.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database import get_session
from src.portfolio import get_portfolio_overview, calculate_portfolio_irr, get_performance_by_period
from src.market_data import get_benchmark_data, get_benchmark_returns
from src.calculations import format_currency, format_percentage, calculate_performance_attribution
from src.styles import apply_dark_theme, COLORS, PLOTLY_LAYOUT, page_header, section_header

st.set_page_config(page_title="Performance | Investment Register", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

# Apply dark theme
apply_dark_theme()

from src.sidebar import render_sidebar
render_sidebar()

page_header("Performance", "Returns, benchmarks, and performance attribution")

session = get_session()

try:
    portfolio = get_portfolio_overview(session)
    summary = portfolio['summary']

    if summary['investment_count'] == 0:
        st.info("No investments to analyze. Add investments from the Holdings page.")
        st.stop()

    # Performance period selector
    col1, col2 = st.columns([1, 3])
    with col1:
        period = st.selectbox("Time Period", ["1 Month", "3 Months", "1 Year", "YTD", "Since Inception"])
        period_map = {"1 Month": "1m", "3 Months": "3m", "1 Year": "1y", "YTD": "ytd", "Since Inception": "all"}

    st.markdown("---")

    # Portfolio Returns
    st.subheader("Portfolio Returns")

    perf = get_performance_by_period(session, period_map.get(period, "1m"))
    irr = calculate_portfolio_irr(session)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Simple Return", f"{summary['total_gain_pct']:+.1f}%")

    with col2:
        if irr is not None:
            st.metric("IRR (Annualized)", f"{irr:+.1f}%")
        else:
            st.metric("IRR (Annualized)", "N/A")

    with col3:
        st.metric("Total Gain/Loss", format_currency(summary['total_gain']))

    with col4:
        st.metric("Current Value", format_currency(summary['total_value_cad']))

    st.markdown("---")

    # Benchmark Comparison
    st.subheader("Benchmark Comparison")

    benchmarks = {
        "S&P 500": "^GSPC",
        "NASDAQ": "^IXIC",
        "TSX Composite": "^GSPTSE"
    }

    benchmark_returns = {}
    for name, symbol in benchmarks.items():
        returns = get_benchmark_returns(symbol)
        if returns:
            benchmark_returns[name] = returns

    # Create comparison table
    if benchmark_returns:
        comparison_data = []
        portfolio_return = summary['total_gain_pct']

        comparison_data.append({
            "": "Your Portfolio",
            "Total Return": f"{portfolio_return:+.1f}%",
            "1M": "N/A",  # Would need historical snapshots
            "3M": "N/A",
            "1Y": f"{portfolio_return:+.1f}%",
            "YTD": "N/A"
        })

        for name, returns in benchmark_returns.items():
            comparison_data.append({
                "": name,
                "Total Return": f"{returns.get('1y', 0):+.1f}%",
                "1M": f"{returns.get('1m', 0):+.1f}%",
                "3M": f"{returns.get('3m', 0):+.1f}%",
                "1Y": f"{returns.get('1y', 0):+.1f}%",
                "YTD": f"{returns.get('ytd', 0):+.1f}%"
            })

        df_comparison = pd.DataFrame(comparison_data)
        st.dataframe(df_comparison, use_container_width=True, hide_index=True)

        # Benchmark chart
        st.markdown("### Benchmark Performance (1 Year)")

        fig = go.Figure()

        for name, symbol in benchmarks.items():
            data = get_benchmark_data(symbol, period='1y')
            if data is not None and not data.empty:
                # Normalize to 100
                normalized = (data['Close'] / data['Close'].iloc[0]) * 100
                fig.add_trace(go.Scatter(
                    x=data.index,
                    y=normalized,
                    mode='lines',
                    name=name
                ))

        fig.update_layout(
            yaxis_title="Normalized Value (100 = Start)",
            xaxis_title="Date",
            hovermode='x unified',
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Performance by Asset Class
    st.subheader("Performance by Asset Class")

    asset_class_perf = []
    for ac, data in portfolio['by_asset_class'].items():
        gain = data['value'] - data['cost']
        gain_pct = (gain / data['cost'] * 100) if data['cost'] > 0 else 0
        asset_class_perf.append({
            'Asset Class': ac,
            'Current Value': data['value'],
            'Cost Basis': data['cost'],
            'Gain/Loss': gain,
            'Return (%)': gain_pct,
            'Weight': data['weight']
        })

    df_ac_perf = pd.DataFrame(asset_class_perf)
    df_ac_perf = df_ac_perf.sort_values('Return (%)', ascending=False)

    # Create bar chart
    fig = go.Figure()

    colors = ['green' if x >= 0 else 'red' for x in df_ac_perf['Return (%)']]

    fig.add_trace(go.Bar(
        x=df_ac_perf['Asset Class'],
        y=df_ac_perf['Return (%)'],
        marker_color=colors,
        text=[f"{x:+.1f}%" for x in df_ac_perf['Return (%)']],
        textposition='outside'
    ))

    fig.update_layout(
        yaxis_title="Return (%)",
        xaxis_title="Asset Class",
        height=400,
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)

    # Detailed table
    display_df = df_ac_perf.copy()
    display_df['Current Value'] = display_df['Current Value'].apply(lambda x: f"${x:,.0f}")
    display_df['Cost Basis'] = display_df['Cost Basis'].apply(lambda x: f"${x:,.0f}")
    display_df['Gain/Loss'] = display_df['Gain/Loss'].apply(lambda x: f"+${x:,.0f}" if x >= 0 else f"-${abs(x):,.0f}")
    display_df['Return (%)'] = display_df['Return (%)'].apply(lambda x: f"{x:+.1f}%")
    display_df['Weight'] = display_df['Weight'].apply(lambda x: f"{x:.1f}%")

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Performance by Entity
    st.subheader("Performance by Entity")

    entity_perf = []
    for entity, data in portfolio['by_entity'].items():
        gain = data['value'] - data['cost']
        gain_pct = (gain / data['cost'] * 100) if data['cost'] > 0 else 0
        entity_perf.append({
            'Entity': entity,
            'Current Value': data['value'],
            'Cost Basis': data['cost'],
            'Gain/Loss': gain,
            'Return (%)': gain_pct,
            'Weight': data['weight']
        })

    df_entity_perf = pd.DataFrame(entity_perf)

    col1, col2 = st.columns(2)

    with col1:
        for _, row in df_entity_perf.iterrows():
            color = "🟢" if row['Return (%)'] >= 0 else "🔴"
            st.metric(
                f"{color} {row['Entity']}",
                format_currency(row['Current Value']),
                delta=f"{row['Return (%)']:+.1f}%"
            )

    with col2:
        fig = px.pie(
            df_entity_perf,
            values='Current Value',
            names='Entity',
            hole=0.4
        )
        fig.update_layout(height=300, margin=dict(t=20, b=20, l=20, r=20))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # Top and Bottom Performers
    st.subheader("Individual Performance")

    holdings = portfolio['holdings']

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Top Performers")
        top_performers = sorted(holdings, key=lambda x: x['unrealized_gain_pct'], reverse=True)[:5]

        for h in top_performers:
            st.markdown(
                f"**{h['name']}** ({h['asset_class']}): "
                f"+{h['unrealized_gain_pct']:.1f}% ({format_currency(h['unrealized_gain'])})"
            )

    with col2:
        st.markdown("### Bottom Performers")
        bottom_performers = sorted(holdings, key=lambda x: x['unrealized_gain_pct'])[:5]

        for h in bottom_performers:
            color = "🟢" if h['unrealized_gain_pct'] >= 0 else "🔴"
            st.markdown(
                f"{color} **{h['name']}** ({h['asset_class']}): "
                f"{h['unrealized_gain_pct']:+.1f}% ({format_currency(h['unrealized_gain'])})"
            )

finally:
    session.close()
