"""
Settings Page - Data import, configuration, and export.
"""

import streamlit as st
import pandas as pd
import os
import sys
import yaml
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database import get_session, get_all_investments, get_all_entities, Entity, init_db
from src.importers import CSVImporter, generate_import_template
from src.portfolio import get_portfolio_overview, update_market_prices
from src.styles import apply_dark_theme, COLORS, PLOTLY_LAYOUT, page_header, section_header

st.set_page_config(page_title="Settings | Investment Register", page_icon="⚙️", layout="wide")

# Apply dark theme
apply_dark_theme()

page_header("Settings & Import", "Data import, configuration, and export")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📥 Import Data",
    "📤 Export Data",
    "⚙️ Configuration",
    "🔧 Maintenance"
])

session = get_session()

try:
    with tab1:
        st.subheader("Import Investments & Transactions")

        st.markdown("""
        Import your investment data from CSV or Excel files.
        Download the templates below to see the expected format.
        """)

        # Download templates
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Investment Template")
            investment_template = generate_import_template('investments')
            csv_investments = investment_template.to_csv(index=False)
            st.download_button(
                "📥 Download Investment Template",
                csv_investments,
                file_name="investment_template.csv",
                mime="text/csv"
            )

        with col2:
            st.markdown("### Transaction Template")
            transaction_template = generate_import_template('transactions')
            csv_transactions = transaction_template.to_csv(index=False)
            st.download_button(
                "📥 Download Transaction Template",
                csv_transactions,
                file_name="transaction_template.csv",
                mime="text/csv"
            )

        st.markdown("---")

        # Import investments
        st.markdown("### Import Investments")

        uploaded_investments = st.file_uploader(
            "Upload Investment CSV/Excel",
            type=['csv', 'xlsx', 'xls'],
            key="investment_upload"
        )

        if uploaded_investments:
            # Save to temp file
            temp_path = f"/tmp/{uploaded_investments.name}"
            with open(temp_path, 'wb') as f:
                f.write(uploaded_investments.getbuffer())

            # Preview
            importer = CSVImporter()
            preview_df, warnings = importer.preview_investments(temp_path)

            if importer.errors:
                st.error("Errors found:")
                for error in importer.errors:
                    st.markdown(f"- {error}")
            else:
                st.markdown("**Preview:**")
                st.dataframe(preview_df.head(10), use_container_width=True)

                if warnings:
                    st.warning("Warnings:")
                    for w in warnings:
                        st.markdown(f"- {w}")

                if st.button("Import Investments", key="import_inv"):
                    result = importer.import_investments(temp_path, session)

                    if result['success']:
                        st.success(f"Imported {result['imported']} investments")
                        if result['skipped']:
                            st.info(f"Skipped {result['skipped']} duplicates")
                        st.rerun()
                    else:
                        st.error("Import failed")
                        for error in result['errors']:
                            st.markdown(f"- {error}")

        st.markdown("---")

        # Import transactions
        st.markdown("### Import Transactions")

        uploaded_transactions = st.file_uploader(
            "Upload Transaction CSV/Excel",
            type=['csv', 'xlsx', 'xls'],
            key="transaction_upload"
        )

        if uploaded_transactions:
            temp_path = f"/tmp/{uploaded_transactions.name}"
            with open(temp_path, 'wb') as f:
                f.write(uploaded_transactions.getbuffer())

            importer = CSVImporter()
            preview_df, warnings = importer.preview_transactions(temp_path)

            if importer.errors:
                st.error("Errors found:")
                for error in importer.errors:
                    st.markdown(f"- {error}")
            else:
                st.markdown("**Preview:**")
                st.dataframe(preview_df.head(10), use_container_width=True)

                if st.button("Import Transactions", key="import_tx"):
                    result = importer.import_transactions(temp_path, session)

                    if result['success']:
                        st.success(f"Imported {result['imported']} transactions")
                        st.rerun()
                    else:
                        st.error("Import failed")

        st.markdown("---")

        # Google Sheets (placeholder)
        st.markdown("### Google Sheets Integration")
        st.info("""
        To use Google Sheets integration:
        1. Create a Google Cloud service account
        2. Download the credentials JSON
        3. Share your sheet with the service account email
        4. Upload credentials below
        """)

        credentials_file = st.file_uploader(
            "Upload Google Service Account Credentials",
            type=['json'],
            key="google_creds"
        )

        if credentials_file:
            st.session_state['google_credentials'] = credentials_file.read()
            st.success("Credentials uploaded (session only)")

    with tab2:
        st.subheader("Export Data")

        portfolio = get_portfolio_overview(session)

        if portfolio['summary']['investment_count'] > 0:
            # Export holdings
            st.markdown("### Export Holdings")

            holdings_df = pd.DataFrame(portfolio['holdings'])
            csv_holdings = holdings_df.to_csv(index=False)

            st.download_button(
                "📤 Download Holdings CSV",
                csv_holdings,
                file_name="holdings_export.csv",
                mime="text/csv"
            )

            # Export summary
            st.markdown("### Export Summary")

            summary_data = {
                'Metric': [
                    'Total Portfolio Value (CAD)',
                    'Total Cost Basis (CAD)',
                    'Total Gain/Loss (CAD)',
                    'Total Return (%)',
                    'Number of Positions'
                ],
                'Value': [
                    f"${portfolio['summary']['total_value_cad']:,.2f}",
                    f"${portfolio['summary']['total_cost_basis_cad']:,.2f}",
                    f"${portfolio['summary']['total_gain']:,.2f}",
                    f"{portfolio['summary']['total_gain_pct']:.2f}%",
                    portfolio['summary']['investment_count']
                ]
            }

            summary_df = pd.DataFrame(summary_data)
            csv_summary = summary_df.to_csv(index=False)

            st.download_button(
                "📤 Download Summary CSV",
                csv_summary,
                file_name="portfolio_summary.csv",
                mime="text/csv"
            )

            # Export by asset class
            st.markdown("### Export by Asset Class")

            ac_data = []
            for ac, data in portfolio['by_asset_class'].items():
                ac_data.append({
                    'Asset Class': ac,
                    'Value (CAD)': data['value'],
                    'Cost Basis (CAD)': data['cost'],
                    'Gain/Loss (CAD)': data['value'] - data['cost'],
                    'Return (%)': data['gain_pct'],
                    'Weight (%)': data['weight']
                })

            ac_df = pd.DataFrame(ac_data)
            csv_ac = ac_df.to_csv(index=False)

            st.download_button(
                "📤 Download Asset Class Breakdown",
                csv_ac,
                file_name="asset_class_breakdown.csv",
                mime="text/csv"
            )

        else:
            st.info("No data to export yet.")

    with tab3:
        st.subheader("Configuration")

        # Load current config
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml')

        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
        except:
            config = {}

        # Investment Policy
        st.markdown("### Investment Policy Settings")

        col1, col2 = st.columns(2)

        with col1:
            risk_profile = st.selectbox(
                "Risk Profile",
                ["conservative", "moderate", "aggressive"],
                index=["conservative", "moderate", "aggressive"].index(
                    config.get('investment_policy', {}).get('risk_profile', 'aggressive')
                )
            )

            horizon = st.selectbox(
                "Investment Horizon",
                ["short", "medium", "long", "mixed"],
                index=["short", "medium", "long", "mixed"].index(
                    config.get('investment_policy', {}).get('investment_horizon', 'mixed')
                )
            )

        with col2:
            max_position = st.slider(
                "Max Single Position (%)",
                min_value=5,
                max_value=50,
                value=int(config.get('investment_policy', {}).get('max_single_position_pct', 20) * 100) // 100
            )

            min_liquidity = st.slider(
                "Min Liquidity (%)",
                min_value=5,
                max_value=50,
                value=int(config.get('investment_policy', {}).get('min_liquidity_pct', 15) * 100) // 100
            )

        st.markdown("### Target Allocation")

        target_allocation = config.get('investment_policy', {}).get('target_allocation', {})

        new_allocation = {}
        cols = st.columns(3)

        asset_classes = [
            'PUBLIC_EQUITY', 'PRIVATE_BUSINESS', 'VENTURE_FUND',
            'VENTURE_ENTITY', 'REAL_ESTATE', 'GOLD', 'CRYPTO', 'CASH'
        ]

        for i, ac in enumerate(asset_classes):
            with cols[i % 3]:
                current = target_allocation.get(ac, 0.1)
                new_allocation[ac] = st.number_input(
                    ac.replace('_', ' ').title(),
                    min_value=0.0,
                    max_value=1.0,
                    value=float(current),
                    step=0.05,
                    format="%.2f",
                    key=f"alloc_{ac}"
                )

        # Check total
        total_alloc = sum(new_allocation.values())
        if abs(total_alloc - 1.0) > 0.01:
            st.warning(f"Total allocation is {total_alloc:.0%}, should be 100%")

        if st.button("Save Configuration"):
            # Update config
            config['investment_policy'] = {
                'risk_profile': risk_profile,
                'investment_horizon': horizon,
                'max_single_position_pct': max_position / 100,
                'min_liquidity_pct': min_liquidity / 100,
                'target_allocation': new_allocation,
                'tax_jurisdiction': 'Canada',
                'consider_capital_gains_deferral': True
            }

            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)

            st.success("Configuration saved!")

        st.markdown("---")

        # API Keys
        st.markdown("### API Configuration")

        api_key = st.text_input(
            "Anthropic API Key",
            type="password",
            value=os.environ.get('ANTHROPIC_API_KEY', ''),
            help="Required for AI Advisor features"
        )

        if st.button("Set API Key (Session Only)"):
            if api_key:
                os.environ['ANTHROPIC_API_KEY'] = api_key
                st.success("API key set for this session")

        st.markdown("---")

        # Entities
        st.markdown("### Manage Entities")

        entities = get_all_entities(session)
        st.markdown("**Current Entities:**")
        for e in entities:
            st.markdown(f"- {e.name} ({e.entity_type})")

        with st.form("add_entity"):
            new_entity_name = st.text_input("New Entity Name")
            new_entity_type = st.selectbox(
                "Entity Type",
                ["corporation", "individual", "trust", "partnership"]
            )

            if st.form_submit_button("Add Entity"):
                if new_entity_name:
                    entity = Entity(
                        name=new_entity_name,
                        entity_type=new_entity_type
                    )
                    session.add(entity)
                    session.commit()
                    st.success(f"Added entity: {new_entity_name}")
                    st.rerun()

    with tab4:
        st.subheader("Maintenance")

        # Refresh prices
        st.markdown("### Market Data")

        if st.button("🔄 Refresh All Prices"):
            with st.spinner("Updating market prices..."):
                result = update_market_prices(session)
                st.success(f"Updated {result['updated']} of {result['total']} positions")

                if result['errors']:
                    st.warning("Some errors occurred:")
                    for error in result['errors'][:5]:
                        st.markdown(f"- {error}")

        st.markdown("---")

        # Database stats
        st.markdown("### Database Statistics")

        investments = get_all_investments(session, active_only=False)
        active = len([i for i in investments if i.is_active])
        inactive = len(investments) - active

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Investments", len(investments))
        with col2:
            st.metric("Active", active)
        with col3:
            st.metric("Inactive", inactive)

        st.markdown("---")

        # Reset database (danger zone)
        st.markdown("### Danger Zone")

        with st.expander("⚠️ Reset Database"):
            st.warning("This will delete ALL data and cannot be undone!")

            confirm = st.text_input(
                "Type 'DELETE ALL DATA' to confirm",
                key="confirm_delete"
            )

            if st.button("Reset Database", type="primary"):
                if confirm == "DELETE ALL DATA":
                    # Delete database file
                    db_path = os.path.join(
                        os.path.dirname(os.path.dirname(__file__)),
                        'data', 'investments.db'
                    )
                    if os.path.exists(db_path):
                        os.remove(db_path)

                    # Reinitialize
                    init_db()
                    st.success("Database reset complete")
                    st.rerun()
                else:
                    st.error("Please type the confirmation text exactly")

finally:
    session.close()
