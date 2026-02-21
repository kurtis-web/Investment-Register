"""
AI Advisor Page - AI-powered investment recommendations and analysis.
"""

import streamlit as st
import pandas as pd
import os
import sys
import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database import get_session
from src.portfolio import get_portfolio_overview
from src.ai_advisor import (
    is_ai_available, get_portfolio_analysis, get_rebalancing_recommendations,
    get_risk_assessment, get_market_commentary, suggest_target_allocation,
    draft_investment_policy_statement
)
from src.calculations import format_currency
from src.styles import apply_dark_theme, COLORS, PLOTLY_LAYOUT, page_header, section_header

st.set_page_config(page_title="AI Advisor | Investment Register", page_icon="🤖", layout="wide", initial_sidebar_state="expanded")

# Apply dark theme
apply_dark_theme()

from src.sidebar import render_sidebar
render_sidebar()

page_header("AI Investment Advisor", "AI-powered recommendations and analysis")

# Check API key
if not is_ai_available():
    st.warning("""
    ### API Key Required

    To use the AI Advisor, you need to set your Anthropic API key.

    **Option 1: Environment Variable**
    ```bash
    export ANTHROPIC_API_KEY='your-api-key'
    ```

    **Option 2: Create a `.env` file**
    ```
    ANTHROPIC_API_KEY=your-api-key
    ```

    Get your API key from: https://console.anthropic.com/
    """)

    # Allow manual entry for session
    api_key = st.text_input("Or enter API key here (session only):", type="password")
    if api_key:
        os.environ['ANTHROPIC_API_KEY'] = api_key
        st.rerun()

    st.stop()

session = get_session()

