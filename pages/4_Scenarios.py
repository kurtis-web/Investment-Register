"""
Scenarios Page - What-if analysis and stress testing.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database import get_session
from src.portfolio import get_portfolio_overview
from src.ai_advisor import is_ai_available, get_scenario_analysis
from src.calculations import format_currency
from src.styles import apply_dark_theme, COLORS, PLOTLY_LAYOUT, page_header, section_header

st.set_page_config(page_title="Scenarios | Investment Register", page_icon="🔮", layout="wide", initial_sidebar_state="expanded")

# Apply dark theme
apply_dark_theme()

from src.sidebar import render_sidebar
render_sidebar()

page_header("Scenario Analysis", "What-if analysis and stress testing")

session = get_session()

try:
    portfolio = get_portfolio_overview(session)
    summary = portfolio['summary']

    if summary['investment_count'] == 0:
        st.info("Add investments before running scenario analysis.")
        st.stop()

    st.markdown("""
    Analyze how your portfolio might perform under different market scenarios.
    Select a scenario below to see estimated impacts on your holdings.
    """)

    # Portfolio summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Current Portfolio Value", format_currency(summary['total_value_cad']))
    with col2:
        st.metric("Current Gain/Loss", format_currency(summary['total_gain']))
    with col3:
        st.metric("Return", f"{summary['total_gain_pct']:+.1f}%")

    st.markdown("---")

    # Scenario selection
    st.subheader("Select Scenario")

    scenarios = {
        "market_crash": {
            "name": "Market Crash",
            "description": "30% decline in global equity markets over 3 months",
            "icon": "📉",
            "assumptions": {
                "Public Equities": -30,
                "Private Business": -20,
                "Venture Fund": -25,
                "Venture Entity": -30,
                "Real Estate": -10,
                "Gold": +5,
                "Crypto": -50,
                "Cash & Equivalents": 0,
                "Bonds": +5
            }
        },
        "recession": {
            "name": "Recession",
            "description": "Canadian recession with GDP declining 2% over 12 months",
            "icon": "📊",
            "assumptions": {
                "Public Equities": -20,
                "Private Business": -15,
                "Venture Fund": -20,
                "Venture Entity": -25,
                "Real Estate": -15,
                "Gold": +10,
                "Crypto": -30,
                "Cash & Equivalents": 0,
                "Bonds": +3
            }
        },
        "inflation": {
            "name": "High Inflation",
            "description": "Inflation rising to 8% with aggressive rate hikes",
            "icon": "📈",
            "assumptions": {
                "Public Equities": -15,
                "Private Business": -5,
                "Venture Fund": -15,
                "Venture Entity": -20,
                "Real Estate": +5,
                "Gold": +15,
                "Crypto": -20,
                "Cash & Equivalents": -5,
                "Bonds": -10
            }
        },
        "rate_hike": {
            "name": "Rate Shock",
            "description": "Bank of Canada raising rates by 200 basis points",
            "icon": "🏦",
            "assumptions": {
                "Public Equities": -10,
                "Private Business": -5,
                "Venture Fund": -10,
                "Venture Entity": -15,
                "Real Estate": -20,
                "Gold": 0,
                "Crypto": -15,
                "Cash & Equivalents": +2,
                "Bonds": -8
            }
        },
        "cad_depreciation": {
            "name": "CAD Depreciation",
            "description": "Canadian dollar declining 15% against USD",
            "icon": "💵",
            "assumptions": {
                "Public Equities": +10,  # USD holdings gain value
                "Private Business": 0,
                "Venture Fund": +5,
                "Venture Entity": +5,
                "Real Estate": 0,
                "Gold": +15,
                "Crypto": +15,
                "Cash & Equivalents": 0,
                "Bonds": 0
            }
        },
        "tech_crash": {
            "name": "Tech Crash",
            "description": "Technology sector declining 40% while other sectors flat",
            "icon": "💻",
            "assumptions": {
                "Public Equities": -25,  # Assuming some tech exposure
                "Private Business": -10,
                "Venture Fund": -40,
                "Venture Entity": -40,
                "Real Estate": 0,
                "Gold": +5,
                "Crypto": -35,
                "Cash & Equivalents": 0,
                "Bonds": +3
            }
        },
        "real_estate_correction": {
            "name": "Real Estate Correction",
            "description": "Canadian real estate values declining 25%",
            "icon": "🏠",
            "assumptions": {
                "Public Equities": -5,
                "Private Business": -5,
                "Venture Fund": 0,
                "Venture Entity": 0,
                "Real Estate": -25,
                "Gold": +3,
                "Crypto": 0,
                "Cash & Equivalents": 0,
                "Bonds": +2
            }
        }
    }

    # Scenario cards
    col1, col2, col3 = st.columns(3)
    cols = [col1, col2, col3]

    selected_scenario = None

    for i, (key, scenario) in enumerate(scenarios.items()):
        with cols[i % 3]:
            if st.button(
                f"{scenario['icon']} {scenario['name']}",
                key=f"scenario_{key}",
                use_container_width=True
            ):
                selected_scenario = key

    # Show analysis if scenario selected
    if selected_scenario:
        scenario = scenarios[selected_scenario]

        st.markdown("---")
        st.subheader(f"{scenario['icon']} {scenario['name']} Analysis")
        st.markdown(f"**Scenario:** {scenario['description']}")

        # Calculate impact
        impact_data = []
        total_impact = 0

        for ac, data in portfolio['by_asset_class'].items():
            impact_pct = scenario['assumptions'].get(ac, 0)
            impact_value = data['value'] * (impact_pct / 100)
            new_value = data['value'] + impact_value
            total_impact += impact_value

            impact_data.append({
                'Asset Class': ac,
                'Current Value': data['value'],
                'Impact (%)': impact_pct,
                'Impact ($)': impact_value,
                'New Value': new_value
            })

        # Summary metrics
        new_portfolio_value = summary['total_value_cad'] + total_impact
        impact_pct = (total_impact / summary['total_value_cad']) * 100

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Current Value",
                format_currency(summary['total_value_cad'])
            )

        with col2:
            st.metric(
                "Estimated New Value",
                format_currency(new_portfolio_value),
                delta=format_currency(total_impact),
                delta_color="inverse" if total_impact < 0 else "normal"
            )

        with col3:
            st.metric(
                "Portfolio Impact",
                f"{impact_pct:+.1f}%",
                delta=format_currency(total_impact)
            )

        with col4:
            at_risk = abs(total_impact) if total_impact < 0 else 0
            st.metric("Value at Risk", format_currency(at_risk))

        st.markdown("---")

        # Impact by asset class
        st.markdown("### Impact by Asset Class")

        df_impact = pd.DataFrame(impact_data)
        df_impact = df_impact.sort_values('Impact ($)')

        # Waterfall chart
        fig = go.Figure()

        colors = [COLORS['danger'] if x < 0 else COLORS['success'] for x in df_impact['Impact ($)']]

        fig.add_trace(go.Bar(
            x=df_impact['Asset Class'],
            y=df_impact['Impact ($)'],
            marker_color=colors,
            text=[f"${x/1000:+.0f}K" for x in df_impact['Impact ($)']],
            textposition='outside'
        ))

        fig.update_layout(
            yaxis_title="Impact ($)",
            xaxis_title="Asset Class",
            height=400
        )

        st.plotly_chart(fig, use_container_width=True)

        # Detailed table
        display_df = df_impact.copy()
        display_df['Current Value'] = display_df['Current Value'].apply(lambda x: f"${x:,.0f}")
        display_df['Impact (%)'] = display_df['Impact (%)'].apply(lambda x: f"{x:+.0f}%")
        display_df['Impact ($)'] = display_df['Impact ($)'].apply(lambda x: f"${x:+,.0f}")
        display_df['New Value'] = display_df['New Value'].apply(lambda x: f"${x:,.0f}")

        st.dataframe(display_df, use_container_width=True, hide_index=True)

        st.markdown("---")

        # Most affected holdings
        st.markdown("### Most Affected Holdings")

        holdings_impact = []
        for h in portfolio['holdings']:
            impact_pct = scenario['assumptions'].get(h['asset_class'], 0)
            impact_value = h['current_value'] * (impact_pct / 100)
            holdings_impact.append({
                'name': h['name'],
                'asset_class': h['asset_class'],
                'current_value': h['current_value'],
                'impact_pct': impact_pct,
                'impact_value': impact_value
            })

        # Sort by absolute impact
        holdings_impact.sort(key=lambda x: abs(x['impact_value']), reverse=True)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Most Negatively Affected:**")
            for h in holdings_impact[:5]:
                if h['impact_value'] < 0:
                    st.markdown(
                        f"- **{h['name']}**: {format_currency(h['impact_value'])} ({h['impact_pct']:+.0f}%)"
                    )

        with col2:
            st.markdown("**Potential Beneficiaries:**")
            for h in holdings_impact[:5]:
                if h['impact_value'] > 0:
                    st.markdown(
                        f"- **{h['name']}**: {format_currency(h['impact_value'])} ({h['impact_pct']:+.0f}%)"
                    )

        st.markdown("---")

        # AI Analysis (if available)
        if is_ai_available():
            st.markdown("### AI Deep-Dive Analysis")

            if st.button("Get AI Analysis", key="ai_scenario"):
                with st.spinner("Generating detailed scenario analysis..."):
                    ai_analysis = get_scenario_analysis(portfolio, selected_scenario)

                    if ai_analysis:
                        st.markdown(ai_analysis)
                    else:
                        st.error("Failed to generate AI analysis.")
        else:
            st.info("Set up your Anthropic API key on the AI Advisor page for deeper analysis.")

    else:
        st.markdown("---")
        st.info("👆 Select a scenario above to see how your portfolio might be affected.")

    # Custom scenario builder
    st.markdown("---")
    st.subheader("📝 Custom Scenario Builder")

    with st.expander("Create Custom Scenario"):
        st.markdown("Define your own scenario with custom impact percentages for each asset class.")

        custom_assumptions = {}
        cols = st.columns(3)

        for i, ac in enumerate(portfolio['by_asset_class'].keys()):
            with cols[i % 3]:
                custom_assumptions[ac] = st.slider(
                    ac,
                    min_value=-50,
                    max_value=50,
                    value=0,
                    step=5,
                    format="%d%%",
                    key=f"custom_{ac}"
                )

        if st.button("Analyze Custom Scenario"):
            # Calculate custom impact
            total_impact = 0
            for ac, data in portfolio['by_asset_class'].items():
                impact_pct = custom_assumptions.get(ac, 0)
                impact_value = data['value'] * (impact_pct / 100)
                total_impact += impact_value

            new_value = summary['total_value_cad'] + total_impact
            impact_pct = (total_impact / summary['total_value_cad']) * 100

            st.metric(
                "Portfolio Impact",
                f"{impact_pct:+.1f}%",
                delta=format_currency(total_impact)
            )
            st.metric(
                "New Portfolio Value",
                format_currency(new_value)
            )

finally:
    session.close()
