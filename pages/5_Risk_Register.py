"""
Risk Register - Risk identification, assessment, and monitoring.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from collections import defaultdict
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database import (
    get_session, get_all_entities, get_all_investments,
    Risk, Entity, Investment,
    get_all_risks, add_risk, update_risk, delete_risk
)
from src.ai_advisor import (
    is_ai_available, get_risk_register_analysis, get_mitigation_suggestions
)
from src.portfolio import get_portfolio_overview
from src.styles import apply_dark_theme, COLORS, apply_plotly_theme, page_header, section_header

st.set_page_config(page_title="Risk Register | Investment Register", page_icon="\U0001f6e1\ufe0f", layout="wide", initial_sidebar_state="expanded")

apply_dark_theme()

from src.sidebar import render_sidebar
render_sidebar()

page_header("Risk Register", "Risk identification, assessment, and monitoring")

# --- Constants (fixed scales) ---

LIKELIHOOD_LABELS = {
    0: "0 - Not at all",
    1: "1 - Very unlikely",
    2: "2 - Unlikely",
    3: "3 - Reasonably likely",
    4: "4 - Very likely",
    5: "5 - Almost certain",
}

IMPACT_LABELS = {
    0: "0 - No impact",
    1: "1 - Very minor",
    2: "2 - Minor",
    3: "3 - Moderate",
    4: "4 - Significant",
    5: "5 - Extreme",
}

# --- Configurable dropdown options ---

_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "risk_config.json")

_DEFAULT_CONFIG = {
    "categories": [
        "Financial", "Operational", "Legal", "Reputational",
        "Strategic", "Compliance", "Personnel", "Cybersecurity", "Market"
    ],
    "statuses": [
        "Identified", "Assessed", "Mitigating", "Accepted", "Closed", "Monitoring"
    ],
    "owners": [],
    "review_frequencies": ["Monthly", "Quarterly", "Semi-annually", "Annually"],
}


def load_risk_config():
    """Load dropdown options from config file, falling back to defaults."""
    if os.path.exists(_CONFIG_PATH):
        try:
            with open(_CONFIG_PATH, 'r') as f:
                config = json.load(f)
            # Merge with defaults for any missing keys
            for key, default in _DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = default
            return config
        except (json.JSONDecodeError, IOError):
            pass
    return dict(_DEFAULT_CONFIG)


def save_risk_config(config):
    """Save dropdown options to config file."""
    with open(_CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=2)


risk_config = load_risk_config()
RISK_CATEGORIES = risk_config["categories"]
RISK_STATUSES = risk_config["statuses"]
RISK_OWNERS = risk_config["owners"]
REVIEW_FREQUENCIES = risk_config["review_frequencies"]


def score_color(score):
    """Return color based on risk score."""
    if score >= 15:
        return COLORS['danger']
    elif score >= 5:
        return COLORS['warning']
    return COLORS['success']


def score_label(score):
    """Return severity label for a risk score."""
    if score >= 15:
        return "Critical"
    elif score >= 5:
        return "Moderate"
    return "Low"


def _parse_scale(val):
    """Extract integer from a label like '3 - Reasonably likely' or return int directly."""
    if isinstance(val, (int, float)):
        return int(val)
    try:
        return int(str(val).split(" - ")[0])
    except (ValueError, IndexError):
        return 0


def _stoplight_scale(val):
    """Stoplight CSS for 0-5 scale values (dark theme optimized)."""
    n = _parse_scale(val)
    if n >= 4:
        return ('background-color: rgba(255, 71, 87, 0.25); '
                'color: #ff6b7a; font-weight: 600')
    elif n >= 2:
        return ('background-color: rgba(255, 165, 2, 0.20); '
                'color: #ffb830; font-weight: 600')
    return ('background-color: rgba(0, 210, 106, 0.20); '
            'color: #33e088; font-weight: 600')


def _stoplight_score(val):
    """Stoplight CSS for 0-25 score values (5-tier, dark theme optimized)."""
    n = int(val) if not pd.isna(val) else 0
    if n >= 20:
        return ('background-color: rgba(204, 0, 0, 0.35); '
                'color: #ff6b7a; font-weight: 700; font-size: 1.05em')
    elif n >= 15:
        return ('background-color: rgba(255, 71, 87, 0.28); '
                'color: #ff6b7a; font-weight: 700; font-size: 1.05em')
    elif n >= 10:
        return ('background-color: rgba(255, 140, 50, 0.25); '
                'color: #ffa05c; font-weight: 700; font-size: 1.05em')
    elif n >= 5:
        return ('background-color: rgba(255, 193, 7, 0.22); '
                'color: #ffcc33; font-weight: 600; font-size: 1.05em')
    return ('background-color: rgba(0, 210, 106, 0.18); '
            'color: #33e088; font-weight: 600; font-size: 1.05em')


def _format_scale_short(val):
    """Strip numeric prefix for cleaner display: '3 - Reasonably likely' -> 'Reasonably likely'."""
    if isinstance(val, str) and " - " in val:
        return val.split(" - ", 1)[1]
    return val


# --- Main Page ---

session = get_session()

try:
    # Load data
    risks = get_all_risks(session, include_closed=True)
    entities = get_all_entities(session)
    investments = get_all_investments(session, active_only=True)
    entity_map = {e.id: e.name for e in entities}
    investment_map = {i.id: i.name for i in investments}

    tab1, tab2, tab3, tab4 = st.tabs([
        "Risk List",
        "Risk Matrix",
        "Review Calendar",
        "AI Insights"
    ])

    # =========================================================================
    # TAB 1: RISK LIST
    # =========================================================================
    with tab1:
        # Summary metrics
        active_risks = [r for r in risks if r.status != 'Closed']
        critical = [r for r in active_risks if r.risk_score >= 15]
        moderate = [r for r in active_risks if 5 <= r.risk_score < 15]
        low = [r for r in active_risks if r.risk_score < 5]

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Active Risks", len(active_risks))
        with col2:
            st.metric("Critical (15+)", len(critical))
        with col3:
            st.metric("Moderate (5-14)", len(moderate))
        with col4:
            st.metric("Low (< 5)", len(low))

        st.markdown("---")

        # Filters
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            filter_entity = st.selectbox(
                "Entity",
                ["All"] + [e.name for e in entities],
                key="risk_filter_entity"
            )
        with col2:
            filter_category = st.selectbox(
                "Category",
                ["All"] + RISK_CATEGORIES,
                key="risk_filter_category"
            )
        with col3:
            filter_status = st.selectbox(
                "Status",
                ["All (Active)", "All (Including Closed)"] + RISK_STATUSES,
                key="risk_filter_status"
            )
        with col4:
            filter_severity = st.selectbox(
                "Severity",
                ["All", "Critical (15+)", "Moderate (5-14)", "Low (< 5)"],
                key="risk_filter_severity"
            )

        # Apply filters
        filtered_risks = list(risks)

        if filter_entity != "All":
            entity_obj = next((e for e in entities if e.name == filter_entity), None)
            if entity_obj:
                filtered_risks = [r for r in filtered_risks if r.entity_id == entity_obj.id]

        if filter_category != "All":
            filtered_risks = [r for r in filtered_risks if r.category == filter_category]

        if filter_status == "All (Active)":
            filtered_risks = [r for r in filtered_risks if r.status != 'Closed']
        elif filter_status != "All (Including Closed)":
            filtered_risks = [r for r in filtered_risks if r.status == filter_status]

        if filter_severity == "Critical (15+)":
            filtered_risks = [r for r in filtered_risks if r.risk_score >= 15]
        elif filter_severity == "Moderate (5-14)":
            filtered_risks = [r for r in filtered_risks if 5 <= r.risk_score < 15]
        elif filter_severity == "Low (< 5)":
            filtered_risks = [r for r in filtered_risks if r.risk_score < 5]

        # Sort by score descending
        filtered_risks.sort(key=lambda r: r.risk_score, reverse=True)

        # Build owner options: configured list + any existing owners from DB
        all_owners = list(RISK_OWNERS)
        for r in risks:
            if r.risk_owner and r.risk_owner not in all_owners:
                all_owners.append(r.risk_owner)

        # Risk table
        if filtered_risks:

            likelihood_options = [LIKELIHOOD_LABELS[i] for i in range(6)]
            impact_options = [IMPACT_LABELS[i] for i in range(6)]

            table_data = []
            for r in filtered_risks:
                table_data.append({
                    '_risk_id': r.id,
                    'Title': r.title,
                    'Category': r.category,
                    'Entity': entity_map.get(r.entity_id, ''),
                    'Owner': r.risk_owner or '',
                    'Likelihood': r.likelihood,
                    'Impact': r.impact,
                    'Score': r.risk_score,
                    'Status': r.status,
                    'Review': r.review_frequency or '',
                    'Next Review': r.next_review_date if r.next_review_date else None,
                    'Mitigation Plan': r.mitigation_plan or '',
                    'Mitigation Actions': r.mitigation_actions or '',
                    'Delete': False,
                })

            df = pd.DataFrame(table_data)

            # Store original for diff detection
            if 'risk_df_original' not in st.session_state or st.session_state.get('_risk_data_stale', True):
                st.session_state['risk_df_original'] = df.copy()
                st.session_state['_risk_data_stale'] = False

            entity_names = [e.name for e in entities]
            name_to_entity_id = {e.name: e.id for e in entities}

            # --- Auto-save: detect edit→view transition and persist changes ---
            prev_edit_mode = st.session_state.get('_prev_edit_mode', False)
            edit_mode = st.toggle("Edit Mode", value=False, key="risk_edit_mode")
            st.session_state['_prev_edit_mode'] = edit_mode

            if prev_edit_mode and not edit_mode:
                # Transitioning from Edit → View: auto-save pending edits
                editor_state = st.session_state.get('risk_editor', {})
                edited_rows = editor_state.get('edited_rows', {})
                original = st.session_state.get('risk_df_original')

                if edited_rows and original is not None:
                    changes_made = 0
                    for row_idx_str, changes in edited_rows.items():
                        row_idx = int(row_idx_str)
                        if row_idx >= len(original):
                            continue
                        risk_id = int(original.iloc[row_idx]['_risk_id'])
                        row_orig = original.iloc[row_idx]

                        # Merge changes onto original row
                        merged = dict(row_orig)
                        merged.update(changes)

                        entity_name = merged.get('Entity', '')
                        entity_id = name_to_entity_id.get(entity_name) if entity_name else None

                        update_risk(
                            session, risk_id,
                            title=merged['Title'],
                            category=merged['Category'],
                            entity_id=entity_id,
                            risk_owner=merged['Owner'] if merged.get('Owner') else None,
                            likelihood=_parse_scale(merged['Likelihood']),
                            impact=_parse_scale(merged['Impact']),
                            status=merged['Status'],
                            review_frequency=merged['Review'] if merged.get('Review') else None,
                            next_review_date=merged.get('Next Review'),
                            mitigation_plan=merged['Mitigation Plan'] if merged.get('Mitigation Plan') else None,
                            mitigation_actions=merged['Mitigation Actions'] if merged.get('Mitigation Actions') else None,
                        )
                        changes_made += 1

                    if changes_made > 0:
                        st.session_state['_risk_data_stale'] = True
                        st.toast(f"Auto-saved {changes_made} change(s).")
                        st.rerun()

            if edit_mode:
                # ---- EDIT MODE: st.data_editor with full editing ----
                # Create edit DataFrame with label strings for Likelihood/Impact
                edit_df = df.copy()
                edit_df['Likelihood'] = edit_df['Likelihood'].map(
                    lambda x: LIKELIHOOD_LABELS.get(x, f"{x}"))
                edit_df['Impact'] = edit_df['Impact'].map(
                    lambda x: IMPACT_LABELS.get(x, f"{x}"))

                edited_df = st.data_editor(
                    edit_df,
                    column_config={
                        '_risk_id': None,
                        'Title': st.column_config.TextColumn(
                            'Title',
                            width='medium',
                            required=True,
                        ),
                        'Category': st.column_config.SelectboxColumn(
                            'Category',
                            options=RISK_CATEGORIES,
                            required=True,
                        ),
                        'Entity': st.column_config.SelectboxColumn(
                            'Entity',
                            options=[''] + entity_names,
                        ),
                        'Owner': st.column_config.SelectboxColumn(
                            'Owner',
                            options=[''] + all_owners,
                            width='small',
                        ),
                        'Likelihood': st.column_config.SelectboxColumn(
                            'Likelihood',
                            options=likelihood_options,
                            required=True,
                        ),
                        'Impact': st.column_config.SelectboxColumn(
                            'Impact',
                            options=impact_options,
                            required=True,
                        ),
                        'Score': st.column_config.ProgressColumn(
                            'Score',
                            help='Auto-calculated on save (Likelihood x Impact)',
                            format='%d',
                            min_value=0,
                            max_value=25,
                        ),
                        'Status': st.column_config.SelectboxColumn(
                            'Status',
                            options=RISK_STATUSES,
                            required=True,
                        ),
                        'Review': st.column_config.SelectboxColumn(
                            'Review',
                            options=[''] + REVIEW_FREQUENCIES,
                        ),
                        'Next Review': st.column_config.DateColumn(
                            'Next Review',
                            format='YYYY-MM-DD',
                        ),
                        'Mitigation Plan': st.column_config.TextColumn(
                            'Mitigation Plan',
                            width='large',
                        ),
                        'Mitigation Actions': st.column_config.TextColumn(
                            'Mitigation Actions',
                            width='large',
                        ),
                        'Delete': st.column_config.CheckboxColumn(
                            'Delete',
                            help='Select rows to delete',
                            default=False,
                        ),
                    },
                    disabled=['Score'],
                    hide_index=True,
                    num_rows='fixed',
                    use_container_width=True,
                    key='risk_editor',
                )

                # Delete button
                col_delete, col_info = st.columns([1, 4])

                with col_delete:
                    delete_clicked = st.button("Delete Selected", key="delete_selected_risks")

                with col_info:
                    st.caption("Changes are saved automatically when you switch back to View Mode. Score is recalculated on save.")

                # Delete logic
                if delete_clicked:
                    rows_to_delete = edited_df[edited_df['Delete'] == True]
                    if rows_to_delete.empty:
                        st.warning("No rows selected for deletion.")
                    else:
                        count = len(rows_to_delete)
                        for _, row in rows_to_delete.iterrows():
                            risk_id = int(row['_risk_id'])
                            delete_risk(session, risk_id)
                        st.success(f"Deleted {count} risk(s).")
                        st.session_state['_risk_data_stale'] = True
                        st.rerun()

            else:
                # ---- VIEW MODE: styled table with stoplight colors ----
                # Convert Likelihood/Impact to labels for display
                display_df = df.drop(columns=['_risk_id', 'Delete']).copy()
                display_df['Likelihood'] = display_df['Likelihood'].map(
                    lambda x: LIKELIHOOD_LABELS.get(x, f"{x}"))
                display_df['Impact'] = display_df['Impact'].map(
                    lambda x: IMPACT_LABELS.get(x, f"{x}"))

                styled_df = (display_df.style
                    .map(_stoplight_scale, subset=['Likelihood', 'Impact'])
                    .map(_stoplight_score, subset=['Score'])
                    .format(_format_scale_short, subset=['Likelihood', 'Impact'])
                    .format('{:.0f}', subset=['Score'])
                    .set_properties(
                        subset=['Score', 'Likelihood', 'Impact', 'Status', 'Category'],
                        **{'text-align': 'center'}
                    )
                    .set_properties(
                        subset=['Title', 'Mitigation Plan', 'Mitigation Actions'],
                        **{'text-align': 'left'}
                    )
                )

                st.dataframe(
                    styled_df,
                    hide_index=True,
                    use_container_width=True,
                    column_config={
                        'Title': st.column_config.TextColumn('Title', width='medium'),
                        'Score': st.column_config.NumberColumn('Score', width='small'),
                        'Category': st.column_config.TextColumn('Category', width='small'),
                        'Status': st.column_config.TextColumn('Status', width='small'),
                        'Owner': st.column_config.TextColumn('Owner', width='small'),
                        'Mitigation Plan': st.column_config.TextColumn('Mitigation Plan', width='large'),
                        'Mitigation Actions': st.column_config.TextColumn('Mitigation Actions', width='large'),
                    },
                )

                # Delete risks
                risk_labels = {f"[{r.risk_score}] {r.title}": r.id for r in filtered_risks}
                selected_for_delete = st.multiselect(
                    "Select risks to delete",
                    options=list(risk_labels.keys()),
                    key="view_delete_select",
                )
                if selected_for_delete:
                    if st.button(f"Delete {len(selected_for_delete)} risk(s)", type="primary", key="view_delete_risks"):
                        for label in selected_for_delete:
                            delete_risk(session, risk_labels[label])
                        st.session_state['_risk_data_stale'] = True
                        st.success(f"Deleted {len(selected_for_delete)} risk(s).")
                        st.rerun()

        else:
            st.info("No risks match the current filters.")

        st.markdown("---")

        # Add New Risk
        with st.expander("Add New Risk"):
            with st.form("add_risk_form"):
                new_title = st.text_input("Title *")
                new_description = st.text_area("Description")

                col1, col2 = st.columns(2)
                with col1:
                    new_category = st.selectbox("Category *", RISK_CATEGORIES, key="new_category")
                    new_entity = st.selectbox(
                        "Entity",
                        ["None"] + [e.name for e in entities],
                        key="new_entity"
                    )
                    new_investment = st.selectbox(
                        "Linked Investment (optional)",
                        ["None"] + [f"{i.name} ({i.symbol})" if i.symbol else i.name for i in investments],
                        key="new_investment"
                    )
                with col2:
                    new_owner = st.selectbox("Risk Owner", [""] + all_owners, key="new_owner")
                    new_status = st.selectbox("Status", RISK_STATUSES, key="new_status")
                    new_review_freq = st.selectbox("Review Frequency", REVIEW_FREQUENCIES, key="new_review_freq")

                col1, col2, col3 = st.columns(3)
                with col1:
                    new_likelihood = st.selectbox(
                        "Likelihood *",
                        list(LIKELIHOOD_LABELS.keys()),
                        format_func=lambda x: LIKELIHOOD_LABELS[x],
                        key="new_likelihood"
                    )
                with col2:
                    new_impact = st.selectbox(
                        "Impact *",
                        list(IMPACT_LABELS.keys()),
                        format_func=lambda x: IMPACT_LABELS[x],
                        key="new_impact"
                    )
                with col3:
                    st.metric("Calculated Score", new_likelihood * new_impact)

                new_mitigation_plan = st.text_area("Mitigation Plan", key="new_mit_plan")
                new_mitigation_actions = st.text_area("Mitigation Actions", key="new_mit_actions")
                new_review_date = st.date_input("Next Review Date", value=date.today() + timedelta(days=90), key="new_review_date")

                if st.form_submit_button("Add Risk"):
                    if new_title:
                        entity_id = None
                        if new_entity != "None":
                            entity_obj = next((e for e in entities if e.name == new_entity), None)
                            if entity_obj:
                                entity_id = entity_obj.id

                        investment_id = None
                        if new_investment != "None":
                            inv_idx = [("None")] + [f"{i.name} ({i.symbol})" if i.symbol else i.name for i in investments]
                            inv_pos = inv_idx.index(new_investment) - 1 if new_investment in inv_idx else -1
                            if 0 <= inv_pos < len(investments):
                                investment_id = investments[inv_pos].id

                        add_risk(
                            session,
                            title=new_title,
                            description=new_description if new_description else None,
                            category=new_category,
                            entity_id=entity_id,
                            investment_id=investment_id,
                            risk_owner=new_owner if new_owner and new_owner != "" else None,
                            likelihood=new_likelihood,
                            impact=new_impact,
                            status=new_status,
                            mitigation_plan=new_mitigation_plan if new_mitigation_plan else None,
                            mitigation_actions=new_mitigation_actions if new_mitigation_actions else None,
                            review_frequency=new_review_freq,
                            next_review_date=new_review_date,
                        )
                        st.success(f"Added risk: {new_title}")
                        # Clear form fields
                        for key in ['new_category', 'new_entity', 'new_investment',
                                    'new_owner', 'new_status', 'new_review_freq',
                                    'new_likelihood', 'new_impact', 'new_mit_plan',
                                    'new_mit_actions', 'new_review_date']:
                            if key in st.session_state:
                                del st.session_state[key]
                        st.session_state['_risk_data_stale'] = True
                        st.rerun()
                    else:
                        st.error("Title is required.")

        # Manage dropdown options
        with st.expander("Manage Dropdown Options"):
            st.caption("Edit the options available in each dropdown. One item per line.")

            col1, col2 = st.columns(2)
            with col1:
                edit_categories = st.text_area(
                    "Categories",
                    value="\n".join(RISK_CATEGORIES),
                    height=200,
                    key="edit_categories"
                )
                edit_owners = st.text_area(
                    "Owners",
                    value="\n".join(RISK_OWNERS),
                    height=200,
                    key="edit_owners"
                )
            with col2:
                edit_statuses = st.text_area(
                    "Statuses",
                    value="\n".join(RISK_STATUSES),
                    height=200,
                    key="edit_statuses"
                )
                edit_frequencies = st.text_area(
                    "Review Frequencies",
                    value="\n".join(REVIEW_FREQUENCIES),
                    height=200,
                    key="edit_frequencies"
                )

            if st.button("Save Dropdown Options", type="primary", key="save_dropdown_options"):
                new_config = {
                    "categories": [x.strip() for x in edit_categories.strip().split("\n") if x.strip()],
                    "statuses": [x.strip() for x in edit_statuses.strip().split("\n") if x.strip()],
                    "owners": [x.strip() for x in edit_owners.strip().split("\n") if x.strip()],
                    "review_frequencies": [x.strip() for x in edit_frequencies.strip().split("\n") if x.strip()],
                }
                save_risk_config(new_config)
                st.success("Dropdown options saved. Reloading...")
                st.rerun()

    # =========================================================================
    # TAB 2: RISK MATRIX (5x5 Heatmap)
    # =========================================================================
    with tab2:
        section_header("Risk Matrix — Likelihood vs Impact")
        st.caption("Risks plotted by likelihood (X) and impact (Y). Cell shows count of risks.")

        active_risks = [r for r in risks if r.status != 'Closed']

        # Build 5x5 matrix (indices 0-4 map to scores 1-5)
        matrix = np.zeros((5, 5), dtype=int)
        risk_names_matrix = [["" for _ in range(5)] for _ in range(5)]

        for r in active_risks:
            if r.likelihood > 0 and r.impact > 0:
                li = r.likelihood - 1  # 0-indexed
                ii = r.impact - 1
                matrix[ii][li] += 1
                name = r.title[:25] + "..." if len(r.title) > 25 else r.title
                if risk_names_matrix[ii][li]:
                    risk_names_matrix[ii][li] += f"<br>{name}"
                else:
                    risk_names_matrix[ii][li] = name

        # Display text: count + truncated names
        display_text = [["" for _ in range(5)] for _ in range(5)]
        for i in range(5):
            for j in range(5):
                if matrix[i][j] > 0:
                    display_text[i][j] = str(matrix[i][j])

        # Background color based on inherent score (likelihood * impact)
        score_matrix = np.zeros((5, 5))
        for i in range(5):
            for j in range(5):
                score_matrix[i][j] = (j + 1) * (i + 1)

        x_labels = ["Very unlikely", "Unlikely", "Reasonably likely", "Very likely", "Almost certain"]
        y_labels = ["Very minor", "Minor", "Moderate", "Significant", "Extreme"]

        # Custom colorscale: green -> yellow -> orange -> red
        colorscale = [
            [0.0, '#00d26a'],
            [0.24, '#00d26a'],
            [0.25, '#7dbd3a'],
            [0.39, '#b8a620'],
            [0.40, '#ffa502'],
            [0.59, '#ff7b2a'],
            [0.60, '#ff5733'],
            [0.79, '#e83e3e'],
            [0.80, '#ff4757'],
            [1.0, '#cc0000'],
        ]

        fig = go.Figure(data=go.Heatmap(
            z=score_matrix,
            x=x_labels,
            y=y_labels,
            text=display_text,
            texttemplate="<b>%{text}</b>",
            textfont={"size": 18, "color": "white"},
            colorscale=colorscale,
            showscale=False,
            hovertext=[[risk_names_matrix[i][j] if risk_names_matrix[i][j] else "No risks"
                        for j in range(5)] for i in range(5)],
            hovertemplate="Likelihood: %{x}<br>Impact: %{y}<br>Score: %{z}<br>Risks:<br>%{hovertext}<extra></extra>",
        ))

        fig.update_layout(
            xaxis_title="Likelihood",
            yaxis_title="Impact",
            xaxis=dict(side="bottom"),
            yaxis=dict(autorange=True),
        )
        apply_plotly_theme(fig, show_legend=False, height=500)

        st.plotly_chart(fig, width='stretch')

        # Legend
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"<div style='padding: 8px 12px; background: {COLORS['danger']}; color: white; border-radius: 6px; text-align: center;'><b>Red Zone (15-25)</b><br>Immediate attention</div>", unsafe_allow_html=True)
        with col2:
            st.markdown(f"<div style='padding: 8px 12px; background: {COLORS['warning']}; color: black; border-radius: 6px; text-align: center;'><b>Orange Zone (5-14)</b><br>Active monitoring</div>", unsafe_allow_html=True)
        with col3:
            st.markdown(f"<div style='padding: 8px 12px; background: {COLORS['success']}; color: white; border-radius: 6px; text-align: center;'><b>Green Zone (1-4)</b><br>Acceptable risk</div>", unsafe_allow_html=True)

        # Distribution breakdown
        st.markdown("---")
        section_header("Risk Distribution by Category")

        cat_counts = defaultdict(int)
        cat_scores = defaultdict(list)
        for r in active_risks:
            cat_counts[r.category] += 1
            cat_scores[r.category].append(r.risk_score)

        if cat_counts:
            dist_data = []
            for cat in sorted(cat_counts.keys()):
                scores = cat_scores[cat]
                dist_data.append({
                    'Category': cat,
                    'Count': cat_counts[cat],
                    'Avg Score': round(sum(scores) / len(scores), 1),
                    'Max Score': max(scores),
                })

            df_dist = pd.DataFrame(dist_data)

            fig_bar = go.Figure(data=[
                go.Bar(
                    x=df_dist['Category'],
                    y=df_dist['Count'],
                    text=df_dist['Count'],
                    textposition='auto',
                    marker_color=COLORS['accent'],
                )
            ])
            apply_plotly_theme(fig_bar, show_legend=False, height=300)
            fig_bar.update_layout(xaxis_title="Category", yaxis_title="Number of Risks")
            st.plotly_chart(fig_bar, width='stretch')

    # =========================================================================
    # TAB 3: REVIEW CALENDAR
    # =========================================================================
    with tab3:
        section_header("Risk Review Calendar")

        risks_with_dates = [r for r in risks if r.next_review_date and r.status != 'Closed']
        risks_with_dates.sort(key=lambda r: r.next_review_date)

        today = date.today()
        overdue = [r for r in risks_with_dates if r.next_review_date < today]
        upcoming_30 = [r for r in risks_with_dates if today <= r.next_review_date <= today + timedelta(days=30)]
        upcoming_90 = [r for r in risks_with_dates if today <= r.next_review_date <= today + timedelta(days=90)]

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Overdue Reviews", len(overdue))
        with col2:
            st.metric("Due Next 30 Days", len(upcoming_30))
        with col3:
            st.metric("Due Next 90 Days", len(upcoming_90))

        st.markdown("---")

        if not risks_with_dates:
            st.info("No review dates set. Edit risks in the Risk List tab to add next review dates.")
        else:
            # Overdue section
            if overdue:
                st.error(f"**{len(overdue)} Overdue Review(s)**")
                for r in overdue:
                    days_over = (today - r.next_review_date).days
                    st.markdown(
                        f"- **{r.title}** — Due {r.next_review_date.strftime('%b %d, %Y')} "
                        f"({days_over} day{'s' if days_over != 1 else ''} overdue) "
                        f"| Score: {r.risk_score} | {r.status}"
                    )
                st.markdown("---")

            # Group by month
            by_month = defaultdict(list)
            for r in risks_with_dates:
                if r.next_review_date >= today:
                    month_key = r.next_review_date.strftime("%B %Y")
                    by_month[month_key].append(r)

            for month, month_risks in by_month.items():
                section_header(month)
                for r in month_risks:
                    score_badge = score_label(r.risk_score)
                    st.markdown(
                        f"- **{r.next_review_date.strftime('%b %d')}** — {r.title} "
                        f"(Score: {r.risk_score}, {score_badge}) | {r.status} | {r.review_frequency or '—'}"
                    )

            # Timeline visualization
            st.markdown("---")
            section_header("Review Timeline")

            if risks_with_dates:
                timeline_data = []
                for r in risks_with_dates:
                    timeline_data.append({
                        'Risk': r.title[:30] + "..." if len(r.title) > 30 else r.title,
                        'Date': r.next_review_date,
                        'Score': r.risk_score,
                        'Status': 'Overdue' if r.next_review_date < today else 'Upcoming',
                    })

                df_timeline = pd.DataFrame(timeline_data)
                colors = [COLORS['danger'] if s == 'Overdue' else COLORS['accent'] for s in df_timeline['Status']]

                fig_timeline = go.Figure(data=go.Scatter(
                    x=df_timeline['Date'],
                    y=df_timeline['Risk'],
                    mode='markers+text',
                    marker=dict(size=df_timeline['Score'] * 3 + 8, color=colors),
                    text=df_timeline['Score'],
                    textposition='middle right',
                    hovertemplate="<b>%{y}</b><br>Date: %{x}<br>Score: %{text}<extra></extra>",
                ))
                apply_plotly_theme(fig_timeline, show_legend=False, height=max(300, len(timeline_data) * 35))
                fig_timeline.update_layout(
                    xaxis_title="Review Date",
                    yaxis_title="",
                )
                st.plotly_chart(fig_timeline, width='stretch')

        # Risks without review dates
        no_dates = [r for r in risks if not r.next_review_date and r.status != 'Closed']
        if no_dates:
            st.markdown("---")
            st.warning(f"**{len(no_dates)} risk(s) have no review date set:**")
            for r in no_dates:
                st.markdown(f"- {r.title} (Score: {r.risk_score})")

    # =========================================================================
    # TAB 4: AI INSIGHTS
    # =========================================================================
    with tab4:
        section_header("AI Risk Analysis")
        st.markdown("Get AI-powered insights on your risk register and mitigation strategies.")

        if not is_ai_available():
            st.info(
                "Set up your Anthropic API key in Settings to enable AI-powered risk analysis. "
                "Set the `ANTHROPIC_API_KEY` environment variable or configure it in Settings."
            )
        else:
            # Overall risk register analysis
            section_header("Risk Register Analysis")
            if st.button("Analyze Risk Register", key="ai_risk_analysis"):
                with st.spinner("Analyzing risk register..."):
                    active_risks = [r for r in risks if r.status != 'Closed']
                    risks_data = [
                        {
                            'title': r.title,
                            'category': r.category,
                            'description': r.description,
                            'likelihood': r.likelihood,
                            'impact': r.impact,
                            'risk_score': r.risk_score,
                            'status': r.status,
                            'mitigation_plan': r.mitigation_plan,
                            'mitigation_actions': r.mitigation_actions,
                            'risk_owner': r.risk_owner,
                            'review_frequency': r.review_frequency,
                        }
                        for r in active_risks
                    ]

                    portfolio = get_portfolio_overview(session)
                    analysis = get_risk_register_analysis(risks_data, portfolio)

                    if analysis:
                        st.markdown(analysis)
                    else:
                        st.error("Failed to generate analysis. Check your API key.")

            st.markdown("---")

            # Per-risk mitigation suggestions
            section_header("Mitigation Suggestions")
            st.markdown("Select a risk to get AI-suggested mitigation strategies.")

            active_risks = [r for r in risks if r.status != 'Closed']
            if active_risks:
                risk_titles = [r.title for r in active_risks]
                selected_idx = st.selectbox(
                    "Select Risk",
                    range(len(active_risks)),
                    format_func=lambda i: f"[{active_risks[i].risk_score}] {active_risks[i].title}",
                    key="ai_risk_select"
                )

                selected_risk = active_risks[selected_idx]

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Likelihood", LIKELIHOOD_LABELS.get(selected_risk.likelihood, "Unknown"))
                with col2:
                    st.metric("Impact", IMPACT_LABELS.get(selected_risk.impact, "Unknown"))
                with col3:
                    st.metric("Risk Score", selected_risk.risk_score)

                if selected_risk.mitigation_plan:
                    st.markdown(f"**Current Mitigation Plan:** {selected_risk.mitigation_plan}")
                if selected_risk.mitigation_actions:
                    st.markdown(f"**Current Actions:** {selected_risk.mitigation_actions}")

                if st.button("Get Mitigation Suggestions", key="ai_mitigation"):
                    with st.spinner("Generating mitigation strategies..."):
                        risk_data = {
                            'title': selected_risk.title,
                            'category': selected_risk.category,
                            'description': selected_risk.description,
                            'likelihood': selected_risk.likelihood,
                            'impact': selected_risk.impact,
                            'risk_score': selected_risk.risk_score,
                            'status': selected_risk.status,
                            'mitigation_plan': selected_risk.mitigation_plan,
                            'mitigation_actions': selected_risk.mitigation_actions,
                        }

                        suggestions = get_mitigation_suggestions(risk_data)

                        if suggestions:
                            st.markdown(suggestions)
                        else:
                            st.error("Failed to generate suggestions. Check your API key.")
            else:
                st.info("No active risks to analyze.")

finally:
    session.close()
