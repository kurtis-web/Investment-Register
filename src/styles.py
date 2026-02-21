"""
Shared styles and theme configuration for the Investment Register.
Import this module in all pages to maintain consistent styling.
"""

import streamlit as st

# Light theme color palette — Slite-inspired
COLORS = {
    'bg_primary': '#FAFAF8',
    'bg_secondary': '#F4F3EF',
    'bg_card': '#FFFFFF',
    'bg_card_hover': '#F9F8F6',
    'border': '#E8E6E1',
    'border_light': '#EEECE7',
    'text_primary': '#1A1A1A',
    'text_secondary': '#4A4A4A',
    'text_muted': '#8C8C88',
    'accent': '#4F46E5',
    'accent_light': '#6366F1',
    'accent_gradient': 'linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)',
    'success': '#16A34A',
    'success_bg': 'rgba(22, 163, 74, 0.08)',
    'danger': '#DC2626',
    'danger_bg': 'rgba(220, 38, 38, 0.08)',
    'warning': '#D97706',
    'chart_colors': ['#4F46E5', '#0EA5E9', '#16A34A', '#8B5CF6', '#F59E0B', '#14B8A6', '#EC4899', '#06B6D4', '#F97316']
}

# Base settings for Plotly charts
# Note: Don't use **PLOTLY_LAYOUT with additional legend/xaxis/yaxis params - use apply_plotly_theme() instead
PLOTLY_LAYOUT = {
    'paper_bgcolor': 'rgba(0,0,0,0)',
    'plot_bgcolor': 'rgba(0,0,0,0)',
    'font': {'color': COLORS['text_secondary'], 'family': 'Inter, sans-serif'},
}


def apply_plotly_theme(fig, show_legend=True, height=400):
    """Apply light theme to a Plotly figure."""
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
            gridcolor='#EEECE7',
            linecolor='#E8E6E1',
            tickfont=dict(color=COLORS['text_muted']),
            gridwidth=1,
        ),
        yaxis=dict(
            gridcolor='#EEECE7',
            linecolor='#E8E6E1',
            tickfont=dict(color=COLORS['text_muted']),
            gridwidth=1,
        ),
        height=height
    )
    return fig


