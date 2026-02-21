"""
Investment Register - Main Application
A comprehensive investment tracking and analysis dashboard for family offices.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import os
import sys

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))

from src.database import get_session, init_db, get_all_investments, get_all_entities
from src.portfolio import get_portfolio_overview, update_market_prices, get_recent_activity
from src.market_data import get_usd_cad_rate, get_fx_rate, get_stock_price
from src.calculations import format_currency, format_percentage
from src.styles import apply_theme, COLORS, PLOTLY_LAYOUT, apply_plotly_theme, page_header, section_header

# Page configuration
st.set_page_config(
    page_title="Investment Register",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database
init_db()

# Apply shared theme
apply_theme()

# Legacy CSS block removed — now uses shared apply_theme() from src/styles.py
_LEGACY_CSS_REMOVED = """

    /* Global Styles */
    .stApp {{
        background: {COLORS['bg_primary']};
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}

    /* Main content area */
    .main .block-container {{
        padding: 2rem 3rem;
        max-width: 100%;
    }}

    /* Sidebar styling */
    section[data-testid="stSidebar"] {{
        background: {COLORS['bg_secondary']};
        border-right: 1px solid {COLORS['border']};
    }}

    section[data-testid="stSidebar"] .stMarkdown {{
        color: {COLORS['text_secondary']};
    }}

    /* Headers */
    h1 {{
        color: {COLORS['text_primary']} !important;
        font-weight: 600 !important;
        letter-spacing: -0.02em;
        margin-bottom: 1.5rem !important;
    }}

    h2, h3 {{
        color: {COLORS['text_primary']} !important;
        font-weight: 500 !important;
        letter-spacing: -0.01em;
    }}

    /* Metric cards */
    [data-testid="stMetric"] {{
        background: {COLORS['bg_card']};
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
        padding: 1.25rem;
        transition: all 0.2s ease;
    }}

    [data-testid="stMetric"]:hover {{
        background: {COLORS['bg_card_hover']};
        border-color: {COLORS['border_light']};
        transform: translateY(-2px);
    }}

    [data-testid="stMetric"] label {{
        color: {COLORS['text_secondary']} !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}

    [data-testid="stMetric"] [data-testid="stMetricValue"] {{
        color: {COLORS['text_primary']} !important;
        font-size: 1.75rem !important;
        font-weight: 600 !important;
    }}

    [data-testid="stMetric"] [data-testid="stMetricDelta"] {{
        font-weight: 500 !important;
    }}

    /* Positive/Negative delta colors */
    [data-testid="stMetricDelta"] svg {{
        display: none;
    }}

    [data-testid="stMetricDelta"][data-testid="stMetricDelta"] > div {{
        font-weight: 500;
    }}

    /* Buttons */
    .stButton > button {{
        background: {COLORS['accent']} !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.6rem 1.2rem !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
        text-transform: none !important;
    }}

    .stButton > button:hover {{
        background: {COLORS['accent_light']} !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(255, 87, 51, 0.3) !important;
    }}

    /* Secondary buttons */
    .stButton > button[kind="secondary"] {{
        background: transparent !important;
        border: 1px solid {COLORS['border_light']} !important;
        color: {COLORS['text_primary']} !important;
    }}

    .stButton > button[kind="secondary"]:hover {{
        background: {COLORS['bg_card']} !important;
        border-color: {COLORS['accent']} !important;
    }}

    /* DataFrames */
    .stDataFrame {{
        border: 1px solid {COLORS['border']} !important;
        border-radius: 12px !important;
        overflow: hidden;
    }}

    .stDataFrame [data-testid="stDataFrameResizable"] {{
        background: {COLORS['bg_card']} !important;
    }}

    /* Tables */
    .stDataFrame table {{
        background: {COLORS['bg_card']} !important;
    }}

    .stDataFrame th {{
        background: {COLORS['bg_secondary']} !important;
        color: {COLORS['text_secondary']} !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        font-size: 0.75rem !important;
        letter-spacing: 0.05em;
        padding: 1rem !important;
        border-bottom: 1px solid {COLORS['border']} !important;
    }}

    .stDataFrame td {{
        color: {COLORS['text_primary']} !important;
        padding: 0.875rem 1rem !important;
        border-bottom: 1px solid {COLORS['border']} !important;
    }}

    .stDataFrame tr:hover td {{
        background: {COLORS['bg_card_hover']} !important;
    }}

    /* Expanders */
    .streamlit-expanderHeader {{
        background: {COLORS['bg_card']} !important;
        border: 1px solid {COLORS['border']} !important;
        border-radius: 8px !important;
        color: {COLORS['text_primary']} !important;
        font-weight: 500 !important;
    }}

    .streamlit-expanderHeader:hover {{
        background: {COLORS['bg_card_hover']} !important;
        border-color: {COLORS['border_light']} !important;
    }}

    .streamlit-expanderContent {{
        background: {COLORS['bg_card']} !important;
        border: 1px solid {COLORS['border']} !important;
        border-top: none !important;
        border-radius: 0 0 8px 8px !important;
    }}

    /* Info/Warning/Success/Error boxes */
    .stAlert {{
        background: {COLORS['bg_card']} !important;
        border: 1px solid {COLORS['border']} !important;
        border-radius: 8px !important;
        color: {COLORS['text_primary']} !important;
    }}

    [data-testid="stAlertContentInfo"] {{
        background: rgba(52, 152, 219, 0.1) !important;
        border-left: 4px solid #3498db !important;
    }}

    [data-testid="stAlertContentWarning"] {{
        background: {COLORS['danger_bg']} !important;
        border-left: 4px solid {COLORS['warning']} !important;
    }}

    [data-testid="stAlertContentSuccess"] {{
        background: {COLORS['success_bg']} !important;
        border-left: 4px solid {COLORS['success']} !important;
    }}

    /* Select boxes and inputs */
    .stSelectbox > div > div {{
        background: {COLORS['bg_card']} !important;
        border: 1px solid {COLORS['border']} !important;
        border-radius: 8px !important;
        color: {COLORS['text_primary']} !important;
    }}

    .stTextInput > div > div > input {{
        background: {COLORS['bg_card']} !important;
        border: 1px solid {COLORS['border']} !important;
        border-radius: 8px !important;
        color: {COLORS['text_primary']} !important;
    }}

    .stTextInput > div > div > input:focus {{
        border-color: {COLORS['accent']} !important;
        box-shadow: 0 0 0 2px rgba(255, 87, 51, 0.2) !important;
    }}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        background: transparent;
        gap: 0.5rem;
    }}

    .stTabs [data-baseweb="tab"] {{
        background: {COLORS['bg_card']} !important;
        border: 1px solid {COLORS['border']} !important;
        border-radius: 8px !important;
        color: {COLORS['text_secondary']} !important;
        padding: 0.75rem 1.5rem !important;
        font-weight: 500 !important;
    }}

    .stTabs [data-baseweb="tab"]:hover {{
        background: {COLORS['bg_card_hover']} !important;
        color: {COLORS['text_primary']} !important;
    }}

    .stTabs [aria-selected="true"] {{
        background: {COLORS['accent']} !important;
        border-color: {COLORS['accent']} !important;
        color: white !important;
    }}

    /* Dividers */
    hr {{
        border: none;
        border-top: 1px solid {COLORS['border']};
        margin: 2rem 0;
    }}

    /* Scrollbar */
    ::-webkit-scrollbar {{
        width: 8px;
        height: 8px;
    }}

    ::-webkit-scrollbar-track {{
        background: {COLORS['bg_secondary']};
    }}

    ::-webkit-scrollbar-thumb {{
        background: {COLORS['border_light']};
        border-radius: 4px;
    }}

    ::-webkit-scrollbar-thumb:hover {{
        background: {COLORS['text_muted']};
    }}

    /* Caption text */
    .stCaption {{
        color: {COLORS['text_muted']} !important;
    }}

    /* Markdown text */
    .stMarkdown {{
        color: {COLORS['text_secondary']};
    }}

    .stMarkdown strong {{
        color: {COLORS['text_primary']};
    }}

    /* Custom classes for gain/loss colors */
    .gain-positive {{
        color: {COLORS['success']} !important;
        font-weight: 500;
    }}

    .gain-negative {{
        color: {COLORS['danger']} !important;
        font-weight: 500;
    }}

    /* Spinner */
    .stSpinner > div {{
        border-top-color: {COLORS['accent']} !important;
    }}

    /* File uploader */
    [data-testid="stFileUploader"] {{
        background: {COLORS['bg_card']} !important;
        border: 2px dashed {COLORS['border']} !important;
        border-radius: 12px !important;
        padding: 2rem !important;
    }}

    [data-testid="stFileUploader"]:hover {{
        border-color: {COLORS['accent']} !important;
    }}

    /* Progress bar */
    .stProgress > div > div {{
        background: {COLORS['accent']} !important;
    }}

    /* Sidebar nav items */
    [data-testid="stSidebarNav"] a {{
        color: {COLORS['text_secondary']} !important;
        padding: 0.75rem 1rem !important;
        border-radius: 8px !important;
        transition: all 0.2s ease !important;
    }}

    [data-testid="stSidebarNav"] a:hover {{
        background: {COLORS['bg_card']} !important;
        color: {COLORS['text_primary']} !important;
    }}

    [data-testid="stSidebarNav"] a[aria-selected="true"] {{
        background: {COLORS['bg_card']} !important;
        color: {COLORS['accent']} !important;
        border-left: 3px solid {COLORS['accent']} !important;
    }}
