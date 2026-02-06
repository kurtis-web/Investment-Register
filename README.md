# Investment Register

A comprehensive investment tracking and analysis dashboard for family offices. Built with Streamlit and Python.

## Features

- **Multi-Asset Tracking**: Public equities, private businesses, venture funds, real estate, gold, crypto, and more
- **Multi-Currency Support**: CAD and USD with automatic FX conversion
- **Multiple Entities**: Track investments across HoldCo and Personal accounts
- **Real-Time Market Data**: Yahoo Finance for stocks, Kraken for crypto
- **Performance Analytics**: IRR, simple returns, benchmark comparisons
- **AI-Powered Recommendations**: Portfolio analysis, rebalancing suggestions, risk assessment (requires Anthropic API key)
- **Scenario Analysis**: Stress testing for various market conditions
- **CSV/Excel Import**: Easy data migration from existing spreadsheets

## Quick Start

### 1. Install Dependencies

```bash
cd "/Users/kurtisvallee/Desktop/Investment Register"
pip install -r requirements.txt
```

### 2. Run the Application

```bash
streamlit run Portfolio_Dashboard.py
```

The dashboard will open in your browser at `http://localhost:8501`

### 3. Import Your Data

1. Go to **Settings** page
2. Download the investment template
3. Fill in your investment data
4. Upload and import

Or use the sample data provided in `data/sample_investments.csv`.

## Setting Up AI Features

To enable AI-powered recommendations:

1. Get an API key from [Anthropic Console](https://console.anthropic.com/)
2. Set the environment variable:
   ```bash
   export ANTHROPIC_API_KEY='your-api-key'
   ```
3. Or enter it on the AI Advisor page

## Project Structure

```
Investment Register/
├── Portfolio_Dashboard.py    # Main Streamlit application
├── requirements.txt          # Python dependencies
├── config.yaml              # Configuration settings
├── data/
│   ├── investments.db       # SQLite database (created on first run)
│   └── sample_investments.csv
├── src/
│   ├── database.py          # Database models and operations
│   ├── market_data.py       # Market data fetching
│   ├── calculations.py      # Financial calculations
│   ├── portfolio.py         # Portfolio analytics
│   ├── ai_advisor.py        # AI recommendation engine
│   └── importers.py         # CSV/Excel import
└── pages/
    ├── 1_Holdings.py        # Holdings detail page
    ├── 2_Performance.py     # Performance & benchmarks
    ├── 3_AI_Advisor.py      # AI recommendations
    ├── 4_Scenarios.py       # What-if analysis
    └── 5_Settings.py        # Import & configuration
```

## Dashboard Pages

### Dashboard (Home)
- Total portfolio value with allocation charts
- Top holdings visualization
- Risk summary (concentration, liquidity)
- Recent activity

### Holdings
- Detailed view of all positions
- Filter by entity or asset class
- Add new investments manually
- Real-time price refresh

### Performance
- Simple return and IRR calculations
- Benchmark comparisons (S&P 500, NASDAQ, TSX)
- Performance by asset class and entity
- Top and bottom performers

### AI Advisor
- Portfolio health assessment
- Rebalancing recommendations
- Risk assessment
- Market commentary
- Investment Policy Statement generator

### Scenarios
- Pre-built scenarios (market crash, recession, inflation, etc.)
- Custom scenario builder
- Impact analysis by asset class
- Most affected holdings

### Settings
- Import investments and transactions
- Export data to CSV
- Configure investment policy
- Manage entities
- API key configuration

## Data Import Format

### Investments CSV
| Column | Description | Required |
|--------|-------------|----------|
| name | Investment name | Yes |
| symbol | Ticker symbol | No |
| asset_class | Type (Public Equities, Private Business, etc.) | Yes |
| entity | HoldCo or Personal | Yes |
| currency | CAD or USD | No (default: CAD) |
| quantity | Number of units | Yes |
| cost_basis | Total cost | Yes |
| current_value | Current market value | No |
| purchase_date | Date of purchase (YYYY-MM-DD) | No |
| notes | Additional notes | No |

### Transactions CSV
| Column | Description | Required |
|--------|-------------|----------|
| investment_name | Name of the investment | Yes |
| date | Transaction date | Yes |
| type | Buy, Sell, Dividend, etc. | Yes |
| quantity | Units transacted | No |
| price | Price per unit | No |
| amount | Total amount | Yes |
| currency | CAD or USD | No |

## Configuration

Edit `config.yaml` to customize:

- Base currency
- Supported currencies
- Asset class definitions
- Benchmark indices
- Investment policy parameters
- Target allocation

## Future Enhancements

- [ ] Cloud deployment with authentication
- [ ] Xero accounting integration
- [ ] Real-time alerts and notifications
- [ ] Historical portfolio snapshots
- [ ] PDF report generation
- [ ] Mobile-responsive design

## Security Notes

- The database is stored locally in SQLite
- API keys should be set via environment variables
- For production use, consider implementing proper authentication
- Sensitive data should be backed up securely

## Support

For issues or feature requests, please document them for future development sessions.
