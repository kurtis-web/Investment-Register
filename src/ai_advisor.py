"""
AI Investment Advisor powered by Claude.
Provides recommendations, rebalancing suggestions, risk analysis, and market commentary.
"""

import os
import json
from datetime import datetime, date
from typing import Dict, List, Optional
import yaml

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class AIAdvisor:
    """AI-powered investment advisor using Claude."""

    def __init__(self, config_path: str = None):
        self.api_key = os.environ.get('ANTHROPIC_API_KEY')
        self.client = None

        if ANTHROPIC_AVAILABLE and self.api_key:
            self.client = Anthropic(api_key=self.api_key)

        # Load config
        if config_path is None:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml')

        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except:
            self.config = {}

        self.investment_policy = self.config.get('investment_policy', {})

    def is_available(self) -> bool:
        """Check if AI advisor is available (API key set)."""
        return self.client is not None

    def _call_claude(self, system_prompt: str, user_prompt: str, max_tokens: int = 2000) -> Optional[str]:
        """Make a call to Claude API."""
        if not self.is_available():
            return None

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            return message.content[0].text
        except Exception as e:
            print(f"Claude API error: {e}")
            return None

    def get_portfolio_analysis(self, portfolio_data: Dict) -> Optional[str]:
        """
        Get comprehensive portfolio analysis and recommendations.
        """
        system_prompt = """You are an expert investment advisor for a Canadian single family office.
You provide thoughtful, actionable advice considering:
- The client's aggressive risk profile
- Mixed investment horizon (cash flow needs + generational wealth)
- Canadian tax implications and capital gains deferral strategies
- Portfolio concentration and liquidity concerns

Provide clear, structured analysis with specific recommendations.
Use Canadian dollar figures. Be direct and professional."""

        portfolio_summary = self._format_portfolio_for_ai(portfolio_data)

        user_prompt = f"""Analyze this investment portfolio and provide recommendations:

{portfolio_summary}

Investment Policy:
- Risk Profile: {self.investment_policy.get('risk_profile', 'aggressive')}
- Investment Horizon: {self.investment_policy.get('investment_horizon', 'mixed')}
- Tax Jurisdiction: {self.investment_policy.get('tax_jurisdiction', 'Canada')}
- Consider Capital Gains Deferral: {self.investment_policy.get('consider_capital_gains_deferral', True)}

Please provide:
1. Portfolio Health Assessment (2-3 sentences)
2. Key Strengths (bullet points)
3. Areas of Concern (bullet points)
4. Top 3 Actionable Recommendations
5. Tax Optimization Opportunities
"""

        return self._call_claude(system_prompt, user_prompt)

    def get_rebalancing_recommendations(self, portfolio_data: Dict, target_allocation: Dict) -> Optional[str]:
        """
        Get specific rebalancing recommendations.
        """
        system_prompt = """You are an investment advisor specializing in portfolio rebalancing for high-net-worth Canadian clients.
Consider transaction costs, tax implications, and market timing when making recommendations.
Be specific about which positions to adjust and by how much."""

        portfolio_summary = self._format_portfolio_for_ai(portfolio_data)
        target_str = json.dumps(target_allocation, indent=2)

        user_prompt = f"""The client needs rebalancing recommendations.

Current Portfolio:
{portfolio_summary}

Target Allocation:
{target_str}

Please provide:
1. Priority rebalancing actions (most urgent first)
2. Specific positions to trim or add
3. Tax-efficient execution strategy
4. Timeline recommendation (immediate vs. gradual)
"""

        return self._call_claude(system_prompt, user_prompt)

    def get_risk_assessment(self, portfolio_data: Dict) -> Optional[str]:
        """
        Get detailed risk assessment.
        """
        system_prompt = """You are a risk management expert for investment portfolios.
Identify and quantify risks clearly. Provide specific mitigation strategies.
Consider concentration risk, liquidity risk, market risk, and currency risk."""

        portfolio_summary = self._format_portfolio_for_ai(portfolio_data)
        concentration = portfolio_data.get('risk', {}).get('concentration', {})
        liquidity = portfolio_data.get('risk', {}).get('liquidity', {})

        user_prompt = f"""Assess the risks in this portfolio:

{portfolio_summary}

Concentration Analysis:
- HHI Index: {concentration.get('hhi', 'N/A')}
- Concentrated Positions: {json.dumps(concentration.get('concentrated_positions', []))}

Liquidity Analysis:
- Liquid Percentage: {liquidity.get('liquid_pct', 'N/A'):.1f}%
- Illiquid Percentage: {liquidity.get('illiquid_pct', 'N/A'):.1f}%

Please provide:
1. Overall Risk Rating (Low/Medium/High/Very High)
2. Key Risk Factors (ranked by severity)
3. Specific Mitigation Strategies
4. Stress Test Scenarios to Consider
"""

        return self._call_claude(system_prompt, user_prompt)

    def get_market_commentary(self, portfolio_data: Dict, focus_areas: List[str] = None) -> Optional[str]:
        """
        Get market commentary relevant to the portfolio holdings.
        """
        if focus_areas is None:
            focus_areas = list(portfolio_data.get('by_asset_class', {}).keys())

        system_prompt = """You are a market strategist providing timely commentary for a Canadian investor.
Focus on actionable insights relevant to the specific asset classes held.
Consider both Canadian and US markets. Be concise but insightful."""

        holdings_by_class = {}
        for h in portfolio_data.get('holdings', []):
            ac = h.get('asset_class', 'Other')
            if ac not in holdings_by_class:
                holdings_by_class[ac] = []
            holdings_by_class[ac].append(h.get('name', 'Unknown'))

        user_prompt = f"""Provide market commentary relevant to this portfolio:

Asset Classes Held:
{json.dumps(holdings_by_class, indent=2)}

Focus Areas: {', '.join(focus_areas)}

Please provide:
1. Current Market Environment (2-3 sentences)
2. Asset Class Outlook for each held class
3. Specific Considerations for Canadian Investors
4. Key Events/Risks to Watch
"""

        return self._call_claude(system_prompt, user_prompt)

    def get_scenario_analysis(self, portfolio_data: Dict, scenario: str) -> Optional[str]:
        """
        Analyze portfolio performance under a specific scenario.

        Scenarios: 'market_crash', 'recession', 'inflation', 'rate_hike', 'cad_depreciation'
        """
        system_prompt = """You are a portfolio stress testing expert.
Provide realistic estimates of portfolio impact under various scenarios.
Be specific about which holdings would be most affected and why."""

        portfolio_summary = self._format_portfolio_for_ai(portfolio_data)

        scenario_descriptions = {
            'market_crash': 'A 30% decline in global equity markets over 3 months',
            'recession': 'A Canadian recession with GDP declining 2% over 12 months',
            'inflation': 'Inflation rising to 8% with Bank of Canada raising rates aggressively',
            'rate_hike': 'Bank of Canada raising rates by 200 basis points over 6 months',
            'cad_depreciation': 'Canadian dollar declining 15% against USD',
            'tech_crash': 'Technology sector declining 40% while other sectors remain flat',
            'real_estate_correction': 'Canadian real estate values declining 25%'
        }

        scenario_desc = scenario_descriptions.get(scenario, scenario)

        user_prompt = f"""Analyze this portfolio under the following scenario:

Scenario: {scenario_desc}

Current Portfolio:
{portfolio_summary}

Please provide:
1. Estimated Portfolio Impact (percentage and dollar terms)
2. Most Vulnerable Holdings (top 3-5)
3. Holdings That May Benefit
4. Recommended Defensive Actions
5. Recovery Timeline Estimate
"""

        return self._call_claude(system_prompt, user_prompt)

    def suggest_target_allocation(self, portfolio_data: Dict) -> Optional[str]:
        """
        AI-suggested target allocation based on risk profile and current holdings.
        """
        system_prompt = """You are an asset allocation strategist for high-net-worth Canadian clients.
Design allocations that balance growth with appropriate risk management.
Consider the client's aggressive profile but also their need for some liquidity."""

        portfolio_summary = self._format_portfolio_for_ai(portfolio_data)

        user_prompt = f"""Suggest an optimal target allocation for this portfolio:

Current Portfolio:
{portfolio_summary}

Client Profile:
- Risk Tolerance: Aggressive
- Investment Horizon: Mixed (some current income needs, but primarily generational wealth building)
- Tax Jurisdiction: Canada
- Liquidity Needs: Moderate (15-20% liquid recommended)

Please provide:
1. Recommended Target Allocation (by asset class, percentages)
2. Rationale for Each Allocation
3. Comparison to Current Allocation
4. Implementation Priority (what to change first)
5. Expected Risk/Return Profile
"""

        return self._call_claude(system_prompt, user_prompt)

    def draft_investment_policy_statement(self, portfolio_data: Dict, preferences: Dict = None) -> Optional[str]:
        """
        Draft an Investment Policy Statement.
        """
        if preferences is None:
            preferences = {}

        system_prompt = """You are an investment policy expert drafting formal Investment Policy Statements.
Create a professional, comprehensive document that can guide investment decisions.
Use clear, actionable language suitable for a family office."""

        portfolio_summary = self._format_portfolio_for_ai(portfolio_data)

        user_prompt = f"""Draft an Investment Policy Statement for this family office:

Current Portfolio Size: C${portfolio_data.get('summary', {}).get('total_value_cad', 0):,.0f}

Preferences:
- Risk Profile: {preferences.get('risk_profile', 'Aggressive')}
- Investment Horizon: {preferences.get('horizon', 'Mixed - current income and generational wealth')}
- Tax Jurisdiction: {preferences.get('tax_jurisdiction', 'Canada')}
- Liquidity Requirements: {preferences.get('liquidity', 'Moderate')}
- ESG Considerations: {preferences.get('esg', 'None specified')}
- Restricted Investments: {preferences.get('restrictions', 'None specified')}

Current Holdings Summary:
{portfolio_summary}

Please draft a complete IPS including:
1. Investment Objectives
2. Risk Tolerance Statement
3. Asset Allocation Guidelines
4. Rebalancing Policy
5. Performance Benchmarks
6. Investment Restrictions
7. Tax Considerations
8. Review and Amendment Process
"""

        return self._call_claude(system_prompt, user_prompt, max_tokens=4000)

    def get_risk_register_analysis(self, risks_data: List[Dict], portfolio_data: Dict) -> Optional[str]:
        """Analyze the risk register and provide insights."""
        system_prompt = """You are a risk management expert for a Canadian single family office.
You analyze risk registers and provide actionable insights on:
- Overall risk posture and trends
- Gaps in risk identification
- Prioritization of risks requiring immediate attention
- Correlation between risks that could compound
- Comparison to typical family office risk profiles
Be specific, structured, and professional. Use markdown formatting."""

        risks_text = self._format_risks_for_ai(risks_data)
        portfolio_summary = self._format_portfolio_for_ai(portfolio_data)

        user_prompt = f"""Analyze this risk register for a family office:

{risks_text}

Portfolio Context:
{portfolio_summary}

Please provide:
1. Overall Risk Posture Assessment (2-3 sentences)
2. Top 3 Priority Risks Requiring Immediate Attention
3. Gaps in Risk Coverage (what risks are missing?)
4. Risk Correlations (which risks could compound each other?)
5. Recommendations for Risk Reduction
6. Suggested Review Schedule Adjustments
"""

        return self._call_claude(system_prompt, user_prompt, max_tokens=3000)

    def get_mitigation_suggestions(self, risk_data: Dict) -> Optional[str]:
        """Get AI-suggested mitigation strategies for a specific risk."""
        system_prompt = """You are a risk mitigation specialist for high-net-worth families and family offices.
Provide specific, actionable mitigation strategies that are practical to implement.
Consider insurance, legal structures, operational controls, and contingency planning.
Use markdown formatting."""

        user_prompt = f"""Suggest mitigation strategies for this risk:

Risk: {risk_data.get('title', 'Unknown')}
Category: {risk_data.get('category', 'Unknown')}
Description: {risk_data.get('description', 'No description')}
Likelihood: {risk_data.get('likelihood', 0)} (0=Not at all, 5=Almost certain)
Impact: {risk_data.get('impact', 0)} (0=No impact, 5=Extreme)
Risk Score: {risk_data.get('risk_score', 0)}
Current Status: {risk_data.get('status', 'Identified')}
Current Mitigation Plan: {risk_data.get('mitigation_plan', 'None')}
Current Mitigation Actions: {risk_data.get('mitigation_actions', 'None')}

Please provide:
1. Recommended Mitigation Strategies (3-5 specific actions)
2. Preventive Controls (to reduce likelihood)
3. Detective Controls (to identify early)
4. Response Plan (if the risk materializes)
5. Estimated Residual Risk After Mitigation
6. Suggested Review Frequency
"""

        return self._call_claude(system_prompt, user_prompt, max_tokens=2000)

    def _format_risks_for_ai(self, risks_data: List[Dict]) -> str:
        """Format risk data for AI consumption."""
        lines = [f"Total Risks: {len(risks_data)}", ""]

        categories = {}
        for r in risks_data:
            cat = r.get('category', 'Unknown')
            categories[cat] = categories.get(cat, 0) + 1

        lines.append("By Category:")
        for cat, count in sorted(categories.items()):
            lines.append(f"  - {cat}: {count}")

        lines.append("")
        lines.append("Risk Details (sorted by score, highest first):")
        sorted_risks = sorted(risks_data, key=lambda x: x.get('risk_score', 0), reverse=True)

        for r in sorted_risks:
            lines.append(
                f"  - [{r.get('risk_score', 0)}] {r.get('title', 'Unknown')} "
                f"(L:{r.get('likelihood', '?')} x I:{r.get('impact', '?')}) "
                f"[{r.get('status', '?')}] [{r.get('category', '?')}]"
            )
            if r.get('mitigation_plan'):
                lines.append(f"    Mitigation: {r['mitigation_plan'][:100]}")

        return "\n".join(lines)

    def _format_portfolio_for_ai(self, portfolio_data: Dict) -> str:
        """Format portfolio data for AI consumption."""
        summary = portfolio_data.get('summary', {})
        by_asset_class = portfolio_data.get('by_asset_class', {})
        by_entity = portfolio_data.get('by_entity', {})
        holdings = portfolio_data.get('holdings', [])

        lines = [
            f"Total Portfolio Value: C${summary.get('total_value_cad', 0):,.2f}",
            f"Total Cost Basis: C${summary.get('total_cost_basis_cad', 0):,.2f}",
            f"Total Gain/Loss: C${summary.get('total_gain', 0):,.2f} ({summary.get('total_gain_pct', 0):.1f}%)",
            f"Number of Positions: {summary.get('investment_count', 0)}",
            "",
            "Allocation by Asset Class:",
        ]

        for ac, data in sorted(by_asset_class.items(), key=lambda x: x[1]['value'], reverse=True):
            lines.append(f"  - {ac}: C${data['value']:,.0f} ({data['weight']:.1f}%)")

        lines.append("")
        lines.append("Allocation by Entity:")
        for entity, data in by_entity.items():
            lines.append(f"  - {entity}: C${data['value']:,.0f} ({data['weight']:.1f}%)")

        lines.append("")
        lines.append("Top 10 Holdings:")
        sorted_holdings = sorted(holdings, key=lambda x: x['current_value'], reverse=True)[:10]
        for h in sorted_holdings:
            gain_str = f"+{h['unrealized_gain_pct']:.1f}%" if h['unrealized_gain_pct'] >= 0 else f"{h['unrealized_gain_pct']:.1f}%"
            lines.append(f"  - {h['name']} ({h['asset_class']}): C${h['current_value']:,.0f} ({h['weight']:.1f}%) [{gain_str}]")

        return "\n".join(lines)


