from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class CompanyStats(BaseModel):
    """
    Basic statistics about a company.
    """
    market_cap_million_usd: Optional[float] = Field(None, description="Market Capitalization in millions of USD.")
    employees_count: Optional[int] = Field(None, description="Number of employees.")
    headquarters_location: Optional[str] = Field(None, description="Location of the company's headquarters.")
    ipo_date: Optional[str] = Field(None, description="Date of the company's Initial Public Offering (IPO).")
    sector: Optional[str] = Field(None, description="Sector in which the company operates.")
    industry: Optional[str] = Field(None, description="Industry classification of the company.")

# --- 1. CORE INCOME STATEMENT METRICS ---

class IncomeStatementMetrics(BaseModel):
    """
    Core metrics for the Income Statement.
    """
    net_trading_income_million_eur: Optional[float] = Field(None, description="Net Trading Income in millions of EUR.")
    other_income_million_eur: Optional[float] = Field(None, description="Other Income in millions of EUR.")
    total_income_million_eur: Optional[float] = Field(None, description="Total Income (Net Trading Income + Other Income) in millions of EUR.")
    ebitda_million_eur: Optional[float] = Field(None, description="Earnings Before Interest, Taxes, Depreciation, and Amortization in millions of EUR.")
    interest_expense_million_eur: Optional[float] = Field(None, description="Interest Expense in millions of EUR.")
    depreciation_amortisation_million_eur: Optional[float] = Field(None, description="Depreciation & Amortisation in millions of EUR.")
    profit_loss_on_equity_million_eur: Optional[float] = Field(None, description="Profit/(Loss) on equity-accounted investments in millions of EUR.")
    profit_before_tax_million_eur: Optional[float] = Field(None, description="Profit Before Tax in millions of EUR.")
    tax_expense_million_eur: Optional[float] = Field(None, description="Tax Expense in millions of EUR.")
    net_profit_million_eur: Optional[float] = Field(None, description="Net Profit (or Net Earnings) in millions of EUR.")
    basic_eps_eur: Optional[float] = Field(None, description="Basic Earnings Per Share (EPS) in EUR.")
    fully_diluted_eps_eur: Optional[float] = Field(None, description="Fully Diluted Earnings Per Share (EPS) in EUR.")
    ebitda_margin_percent: Optional[float] = Field(None, description="EBITDA Margin percentage.")

# --- 2. EXPENSE AND REVENUE BREAKDOWN METRICS ---

class OperatingExpenses(BaseModel):
    """
    Breakdown of operating expenses.
    """
    fixed_employee_expenses_million_eur: Optional[float] = Field(None, description="Fixed employee expenses in millions of EUR.")
    variable_employee_expenses_million_eur: Optional[float] = Field(None, description="Variable employee expenses in millions of EUR.")
    technology_expenses_million_eur: Optional[float] = Field(None, description="Technology expenses in millions of EUR.")
    other_expenses_million_eur: Optional[float] = Field(None, description="Other expenses in millions of EUR.")
    one_off_expenses_million_eur: Optional[float] = Field(None, description="One-off expenses in millions of EUR.")
    total_operating_expenses_million_eur: Optional[float] = Field(None, description="Total Operating Expenses in millions of EUR.")

class RevenueBreakdown(BaseModel):
    """
    Revenue broken down by region.
    The keys for the regions can be adjusted for other companies (e.g., 'North America', 'EMEA', 'APAC').
    """
    europe_million_eur: Optional[float] = Field(None, description="Revenue generated from the Europe region in millions of EUR.")
    americas_million_eur: Optional[float] = Field(None, description="Revenue generated from the Americas region in millions of EUR.")
    asia_million_eur: Optional[float] = Field(None, description="Revenue generated from the Asia region in millions of EUR.")

class InvestmentRounds(BaseModel):
    """
    Details about investment rounds.
    """
    round_name: str = Field(..., description="Name of the investment round (e.g., 'Series A', 'Seed').")
    amount_raised_million_usd: Optional[float] = Field(None, description="Amount raised in this round in millions of USD.")
    lead_investors: Optional[str] = Field(None, description="List of lead investors in this round.")
    valuation_post_money_million_usd: Optional[float] = Field(None, description="Post-money valuation after this round in millions of USD.")

# --- 4. PARENT MODEL FOR A SINGLE REPORTING PERIOD ---



class FinancialPeriodData(BaseModel):
    """
    A complete set of financial data for a single reporting period (e.g., '4Q24', 'FY2024').
    """
    period: str = Field(..., description="The reporting period (e.g., '4Q24', 'FY2024', '1Q23').")
    company_stats: Optional[CompanyStats] = Field(None, description="Basic company statistics")
    income_statement: Optional[IncomeStatementMetrics] = Field(None, description="Income statement metrics")
    operating_expenses: Optional[OperatingExpenses] = Field(None, description="Operating expenses breakdown")
    revenue_by_region: Optional[RevenueBreakdown] = Field(None, description="Revenue breakdown by region")
    investment_rounds: Optional[List[InvestmentRounds]] = Field(None, description="List of investment rounds if applicable.")
    

# --- 5. TOP-LEVEL MODEL FOR THE ENTIRE OVERVIEW ---

class FinancialOverview(BaseModel):
    """
    Container for all extracted financial data periods.
    """
    periods_data: List[FinancialPeriodData]

# --- SIMPLIFIED MODEL FOR EASIER LLM GENERATION ---

class SimpleFinancialData(BaseModel):
    """
    Simplified financial data structure for easier LLM generation.
    """
    revenue_million_eur: Optional[float] = Field(None, description="Total revenue in millions of EUR")
    profit_million_eur: Optional[float] = Field(None, description="Net profit in millions of EUR")
    employees: Optional[int] = Field(None, description="Number of employees")
    description: Optional[str] = Field(None, description="Brief description of financial highlights")

class SimpleNewsArticle(BaseModel):
    """
    Simplified news article structure.
    """
    title: str = Field(..., description="Article title")
    link: str = Field(..., description="Article URL")
    is_pdf: bool = Field(False, description="Whether the document is a PDF")
    summary: Optional[str] = Field(None, description="Brief summary of financial content")
    financial_data: Optional[FinancialOverview] = Field(None, description="Extracted financial data")

class SimpleNewsOutput(BaseModel):
    """
    Simplified output structure for news articles.
    """
    articles: List[SimpleNewsArticle] = Field(default_factory=list, description="List of news articles with financial data")