"""


def format_gain_display(value: float, percentage: float) -> str:
    """Format gain/loss for display with color indicator."""
    sign = "+" if value >= 0 else ""
    return f"{sign}{format_currency(value)} ({sign}{percentage:.1f}%)"


def main():
    """Main dashboard page."""

    # Sidebar
    with st.sidebar:
        st.markdown(f"""
        <div style="padding: 1rem 0;">
            <h2 style="color: {COLORS['text_primary']}; font-size: 1.25rem; font-weight: 600; margin: 0;">
                📊 Investment Register
            </h2>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")

        # Refresh data button
        if st.button("🔄 Refresh Prices", use_container_width=True):
            with st.spinner("Updating market prices..."):
                session = get_session()
                result = update_market_prices(session)
                session.close()
                st.success(f"Updated {result['updated']} of {result['total']} positions")
                if result['errors']:
                    st.warning(f"{len(result['errors'])} errors occurred")

        st.markdown("---")

        # Market Data Section
        st.markdown(f"""
        <p style="color: {COLORS['text_muted']}; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem;">Exchange Rates</p>
        """, unsafe_allow_html=True)

        # FX Rates
        usd_cad = get_usd_cad_rate()
        eur_cad = get_fx_rate('EUR', 'CAD')
        gbp_cad = get_fx_rate('GBP', 'CAD')

        st.metric("USD/CAD", f"{usd_cad:.4f}" if usd_cad else "N/A")
        st.metric("EUR/CAD", f"{eur_cad:.4f}" if eur_cad else "N/A")
        st.metric("GBP/CAD", f"{gbp_cad:.4f}" if gbp_cad else "N/A")

        st.markdown("---")

        # Major Indices
        st.markdown(f"""
        <p style="color: {COLORS['text_muted']}; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.5rem;">Major Indices</p>
        """, unsafe_allow_html=True)

        # Fetch index data
        indices = {
            'S&P 500': '^GSPC',
            'NASDAQ': '^IXIC',
            'TSX': '^GSPTSE',
            'DOW': '^DJI'
        }

        for name, symbol in indices.items():
            try:
                data = get_stock_price(symbol)
                if data and data.get('price'):
                    price = data['price']
                    change = data.get('change', 0)
                    change_pct = data.get('change_pct', 0)
                    if change and change != 0:
                        delta_str = f"{change:+,.2f} ({change_pct:+.2f}%)"
                    else:
                        delta_str = None
                    st.metric(
                        name,
                        f"{price:,.2f}",
                        delta=delta_str,
                        delta_color="normal"
                    )
            except:
                pass

        st.markdown("---")

        # Last update
        st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # Main content
    st.markdown(f"""
    <h1 style="font-size: 2rem; margin-bottom: 0.5rem;">Portfolio Dashboard</h1>
    <p style="color: {COLORS['text_muted']}; margin-bottom: 2rem;">Real-time overview of your investment portfolio</p>
    """, unsafe_allow_html=True)

    # Get portfolio data
    session = get_session()

    try:
        portfolio = get_portfolio_overview(session)
        summary = portfolio['summary']

        # Check if we have data
        if summary['investment_count'] == 0:
            st.info("👋 Welcome to your Investment Register!")
            st.markdown("""
            ### Getting Started

            You don't have any investments tracked yet. Here's how to get started:

            1. **Import Data** - Go to the **Settings** page to import your investments from CSV/Excel
            2. **Add Manually** - Or add investments one by one through the Holdings page
            3. **Connect APIs** - Set up your Anthropic API key for AI-powered recommendations

            #### Sample Import Template

            Your CSV should have columns like:
            - `name` - Investment name (required)
            - `symbol` - Ticker symbol (for public equities)
            - `asset_class` - Type of investment
            - `entity` - HoldCo or Personal
            - `quantity` - Number of units
            - `cost_basis` - Total cost
            - `current_value` - Current market value
            """)

            # Show sample data structure
            sample_data = pd.DataFrame({
                'name': ['Apple Inc.', 'Private Co.', 'Gold Bullion'],
                'symbol': ['AAPL', '', 'GOLD'],
                'asset_class': ['Public Equities', 'Private Business', 'Gold'],
                'entity': ['HoldCo', 'HoldCo', 'Personal'],
                'quantity': [100, 1, 10],
                'cost_basis': [15000, 50000, 20000],
                'current_value': [17500, 75000, 22000]
            })
            st.dataframe(sample_data, use_container_width=True)

            session.close()
            return

        # Top metrics row
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Total Portfolio Value",
                format_currency(summary['total_value_cad']),
                delta=format_currency(summary['total_gain']),
                delta_color="normal"
            )

        with col2:
            st.metric(
                "Total Cost Basis",
                format_currency(summary['total_cost_basis_cad'])
            )

        with col3:
            delta_color = "normal" if summary['total_gain'] >= 0 else "inverse"
            st.metric(
                "Unrealized Gain/Loss",
                format_percentage(summary['total_gain_pct']),
                delta=format_currency(summary['total_gain']),
                delta_color=delta_color
            )

        with col4:
            st.metric(
                "Positions",
                summary['investment_count']
            )

        st.markdown("---")

        # Charts row
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"<h3 style='color: {COLORS['text_primary']}; font-size: 1.1rem; font-weight: 500;'>Allocation by Asset Class</h3>", unsafe_allow_html=True)

            # Prepare data for pie chart
            asset_class_data = []
            for ac, data in portfolio['by_asset_class'].items():
                asset_class_data.append({
                    'Asset Class': ac,
                    'Value': data['value'],
                    'Weight': data['weight']
                })

            if asset_class_data:
                df_ac = pd.DataFrame(asset_class_data)
                fig = px.pie(
                    df_ac,
                    values='Value',
                    names='Asset Class',
                    hole=0.5,
                    color_discrete_sequence=COLORS['chart_colors']
                )
                fig.update_traces(
                    textposition='inside',
                    textinfo='percent',
                    textfont=dict(color='white', size=12),
                    marker=dict(line=dict(color=COLORS['bg_primary'], width=2))
                )
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color=COLORS['text_secondary'], family='Inter, sans-serif'),
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.3,
                        bgcolor='rgba(0,0,0,0)',
                        font=dict(color=COLORS['text_secondary'], size=11)
                    ),
                    margin=dict(t=20, b=60, l=20, r=20),
                    height=350
                )
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown(f"<h3 style='color: {COLORS['text_primary']}; font-size: 1.1rem; font-weight: 500;'>Allocation by Entity</h3>", unsafe_allow_html=True)

            entity_data = []
            for entity, data in portfolio['by_entity'].items():
                entity_data.append({
                    'Entity': entity,
                    'Value': data['value'],
                    'Weight': data['weight']
                })

            if entity_data:
                df_entity = pd.DataFrame(entity_data)
                fig = px.pie(
                    df_entity,
                    values='Value',
                    names='Entity',
                    hole=0.5,
                    color_discrete_sequence=[COLORS['accent'], '#3498db', '#2ecc71']
                )
                fig.update_traces(
                    textposition='inside',
                    textinfo='percent',
                    textfont=dict(color='white', size=12),
                    marker=dict(line=dict(color=COLORS['bg_primary'], width=2))
                )
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color=COLORS['text_secondary'], family='Inter, sans-serif'),
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.3,
                        bgcolor='rgba(0,0,0,0)',
                        font=dict(color=COLORS['text_secondary'], size=11)
                    ),
                    margin=dict(t=20, b=60, l=20, r=20),
                    height=350
                )
                st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")

        # Holdings summary
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown(f"<h3 style='color: {COLORS['text_primary']}; font-size: 1.1rem; font-weight: 500;'>Top Holdings</h3>", unsafe_allow_html=True)

            holdings = portfolio['holdings']
            top_holdings = sorted(holdings, key=lambda x: x['current_value'], reverse=True)[:10]

            # Create bar chart
            if top_holdings:
                df_holdings = pd.DataFrame(top_holdings)
                df_holdings['Gain/Loss'] = df_holdings['unrealized_gain']

                fig = go.Figure()

                fig.add_trace(go.Bar(
                    y=df_holdings['name'],
                    x=df_holdings['current_value'],
                    orientation='h',
                    name='Current Value',
                    marker=dict(
                        color=COLORS['accent'],
                        line=dict(width=0)
                    ),
                    text=[format_currency(v) for v in df_holdings['current_value']],
                    textposition='inside',
                    textfont=dict(color='white', size=11),
                    hovertemplate='<b>%{y}</b><br>Value: %{text}<extra></extra>'
                ))

                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color=COLORS['text_secondary'], family='Inter, sans-serif'),
                    showlegend=False,
                    xaxis_title="",
                    yaxis=dict(
                        autorange="reversed",
                        tickfont=dict(color=COLORS['text_secondary'], size=11),
                        gridcolor=COLORS['border'],
                        linecolor=COLORS['border']
                    ),
                    xaxis=dict(
                        showgrid=True,
                        gridcolor=COLORS['border'],
                        linecolor=COLORS['border'],
                        tickfont=dict(color=COLORS['text_muted'])
                    ),
                    height=400,
                    margin=dict(l=20, r=20, t=20, b=40),
                    bargap=0.3
                )

                st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown(f"<h3 style='color: {COLORS['text_primary']}; font-size: 1.1rem; font-weight: 500;'>Risk Summary</h3>", unsafe_allow_html=True)

            # Concentration risk
            concentration = portfolio['risk']['concentration']
            if concentration.get('concentrated_positions'):
                st.warning(f"⚠️ {len(concentration['concentrated_positions'])} concentrated position(s)")
                for pos in concentration['concentrated_positions']:
                    st.markdown(f"- **{pos['name']}**: {pos['weight']:.1f}%")
            else:
                st.success("✅ No concentration concerns")

            st.markdown("<br>", unsafe_allow_html=True)

            # Liquidity
            liquidity = portfolio['risk']['liquidity']
            st.metric("Liquid Assets", f"{liquidity['liquid_pct']:.1f}%")
            st.metric("Illiquid Assets", f"{liquidity['illiquid_pct']:.1f}%")

            # HHI
            hhi = concentration.get('hhi', 0)
            hhi_status = "Highly concentrated" if hhi > 2500 else ("Moderately concentrated" if hhi > 1500 else "Diversified")
            st.caption(f"HHI Index: {hhi:.0f} ({hhi_status})")

        st.markdown("---")

        # Recent activity
        st.markdown(f"<h3 style='color: {COLORS['text_primary']}; font-size: 1.1rem; font-weight: 500;'>Recent Activity</h3>", unsafe_allow_html=True)

        activity = get_recent_activity(session, limit=5)

        if activity:
            for item in activity:
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.markdown(f"**{item['investment']}**")
                with col2:
                    st.markdown(f"{item['type']}")
                with col3:
                    st.markdown(f"{format_currency(item['amount'], item['currency'])} - {item['date']}")
        else:
            st.info("No recent transactions recorded.")

        # Holdings table
        st.markdown("---")
        st.markdown(f"<h3 style='color: {COLORS['text_primary']}; font-size: 1.1rem; font-weight: 500;'>All Holdings</h3>", unsafe_allow_html=True)

        # Create holdings dataframe
        holdings_df = pd.DataFrame(portfolio['holdings'])

        if not holdings_df.empty:
            # Format for display
            display_df = holdings_df[[
                'name', 'asset_class', 'entity', 'quantity',
                'cost_basis', 'current_value', 'unrealized_gain', 'unrealized_gain_pct', 'weight'
            ]].copy()

            display_df.columns = [
                'Investment', 'Asset Class', 'Entity', 'Quantity',
                'Cost Basis', 'Current Value', 'Gain/Loss ($)', 'Gain/Loss (%)', 'Weight (%)'
            ]

            # Format numbers
            display_df['Cost Basis'] = display_df['Cost Basis'].apply(lambda x: f"${x:,.2f}")
            display_df['Current Value'] = display_df['Current Value'].apply(lambda x: f"${x:,.2f}")
            display_df['Gain/Loss ($)'] = display_df['Gain/Loss ($)'].apply(
                lambda x: f"+${x:,.2f}" if x >= 0 else f"-${abs(x):,.2f}"
            )
            display_df['Gain/Loss (%)'] = display_df['Gain/Loss (%)'].apply(
                lambda x: f"+{x:.1f}%" if x >= 0 else f"{x:.1f}%"
            )
            display_df['Weight (%)'] = display_df['Weight (%)'].apply(lambda x: f"{x:.1f}%")
            display_df['Quantity'] = display_df['Quantity'].apply(
                lambda x: f"{x:,.2f}" if x != int(x) else f"{int(x):,}"
            )

            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )

    finally:
        session.close()


if __name__ == "__main__":
    main()