# Singleton instance
_advisor = None


def get_advisor() -> AIAdvisor:
    """Get the AI advisor instance."""
    global _advisor
    if _advisor is None:
        _advisor = AIAdvisor()
    return _advisor


# Convenience functions
def get_portfolio_analysis(portfolio_data: Dict) -> Optional[str]:
    return get_advisor().get_portfolio_analysis(portfolio_data)


def get_rebalancing_recommendations(portfolio_data: Dict, target_allocation: Dict) -> Optional[str]:
    return get_advisor().get_rebalancing_recommendations(portfolio_data, target_allocation)


def get_risk_assessment(portfolio_data: Dict) -> Optional[str]:
    return get_advisor().get_risk_assessment(portfolio_data)


def get_market_commentary(portfolio_data: Dict) -> Optional[str]:
    return get_advisor().get_market_commentary(portfolio_data)


def get_scenario_analysis(portfolio_data: Dict, scenario: str) -> Optional[str]:
    return get_advisor().get_scenario_analysis(portfolio_data, scenario)


def suggest_target_allocation(portfolio_data: Dict) -> Optional[str]:
    return get_advisor().suggest_target_allocation(portfolio_data)


def draft_investment_policy_statement(portfolio_data: Dict, preferences: Dict = None) -> Optional[str]:
    return get_advisor().draft_investment_policy_statement(portfolio_data, preferences)


def get_risk_register_analysis(risks_data: List[Dict], portfolio_data: Dict) -> Optional[str]:
    return get_advisor().get_risk_register_analysis(risks_data, portfolio_data)


def get_mitigation_suggestions(risk_data: Dict) -> Optional[str]:
    return get_advisor().get_mitigation_suggestions(risk_data)


def is_ai_available() -> bool:
    return get_advisor().is_available()