try:
    portfolio = get_portfolio_overview(session)
    summary = portfolio['summary']

    if summary['investment_count'] == 0:
        st.info("Add investments before using the AI Advisor.")
        st.stop()

    # Load config for target allocation
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml')
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        target_allocation = config.get('investment_policy', {}).get('target_allocation', {})
    except:
        target_allocation = {}

    # Portfolio summary display
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Portfolio Value", format_currency(summary['total_value_cad']))
    with col2:
        st.metric("Total Return", f"{summary['total_gain_pct']:+.1f}%")
    with col3:
        st.metric("Positions", summary['investment_count'])

    st.markdown("---")

    # AI Analysis Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Portfolio Analysis",
        "⚖️ Rebalancing",
        "⚠️ Risk Assessment",
        "📰 Market Commentary",
        "📋 Investment Policy"
    ])

    with tab1:
        st.subheader("Portfolio Analysis")
        st.markdown("Get AI-powered insights on your portfolio's health, strengths, concerns, and recommendations.")

        if st.button("Generate Analysis", key="analysis"):
            with st.spinner("Analyzing your portfolio..."):
                analysis = get_portfolio_analysis(portfolio)

                if analysis:
                    st.markdown(analysis)
                else:
                    st.error("Failed to generate analysis. Please check your API key.")

    with tab2:
        st.subheader("Rebalancing Recommendations")
        st.markdown("Get specific suggestions for rebalancing your portfolio to meet target allocations.")

        # Show current vs target
        if target_allocation:
            st.markdown("### Current vs Target Allocation")

            comparison_data = []
            for ac, target in target_allocation.items():
                ac_display = ac.replace('_', ' ').title()
                actual = portfolio['by_asset_class'].get(ac, {}).get('weight', 0)
                diff = actual - (target * 100)

                comparison_data.append({
                    'Asset Class': ac_display,
                    'Target': f"{target * 100:.0f}%",
                    'Actual': f"{actual:.1f}%",
                    'Difference': f"{diff:+.1f}%",
                    'Action': "Reduce" if diff > 5 else ("Add" if diff < -5 else "OK")
                })

            st.dataframe(pd.DataFrame(comparison_data), use_container_width=True, hide_index=True)

        if st.button("Get Rebalancing Advice", key="rebalance"):
            with st.spinner("Generating rebalancing recommendations..."):
                advice = get_rebalancing_recommendations(portfolio, target_allocation)

                if advice:
                    st.markdown(advice)
                else:
                    st.error("Failed to generate recommendations.")

    with tab3:
        st.subheader("Risk Assessment")
        st.markdown("Comprehensive risk analysis including concentration, liquidity, and mitigation strategies.")

        # Show current risk metrics
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Current Risk Metrics")
            concentration = portfolio['risk']['concentration']
            liquidity = portfolio['risk']['liquidity']

            st.metric("HHI Index", f"{concentration.get('hhi', 0):.0f}")
            st.metric("Liquid Assets", f"{liquidity.get('liquid_pct', 0):.1f}%")

            if concentration.get('concentrated_positions'):
                st.warning(f"⚠️ {len(concentration['concentrated_positions'])} concentrated positions")

        with col2:
            if concentration.get('concentrated_positions'):
                st.markdown("### Concentrated Positions")
                for pos in concentration['concentrated_positions']:
                    st.markdown(f"- **{pos['name']}**: {pos['weight']:.1f}%")

        if st.button("Generate Risk Assessment", key="risk"):
            with st.spinner("Assessing portfolio risks..."):
                assessment = get_risk_assessment(portfolio)

                if assessment:
                    st.markdown(assessment)
                else:
                    st.error("Failed to generate assessment.")

    with tab4:
        st.subheader("Market Commentary")
        st.markdown("AI-generated market insights relevant to your portfolio holdings.")

        # Show what asset classes will be covered
        st.markdown("**Asset classes in your portfolio:**")
        st.markdown(", ".join(portfolio['by_asset_class'].keys()))

        if st.button("Generate Commentary", key="commentary"):
            with st.spinner("Generating market commentary..."):
                commentary = get_market_commentary(portfolio)

                if commentary:
                    st.markdown(commentary)
                else:
                    st.error("Failed to generate commentary.")

    with tab5:
        st.subheader("Investment Policy Statement")
        st.markdown("Generate a formal Investment Policy Statement based on your portfolio and preferences.")

        # Preference inputs
        col1, col2 = st.columns(2)

        with col1:
            risk_profile = st.selectbox(
                "Risk Profile",
                ["Conservative", "Moderate", "Aggressive"],
                index=2
            )
            horizon = st.selectbox(
                "Investment Horizon",
                ["Short-term (1-3 years)", "Medium-term (3-7 years)",
                 "Long-term (7+ years)", "Mixed (income + growth)"],
                index=3
            )

        with col2:
            liquidity_needs = st.selectbox(
                "Liquidity Requirements",
                ["Low", "Moderate", "High"],
                index=1
            )
            esg = st.text_input("ESG Considerations", placeholder="e.g., No fossil fuels, impact investing")

        restrictions = st.text_area("Investment Restrictions", placeholder="e.g., No tobacco, no gambling")

        if st.button("Draft Investment Policy Statement", key="ips"):
            with st.spinner("Drafting IPS..."):
                preferences = {
                    'risk_profile': risk_profile,
                    'horizon': horizon,
                    'liquidity': liquidity_needs,
                    'esg': esg if esg else 'None specified',
                    'restrictions': restrictions if restrictions else 'None specified'
                }

                ips = draft_investment_policy_statement(portfolio, preferences)

                if ips:
                    st.markdown(ips)

                    # Download button
                    st.download_button(
                        "Download IPS",
                        ips,
                        file_name="investment_policy_statement.md",
                        mime="text/markdown"
                    )
                else:
                    st.error("Failed to generate IPS.")

        st.markdown("---")

        # Target allocation suggestion
        st.subheader("AI-Suggested Target Allocation")
        st.markdown("Let AI suggest an optimal target allocation based on your risk profile.")

        if st.button("Suggest Target Allocation", key="suggest_allocation"):
            with st.spinner("Analyzing and suggesting allocation..."):
                suggestion = suggest_target_allocation(portfolio)

                if suggestion:
                    st.markdown(suggestion)
                else:
                    st.error("Failed to generate suggestion.")

finally:
    session.close()
