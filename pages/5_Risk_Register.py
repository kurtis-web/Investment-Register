"""
Risk Register - Risk identification, assessment, and monitoring.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from collections import defaultdict
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

st.set_page_config(page_title="Risk Register | Investment Register", page_icon="\U0001f6e1\ufe0f", layout="wide")

apply_dark_theme()

page_header("Risk Register", "Risk identification, assessment, and monitoring")

# --- Constants ---

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

RISK_CATEGORIES = [
    "Financial", "Operational", "Legal", "Reputational",
    "Strategic", "Compliance", "Personnel", "Cybersecurity", "Market"
]

RISK_STATUSES = [
    "Identified", "Assessed", "Mitigating", "Accepted", "Closed", "Monitoring"
]

REVIEW_FREQUENCIES = ["Monthly", "Quarterly", "Semi-annually", "Annually"]


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

        # Risk table
        if filtered_risks:
            table_data = []
            for r in filtered_risks:
                table_data.append({
                    'Title': r.title,
                    'Category': r.category,
                    'Entity': entity_map.get(r.entity_id, '—'),
                    'Owner': r.risk_owner or '—',
                    'Likelihood': r.likelihood,
                    'Impact': r.impact,
                    'Score': r.risk_score,
                    'Status': r.status,
                    'Review': r.review_frequency or '—',
                    'Next Review': r.next_review_date.strftime('%Y-%m-%d') if r.next_review_date else '—',
                })

            df = pd.DataFrame(table_data)

            def color_score(val):
                if val >= 15:
                    return f'background-color: {COLORS["danger"]}; color: white; font-weight: bold'
                elif val >= 5:
                    return f'background-color: {COLORS["warning"]}; color: black; font-weight: bold'
                else:
                    return f'background-color: {COLORS["success"]}; color: white; font-weight: bold'

            styled_df = df.style.map(color_score, subset=['Score'])
            st.dataframe(styled_df, width='stretch', hide_index=True)
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
                    new_owner = st.text_input("Risk Owner")
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
                            risk_owner=new_owner if new_owner else None,
                            likelihood=new_likelihood,
                            impact=new_impact,
                            status=new_status,
                            mitigation_plan=new_mitigation_plan if new_mitigation_plan else None,
                            mitigation_actions=new_mitigation_actions if new_mitigation_actions else None,
                            review_frequency=new_review_freq,
                            next_review_date=new_review_date,
                        )
                        st.success(f"Added risk: {new_title}")
                        st.rerun()
                    else:
                        st.error("Title is required.")

        # Edit/Delete existing risks
        if filtered_risks:
            section_header("Edit Risks")
            for r in filtered_risks:
                color = score_color(r.risk_score)
                label = score_label(r.risk_score)
                with st.expander(f"[{r.risk_score}] {r.title} — {r.category} ({r.status})"):
                    with st.form(f"edit_risk_{r.id}"):
                        edit_title = st.text_input("Title", value=r.title, key=f"edit_title_{r.id}")
                        edit_description = st.text_area("Description", value=r.description or "", key=f"edit_desc_{r.id}")

                        col1, col2 = st.columns(2)
                        with col1:
                            edit_category = st.selectbox(
                                "Category", RISK_CATEGORIES,
                                index=RISK_CATEGORIES.index(r.category) if r.category in RISK_CATEGORIES else 0,
                                key=f"edit_cat_{r.id}"
                            )
                            entity_options = ["None"] + [e.name for e in entities]
                            current_entity = entity_map.get(r.entity_id, "None")
                            edit_entity = st.selectbox(
                                "Entity", entity_options,
                                index=entity_options.index(current_entity) if current_entity in entity_options else 0,
                                key=f"edit_entity_{r.id}"
                            )
                            inv_options = ["None"] + [f"{i.name} ({i.symbol})" if i.symbol else i.name for i in investments]
                            current_inv = "None"
                            if r.investment_id:
                                inv_obj = next((i for i in investments if i.id == r.investment_id), None)
                                if inv_obj:
                                    current_inv = f"{inv_obj.name} ({inv_obj.symbol})" if inv_obj.symbol else inv_obj.name
                            edit_investment = st.selectbox(
                                "Linked Investment", inv_options,
                                index=inv_options.index(current_inv) if current_inv in inv_options else 0,
                                key=f"edit_inv_{r.id}"
                            )
                        with col2:
                            edit_owner = st.text_input("Risk Owner", value=r.risk_owner or "", key=f"edit_owner_{r.id}")
                            edit_status = st.selectbox(
                                "Status", RISK_STATUSES,
                                index=RISK_STATUSES.index(r.status) if r.status in RISK_STATUSES else 0,
                                key=f"edit_status_{r.id}"
                            )
                            edit_review_freq = st.selectbox(
                                "Review Frequency", REVIEW_FREQUENCIES,
                                index=REVIEW_FREQUENCIES.index(r.review_frequency) if r.review_frequency in REVIEW_FREQUENCIES else 0,
                                key=f"edit_freq_{r.id}"
                            )

                        col1, col2, col3 = st.columns(3)
                        with col1:
                            edit_likelihood = st.selectbox(
                                "Likelihood", list(LIKELIHOOD_LABELS.keys()),
                                format_func=lambda x: LIKELIHOOD_LABELS[x],
                                index=r.likelihood,
                                key=f"edit_like_{r.id}"
                            )
                        with col2:
                            edit_impact = st.selectbox(
                                "Impact", list(IMPACT_LABELS.keys()),
                                format_func=lambda x: IMPACT_LABELS[x],
                                index=r.impact,
                                key=f"edit_impact_{r.id}"
                            )
                        with col3:
                            st.metric("Calculated Score", edit_likelihood * edit_impact)

                        edit_mitigation_plan = st.text_area("Mitigation Plan", value=r.mitigation_plan or "", key=f"edit_mit_{r.id}")
                        edit_mitigation_actions = st.text_area("Mitigation Actions", value=r.mitigation_actions or "", key=f"edit_act_{r.id}")
                        edit_review_date = st.date_input(
                            "Next Review Date",
                            value=r.next_review_date if r.next_review_date else date.today() + timedelta(days=90),
                            key=f"edit_date_{r.id}"
                        )

                        col1, col2 = st.columns(2)
                        with col1:
                            update_clicked = st.form_submit_button("Update Risk")
                        with col2:
                            delete_clicked = st.form_submit_button("Delete Risk")

                    if update_clicked:
                        entity_id = None
                        if edit_entity != "None":
                            entity_obj = next((e for e in entities if e.name == edit_entity), None)
                            if entity_obj:
                                entity_id = entity_obj.id

                        investment_id = None
                        if edit_investment != "None":
                            inv_pos = inv_options.index(edit_investment) - 1 if edit_investment in inv_options else -1
                            if 0 <= inv_pos < len(investments):
                                investment_id = investments[inv_pos].id

                        update_risk(
                            session, r.id,
                            title=edit_title,
                            description=edit_description if edit_description else None,
                            category=edit_category,
                            entity_id=entity_id,
                            investment_id=investment_id,
                            risk_owner=edit_owner if edit_owner else None,
                            likelihood=edit_likelihood,
                            impact=edit_impact,
                            status=edit_status,
                            mitigation_plan=edit_mitigation_plan if edit_mitigation_plan else None,
                            mitigation_actions=edit_mitigation_actions if edit_mitigation_actions else None,
                            review_frequency=edit_review_freq,
                            next_review_date=edit_review_date,
                        )
                        st.success(f"Updated: {edit_title}")
                        st.rerun()

                    if delete_clicked:
                        delete_risk(session, r.id)
                        st.success(f"Deleted: {r.title}")
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