def apply_theme():
    """Apply the light theme CSS to the Streamlit app."""
    st.markdown(f"""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global Styles */
    .stApp {{
        background: {COLORS['bg_primary']};
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
    }}

    /* Main content area */
    .main .block-container {{
        padding: 3rem 2.5rem;
        max-width: 1280px;
        margin: 0 auto;
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
        font-weight: 700 !important;
        letter-spacing: -0.03em;
        line-height: 1.2 !important;
        margin-bottom: 1.5rem !important;
    }}

    h2 {{
        color: {COLORS['text_primary']} !important;
        font-weight: 600 !important;
        letter-spacing: -0.02em;
    }}

    h3 {{
        color: {COLORS['text_primary']} !important;
        font-weight: 600 !important;
        letter-spacing: -0.01em;
    }}

    /* Metric cards */
    [data-testid="stMetric"] {{
        background: {COLORS['bg_card']};
        border: 1px solid {COLORS['border']};
        border-radius: 16px;
        padding: 1.5rem;
        transition: all 0.2s cubic-bezier(.215,.61,.355,1);
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    }}

    [data-testid="stMetric"]:hover {{
        background: {COLORS['bg_card']};
        border-color: {COLORS['border']};
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.06);
    }}

    [data-testid="stMetric"] label {{
        color: {COLORS['text_muted']} !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }}

    [data-testid="stMetric"] [data-testid="stMetricValue"] {{
        color: {COLORS['text_primary']} !important;
        font-size: 1.75rem !important;
        font-weight: 700 !important;
    }}

    [data-testid="stMetric"] [data-testid="stMetricDelta"] {{
        font-weight: 500 !important;
    }}

    /* Buttons */
    .stButton > button {{
        background: {COLORS['accent']} !important;
        color: white !important;
        border: none !important;
        border-radius: 42px !important;
        padding: 0.6rem 1.5rem !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        transition: all 0.2s cubic-bezier(.215,.61,.355,1) !important;
        box-shadow: 0 1px 2px rgba(79, 70, 229, 0.15) !important;
        text-transform: none !important;
    }}

    .stButton > button:hover {{
        background: {COLORS['accent_light']} !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.25) !important;
    }}

    /* DataFrames */
    .stDataFrame {{
        border: 1px solid {COLORS['border']} !important;
        border-radius: 16px !important;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    }}

    .stDataFrame [data-testid="stDataFrameResizable"] {{
        background: {COLORS['bg_card']} !important;
    }}

    .stDataFrame table {{
        background: {COLORS['bg_card']} !important;
    }}

    .stDataFrame th {{
        background: {COLORS['bg_secondary']} !important;
        color: {COLORS['text_muted']} !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        font-size: 0.7rem !important;
        letter-spacing: 0.06em;
        padding: 1rem !important;
        border-bottom: 1px solid {COLORS['border']} !important;
    }}

    .stDataFrame td {{
        color: {COLORS['text_primary']} !important;
        padding: 0.875rem 1rem !important;
        border-bottom: 1px solid {COLORS['border_light']} !important;
    }}

    .stDataFrame tr:hover td {{
        background: {COLORS['bg_primary']} !important;
    }}

    /* Expanders */
    .streamlit-expanderHeader {{
        background: {COLORS['bg_card']} !important;
        border: 1px solid {COLORS['border']} !important;
        border-radius: 12px !important;
        color: {COLORS['text_primary']} !important;
        font-weight: 500 !important;
        transition: all 0.2s cubic-bezier(.215,.61,.355,1);
    }}

    .streamlit-expanderHeader:hover {{
        background: {COLORS['bg_card_hover']} !important;
        border-color: {COLORS['border']} !important;
    }}

    .streamlit-expanderContent {{
        background: {COLORS['bg_card']} !important;
        border: 1px solid {COLORS['border']} !important;
        border-top: none !important;
        border-radius: 0 0 12px 12px !important;
    }}

    /* Info/Warning/Success/Error boxes */
    .stAlert {{
        background: {COLORS['bg_card']} !important;
        border: 1px solid {COLORS['border']} !important;
        border-radius: 12px !important;
        color: {COLORS['text_primary']} !important;
    }}

    /* Select boxes and inputs */
    .stSelectbox > div > div {{
        background: {COLORS['bg_card']} !important;
        border: 1px solid {COLORS['border']} !important;
        border-radius: 10px !important;
        color: {COLORS['text_primary']} !important;
        transition: border-color 0.2s cubic-bezier(.215,.61,.355,1);
    }}

    .stTextInput > div > div > input {{
        background: {COLORS['bg_card']} !important;
        border: 1px solid {COLORS['border']} !important;
        border-radius: 10px !important;
        color: {COLORS['text_primary']} !important;
    }}

    .stTextInput > div > div > input:focus {{
        border-color: {COLORS['accent']} !important;
        box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.12) !important;
    }}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        background: transparent;
        gap: 0.25rem;
        border-bottom: 1px solid {COLORS['border']};
    }}

    .stTabs [data-baseweb="tab"] {{
        background: transparent !important;
        border: none !important;
        border-radius: 0 !important;
        color: {COLORS['text_muted']} !important;
        padding: 0.75rem 1.25rem !important;
        font-weight: 500 !important;
        border-bottom: 2px solid transparent !important;
        transition: all 0.2s cubic-bezier(.215,.61,.355,1);
    }}

    .stTabs [data-baseweb="tab"]:hover {{
        background: transparent !important;
        color: {COLORS['text_primary']} !important;
    }}

    .stTabs [aria-selected="true"] {{
        background: transparent !important;
        color: {COLORS['accent']} !important;
        border-bottom: 2px solid {COLORS['accent']} !important;
        font-weight: 600 !important;
    }}

    /* Dividers */
    hr {{
        border: none;
        border-top: 1px solid {COLORS['border']};
        margin: 2rem 0;
    }}

    /* Scrollbar */
    ::-webkit-scrollbar {{
        width: 6px;
        height: 6px;
    }}

    ::-webkit-scrollbar-track {{
        background: {COLORS['bg_secondary']};
    }}

    ::-webkit-scrollbar-thumb {{
        background: #D4D2CD;
        border-radius: 3px;
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
        border-radius: 16px !important;
        padding: 2rem !important;
    }}

    [data-testid="stFileUploader"]:hover {{
        border-color: {COLORS['accent']} !important;
    }}

    /* Progress bar */
    .stProgress > div > div {{
        background: {COLORS['accent']} !important;
    }}

    /* Sidebar nav - consistent spacing */
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
        padding: 0.5rem 0.75rem !important;
        border-radius: 8px !important;
        transition: all 0.15s cubic-bezier(.215,.61,.355,1) !important;
        margin: 0 !important;
        min-height: unset !important;
        line-height: 1.4 !important;
    }}

    [data-testid="stSidebarNav"] a span {{
        transition: none !important;
    }}

    [data-testid="stSidebarNav"] a:hover {{
        background: rgba(79, 70, 229, 0.06) !important;
        color: {COLORS['text_primary']} !important;
    }}

    [data-testid="stSidebarNav"] a[aria-selected="true"] {{
        background: rgba(79, 70, 229, 0.08) !important;
        color: {COLORS['accent']} !important;
        border-left: 3px solid {COLORS['accent']} !important;
        font-weight: 500 !important;
    }}

    /* Number inputs */
    .stNumberInput > div > div > input {{
        background: {COLORS['bg_card']} !important;
        border: 1px solid {COLORS['border']} !important;
        border-radius: 10px !important;
        color: {COLORS['text_primary']} !important;
    }}

    /* Text area */
    .stTextArea > div > div > textarea {{
        background: {COLORS['bg_card']} !important;
        border: 1px solid {COLORS['border']} !important;
        border-radius: 10px !important;
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
        border-radius: 16px !important;
        padding: 1.5rem !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    }}

    /* Download button */
    .stDownloadButton > button {{
        background: {COLORS['bg_card']} !important;
        border: 1px solid {COLORS['border']} !important;
        color: {COLORS['text_primary']} !important;
        border-radius: 42px !important;
        transition: all 0.2s cubic-bezier(.215,.61,.355,1) !important;
    }}

    .stDownloadButton > button:hover {{
        background: {COLORS['bg_card_hover']} !important;
        border-color: {COLORS['accent']} !important;
        transform: translateY(-1px);
    }}
</style>
""", unsafe_allow_html=True)


# Backward compatibility alias
apply_dark_theme = apply_theme


def page_header(title: str, subtitle: str = None):
    """Render a styled page header."""
    html = f'<h1 style="font-size: 2.25rem; font-weight: 700; letter-spacing: -0.03em; margin-bottom: 0.5rem;">{title}</h1>'
    if subtitle:
        html += f'<p style="color: {COLORS["text_muted"]}; font-size: 1.05rem; margin-bottom: 2.5rem;">{subtitle}</p>'
    st.markdown(html, unsafe_allow_html=True)


def section_header(title: str):
    """Render a styled section header."""
    st.markdown(
        f"<h3 style='color: {COLORS['text_primary']}; font-size: 1.15rem; font-weight: 600; letter-spacing: -0.01em;'>{title}</h3>",
        unsafe_allow_html=True
    )
