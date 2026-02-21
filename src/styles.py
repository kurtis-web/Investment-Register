"""
Shared styles and theme configuration for the Investment Register.
Import this module in all pages to maintain consistent dark theme styling.
"""

import streamlit as st

# Dark theme color palette
COLORS = {
    'bg_primary': '#000000',
    'bg_secondary': '#0a0a0a',
    'bg_card': '#111111',
    'bg_card_hover': '#1a1a1a',
    'border': '#1f1f1f',
    'border_light': '#2a2a2a',
    'text_primary': '#ffffff',
    'text_secondary': '#a0a0a0',
    'text_muted': '#666666',
    'accent': '#ff5733',
    'accent_light': '#ff6b47',
    'accent_gradient': 'linear-gradient(135deg, #ff5733 0%, #ff8c66 100%)',
    'success': '#00d26a',
    'success_bg': 'rgba(0, 210, 106, 0.1)',
    'danger': '#ff4757',
    'danger_bg': 'rgba(255, 71, 87, 0.1)',
    'warning': '#ffa502',
    'chart_colors': ['#ff5733', '#3498db', '#2ecc71', '#9b59b6', '#f39c12', '#1abc9c', '#e74c3c', '#00d2d3', '#ff6b81']
}

# Dark theme base settings for Plotly charts
# Note: Don't use **PLOTLY_LAYOUT with additional legend/xaxis/yaxis params - use apply_plotly_theme() instead
PLOTLY_LAYOUT = {
    'paper_bgcolor': 'rgba(0,0,0,0)',
    'plot_bgcolor': 'rgba(0,0,0,0)',
    'font': {'color': COLORS['text_secondary'], 'family': 'Inter, sans-serif'},
}


def apply_plotly_theme(fig, show_legend=True, height=400):
    """Apply dark theme to a Plotly figure safely."""
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=COLORS['text_secondary'], family='Inter, sans-serif'),
        showlegend=show_legend,
        legend=dict(
            bgcolor='rgba(0,0,0,0)',
            font=dict(color=COLORS['text_secondary'])
        ),
        xaxis=dict(
            gridcolor=COLORS['border'],
            linecolor=COLORS['border'],
            tickfont=dict(color=COLORS['text_muted'])
        ),
        yaxis=dict(
            gridcolor=COLORS['border'],
            linecolor=COLORS['border'],
            tickfont=dict(color=COLORS['text_muted'])
        ),
        height=height
    )
    return fig


def apply_dark_theme():
    """Apply the dark theme CSS to the Streamlit app."""
    st.markdown(f"""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

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

    /* DataFrames */
    .stDataFrame {{
        border: 1px solid {COLORS['border']} !important;
        border-radius: 12px !important;
        overflow: hidden;
    }}

    .stDataFrame [data-testid="stDataFrameResizable"] {{
        background: {COLORS['bg_card']} !important;
    }}

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

    /* Sidebar nav - consistent spacing and no animations */
    [data-testid="stSidebarNav"] {{
        padding-bottom: 0.5rem !important;
    }}

    [data-testid="stSidebarNav"] ul {{
        gap: 0 !important;
        padding: 0 !important;
    }}

    [data-testid="stSidebarNav"] li {{
        margin: 0 !important;
        padding: 0 !important;
    }}

    [data-testid="stSidebarNav"] a {{
        color: {COLORS['text_secondary']} !important;
        padding: 0.4rem 0.75rem !important;
        border-radius: 6px !important;
        transition: none !important;
        margin: 0 !important;
        min-height: unset !important;
        line-height: 1.4 !important;
    }}

    [data-testid="stSidebarNav"] a span {{
        transition: none !important;
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

    /* Number inputs */
    .stNumberInput > div > div > input {{
        background: {COLORS['bg_card']} !important;
        border: 1px solid {COLORS['border']} !important;
        border-radius: 8px !important;
        color: {COLORS['text_primary']} !important;
    }}

    /* Text area */
    .stTextArea > div > div > textarea {{
        background: {COLORS['bg_card']} !important;
        border: 1px solid {COLORS['border']} !important;
        border-radius: 8px !important;
        color: {COLORS['text_primary']} !important;
    }}

    /* Slider */
    .stSlider > div > div > div {{
        background: {COLORS['border']} !important;
    }}

    .stSlider > div > div > div > div {{
        background: {COLORS['accent']} !important;
    }}

    /* Form */
    [data-testid="stForm"] {{
        background: {COLORS['bg_card']} !important;
        border: 1px solid {COLORS['border']} !important;
        border-radius: 12px !important;
        padding: 1.5rem !important;
    }}

    /* Download button */
    .stDownloadButton > button {{
        background: {COLORS['bg_card']} !important;
        border: 1px solid {COLORS['border']} !important;
        color: {COLORS['text_primary']} !important;
    }}

    .stDownloadButton > button:hover {{
        background: {COLORS['bg_card_hover']} !important;
        border-color: {COLORS['accent']} !important;
    }}
</style>
""", unsafe_allow_html=True)


def page_header(title: str, subtitle: str = None):
    """Render a styled page header."""
    html = f'<h1 style="font-size: 2rem; margin-bottom: 0.5rem;">{title}</h1>'
    if subtitle:
        html += f'<p style="color: {COLORS["text_muted"]}; margin-bottom: 2rem;">{subtitle}</p>'
    st.markdown(html, unsafe_allow_html=True)


def section_header(title: str):
    """Render a styled section header."""
    st.markdown(
        f"<h3 style='color: {COLORS['text_primary']}; font-size: 1.1rem; font-weight: 500;'>{title}</h3>",
        unsafe_allow_html=True
    )
