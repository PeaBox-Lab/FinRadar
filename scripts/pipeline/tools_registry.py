"""FinRadar — Calculator registry.

Single source of truth for the generated calculator hub. Each registry entry
becomes a dedicated page under ``site/tools/`` and is rendered by
``scripts/tools.js``. The two original calculators remain bespoke because they
consume live dashboard data, but they are listed here for navigation and search.
"""

from __future__ import annotations


def field(key, label, default, unit="", *, kind="number", minimum=None,
          maximum=None, step="any", options=None, help_text=""):
    return {
        "key": key,
        "label": label,
        "default": default,
        "unit": unit,
        "kind": kind,
        "min": minimum,
        "max": maximum,
        "step": step,
        "options": options or [],
        "help": help_text,
    }


def tool(tool_id, category, title, icon, description, *, formula, guide,
         fields, outcomes, notes=None, eyebrow="Calculator"):
    return {
        "id": tool_id,
        "category": category,
        "title": title,
        "icon": icon,
        "description": description,
        "eyebrow": eyebrow,
        "formula": formula,
        "guide": guide,
        "fields": fields,
        "outcomes": outcomes,
        "notes": notes or ["Illustrative only. Confirm numbers with your lender, insurer or adviser before acting."],
        "legacy": False,
        "href": tool_id + ".html",
    }


TOOL_CATEGORIES = [
    {"id": "loans", "title": "Loans & EMI", "icon": "🏦",
     "description": "EMI, affordability, splits, schedules, prepayment and loan comparison."},
    {"id": "investments", "title": "Deposits & Returns", "icon": "📈",
     "description": "FD, RD, SIP, CAGR, compound and simple interest calculators."},
    {"id": "insurance", "title": "Insurance", "icon": "🛡️",
     "description": "Life cover, term premium and health cover adequacy."},
    {"id": "personal", "title": "Personal Finance", "icon": "🧮",
     "description": "Emergency fund, retirement, goals, budgets, inflation and net worth."},
]


LEGACY_TOOLS = [
    {
        "id": "personal-inflation",
        "category": "personal",
        "title": "Personal Inflation Rate",
        "icon": "📊",
        "description": "See how your own spending mix changes the inflation you feel.",
        "eyebrow": "Personal finance",
        "formula": "Weighted average of category sub-indices plus user shocks",
        "guide": "Adjust weights to total roughly 100%, then add a shock for any category.",
        "outcomes": ["Personal inflation rate", "Comparison with headline CPI"],
        "notes": ["Sub-indices are illustrative until live MoSPI bucket data is wired in."],
        "legacy": True,
        "href": "personal-inflation.html",
    },
    {
        "id": "salary-parity",
        "category": "personal",
        "title": "Salary Parity",
        "icon": "💼",
        "description": "Compare purchasing power across Indian cities with a cost-of-living index.",
        "eyebrow": "Personal finance",
        "formula": "Base salary × destination index ÷ source index",
        "guide": "Pick a current city and a target city, then enter your annual salary.",
        "outcomes": ["Equivalent salary", "Purchasing-power direction"],
        "notes": ["City indices are illustrative until live MoSPI data is wired in."],
        "legacy": True,
        "href": "salary-parity.html",
    },
]


TOOLS = [
    tool(
        "emi-calculator", "loans", "EMI Calculator", "💰",
        "Estimate the monthly instalment, total interest and total outgo for a home, car or personal loan.",
        eyebrow="Loans & EMI",
        formula="EMI = P × r × (1 + r)^n ÷ ((1 + r)^n − 1), where r is the monthly rate and n is months",
        guide="Enter the loan amount, annual interest rate and tenure. Change the rate to test sensitivity before signing.",
        fields=[
            field("amount", "Loan amount", 5000000, "₹", minimum=1, step=10000),
            field("rate", "Annual interest rate", 8.5, "% p.a.", minimum=0, maximum=40, step=0.05),
            field("years", "Tenure", 20, "years", minimum=1, maximum=40, step=1),
        ],
        outcomes=["Monthly EMI", "Total interest", "Total payable", "Principal share"],
    ),
    tool(
        "loan-affordability", "loans", "Loan Affordability", "🏠",
        "Work out the largest sensible loan your monthly income can support after existing obligations.",
        eyebrow="Loans & EMI",
        formula="Max EMI = income × FOIR% − existing EMIs; loan = EMI × ((1 + r)^n − 1) ÷ (r × (1 + r)^n)",
        guide="FOIR is the share of take-home income lenders allow for debt servicing. Use 35–45% as a practical band.",
        fields=[
            field("income", "Monthly take-home income", 150000, "₹", minimum=1, step=1000),
            field("existing", "Existing monthly EMIs", 15000, "₹", minimum=0, step=1000),
            field("foir", "Debt-to-income cap (FOIR)", 40, "%", minimum=5, maximum=80, step=1),
            field("rate", "Expected loan rate", 8.5, "% p.a.", minimum=0, maximum=40, step=0.05),
            field("years", "Tenure", 20, "years", minimum=1, maximum=40, step=1),
        ],
        outcomes=["Affordable EMI", "Maximum loan", "Safe borrowing range"],
    ),
    tool(
        "interest-principal-split", "loans", "Interest vs Principal Split", "🧾",
        "See how much of a chosen instalment goes to interest and how much actually reduces your loan.",
        eyebrow="Loans & EMI",
        formula="Interest = opening balance × monthly rate; principal = EMI − interest",
        guide="Try an early month and a later month to see how the mix flips in favour of principal.",
        fields=[
            field("amount", "Loan amount", 5000000, "₹", minimum=1, step=10000),
            field("rate", "Annual interest rate", 8.5, "% p.a.", minimum=0, maximum=40, step=0.05),
            field("years", "Tenure", 20, "years", minimum=1, maximum=40, step=1),
            field("month", "Instalment number", 60, "month", minimum=1, step=1),
        ],
        outcomes=["EMI", "Interest component", "Principal component", "Balance after instalment"],
    ),
    tool(
        "amortization-schedule", "loans", "EMI Schedule / Amortization", "📅",
        "Generate a full repayment schedule showing opening balance, interest, principal and closing balance.",
        eyebrow="Loans & EMI",
        formula="Monthly loop: interest = opening × r; principal = EMI − interest; closing = opening − principal",
        guide="Use yearly view for a quick snapshot and monthly view for exact instalment-level detail. Download the CSV for your records.",
        fields=[
            field("amount", "Loan amount", 5000000, "₹", minimum=1, step=10000),
            field("rate", "Annual interest rate", 8.5, "% p.a.", minimum=0, maximum=40, step=0.05),
            field("years", "Tenure", 20, "years", minimum=1, maximum=40, step=1),
            field("view", "Schedule detail", "yearly", kind="select",
                  options=[["yearly", "Yearly summary"], ["monthly", "Every month"]]),
        ],
        outcomes=["Full schedule", "Cumulative interest", "Cumulative principal", "CSV download"],
    ),
    tool(
        "prepayment-impact", "loans", "Loan Prepayment Impact", "⚡",
        "Estimate how a one-time prepayment shortens your tenure and reduces lifetime interest.",
        eyebrow="Loans & EMI",
        formula="Apply prepayment after the chosen instalment, keep EMI constant and recalculate the remaining months",
        guide="Most Indian lenders let you keep the EMI fixed and reduce the tenure. Confirm their exact rounding rules.",
        fields=[
            field("amount", "Original loan", 5000000, "₹", minimum=1, step=10000),
            field("rate", "Annual interest rate", 8.5, "% p.a.", minimum=0, maximum=40, step=0.05),
            field("years", "Original tenure", 20, "years", minimum=1, maximum=40, step=1),
            field("prepay", "One-time prepayment", 500000, "₹", minimum=0, step=10000),
            field("month", "Prepay after instalment", 60, "month", minimum=1, step=1),
        ],
        outcomes=["Interest saved", "Tenure reduction", "New payoff month", "Remaining balance"],
    ),
    tool(
        "loan-comparison", "loans", "Loan Comparison", "⚖️",
        "Compare two loan offers on EMI, total interest and all-in cost including fees.",
        eyebrow="Loans & EMI",
        formula="Compare EMI and total outgo = EMIs + processing fees",
        guide="A lower rate is not always cheaper once processing fees and tenure changes are included.",
        fields=[
            field("amount", "Loan amount", 5000000, "₹", minimum=1, step=10000),
            field("rateA", "Offer A rate", 8.5, "% p.a.", minimum=0, maximum=40, step=0.05),
            field("yearsA", "Offer A tenure", 20, "years", minimum=1, maximum=40, step=1),
            field("feeA", "Offer A fees", 50000, "₹", minimum=0, step=1000),
            field("rateB", "Offer B rate", 9.0, "% p.a.", minimum=0, maximum=40, step=0.05),
            field("yearsB", "Offer B tenure", 15, "years", minimum=1, maximum=40, step=1),
            field("feeB", "Offer B fees", 15000, "₹", minimum=0, step=1000),
        ],
        outcomes=["EMI for each offer", "Total interest", "All-in cost", "Cheaper offer"],
    ),
    tool(
        "fd-maturity", "investments", "FD Maturity Calculator", "🏦",
        "Calculate fixed-deposit maturity value, interest earned and post-tax returns.",
        eyebrow="Deposits & Returns",
        formula="A = P × (1 + r/m)^(m × years); post-tax interest = interest × (1 − tax rate)",
        guide="Use the same compounding frequency as your bank. Tax rate should reflect your marginal slab.",
        fields=[
            field("principal", "Deposit amount", 500000, "₹", minimum=1, step=10000),
            field("rate", "Annual interest rate", 7.1, "% p.a.", minimum=0, maximum=25, step=0.05),
            field("years", "Tenure", 5, "years", minimum=0.5, maximum=30, step=0.5),
            field("comp", "Compounding", "4", kind="select",
                  options=[["1", "Yearly"], ["4", "Quarterly"], ["12", "Monthly"]]),
            field("tax", "Tax rate", 10, "%", minimum=0, maximum=40, step=1),
        ],
        outcomes=["Maturity value", "Interest earned", "Effective yield", "Post-tax maturity"],
    ),
    tool(
        "rd-maturity", "investments", "RD Maturity Calculator", "🪙",
        "Estimate the maturity value of a recurring deposit with monthly contributions.",
        eyebrow="Deposits & Returns",
        formula="Each monthly instalment is compounded until maturity and summed",
        guide="Enter the amount you can deposit every month, not the annual total. Quarterly compounding is common in India.",
        fields=[
            field("monthly", "Monthly deposit", 10000, "₹", minimum=1, step=500),
            field("rate", "Annual interest rate", 7.2, "% p.a.", minimum=0, maximum=25, step=0.05),
            field("years", "Tenure", 5, "years", minimum=1, maximum=30, step=1),
            field("comp", "Compounding", "4", kind="select",
                  options=[["1", "Yearly"], ["4", "Quarterly"], ["12", "Monthly"]]),
        ],
        outcomes=["Amount invested", "Maturity value", "Interest earned", "Effective return"],
    ),
    tool(
        "sip-returns", "investments", "SIP Return Calculator", "📊",
        "Model monthly mutual-fund investments with annual step-ups and realistic compounding.",
        eyebrow="Deposits & Returns",
        formula="Monthly loop with monthly effective return = (1 + annual return)^(1/12) − 1",
        guide="Step-up the monthly amount each year to reflect salary growth. Returns are assumptions, not guarantees.",
        fields=[
            field("monthly", "Starting monthly SIP", 10000, "₹", minimum=1, step=500),
            field("years", "Investment horizon", 10, "years", minimum=1, maximum=40, step=1),
            field("return", "Expected annual return", 12, "% p.a.", minimum=0, maximum=30, step=0.5),
            field("step", "Annual step-up", 10, "%", minimum=0, maximum=50, step=1),
        ],
        outcomes=["Maturity value", "Amount invested", "Wealth gained", "Growth multiple"],
    ),
    tool(
        "cagr", "investments", "CAGR Calculator", "📈",
        "Compute the compound annual growth rate and inflation-adjusted return of an investment.",
        eyebrow="Deposits & Returns",
        formula="CAGR = (final ÷ initial)^(1 ÷ years) − 1",
        guide="Use equal start and end dates. CAGR smooths volatility, so it hides the path taken.",
        fields=[
            field("initial", "Initial investment", 100000, "₹", minimum=1, step=1000),
            field("final", "Final value", 250000, "₹", minimum=1, step=1000),
            field("years", "Years held", 5, "years", minimum=0.5, maximum=50, step=0.5),
            field("inflation", "Average inflation", 5, "%", minimum=0, maximum=20, step=0.5),
        ],
        outcomes=["CAGR", "Absolute return", "Growth multiple", "Real CAGR"],
    ),
    tool(
        "compound-interest", "investments", "Compound Interest Calculator", "🧮",
        "See how compounding and periodic contributions build a corpus over time.",
        eyebrow="Deposits & Returns",
        formula="Yearly loop: balance = balance × (1 + r/m)^m + annual contribution",
        guide="Compare yearly and monthly compounding on the same principal to see the impact of frequency.",
        fields=[
            field("principal", "Starting principal", 100000, "₹", minimum=0, step=1000),
            field("rate", "Annual rate", 10, "% p.a.", minimum=0, maximum=30, step=0.5),
            field("years", "Period", 10, "years", minimum=1, maximum=50, step=1),
            field("comp", "Compounding per year", "4", kind="select",
                  options=[["1", "Yearly"], ["2", "Half-yearly"], ["4", "Quarterly"], ["12", "Monthly"]]),
            field("contribution", "Year-end contribution", 12000, "₹", minimum=0, step=1000),
        ],
        outcomes=["Future value", "Total invested", "Interest earned", "Interest share"],
    ),
    tool(
        "simple-interest", "investments", "Simple Interest Calculator", "🧾",
        "Calculate simple interest, maturity amount and post-tax interest for short-term deposits.",
        eyebrow="Deposits & Returns",
        formula="Interest = principal × rate × days ÷ 365",
        guide="Simple interest does not compound. It is common in some short-term deposits and informal lending.",
        fields=[
            field("principal", "Principal", 100000, "₹", minimum=1, step=1000),
            field("rate", "Annual rate", 8, "% p.a.", minimum=0, maximum=30, step=0.5),
            field("days", "Number of days", 365, "days", minimum=1, maximum=36500, step=1),
            field("tax", "Tax rate", 10, "%", minimum=0, maximum=40, step=1),
        ],
        outcomes=["Interest", "Maturity amount", "Post-tax interest", "Effective annual yield"],
    ),
    tool(
        "life-cover", "insurance", "Life Cover Need Calculator", "👨‍👩‍👧",
        "Estimate how much term life cover your family needs to replace income and clear obligations.",
        eyebrow="Insurance",
        formula="Inflated family expenses + outstanding debt − liquid assets − existing cover",
        guide="Human life value is a planning estimate. Add specific goals such as child education separately.",
        fields=[
            field("income", "Annual family income", 1200000, "₹", minimum=1, step=50000),
            field("expenses", "Annual family expenses", 600000, "₹", minimum=1, step=50000),
            field("years", "Years until financial independence", 25, "years", minimum=1, maximum=40, step=1),
            field("inflation", "Expense inflation", 6, "%", minimum=0, maximum=15, step=0.5),
            field("debt", "Outstanding debt", 2500000, "₹", minimum=0, step=50000),
            field("assets", "Liquid assets available", 2000000, "₹", minimum=0, step=50000),
            field("cover", "Existing life cover", 5000000, "₹", minimum=0, step=50000),
        ],
        outcomes=["Future family needs", "Cover gap", "Suggested term cover", "Income replacement ratio"],
        notes=["This is a planning estimate, not an underwriting decision. Use a licensed adviser for final cover."],
    ),
    tool(
        "term-premium-estimator", "insurance", "Term Premium Estimator", "🛡️",
        "Get a ballpark annual premium for a term-life policy based on age, cover and lifestyle.",
        eyebrow="Insurance",
        formula="Illustrative rate per ₹1 lakh cover × age, smoker and gender factors",
        guide="Premiums vary widely by insurer and health declaration. Treat this as a budget range only.",
        fields=[
            field("age", "Current age", 35, "years", minimum=18, maximum=65, step=1),
            field("cover", "Cover amount", 10000000, "₹", minimum=100000, step=100000),
            field("term", "Policy term", 30, "years", minimum=5, maximum=40, step=1),
            field("smoker", "Smoker", "no", kind="select", options=[["no", "No"], ["yes", "Yes"]]),
            field("gender", "Gender", "male", kind="select", options=[["male", "Male"], ["female", "Female"]]),
        ],
        outcomes=["Estimated annual premium", "Estimated monthly premium", "Premium per ₹1 lakh"],
        notes=["Illustrative rates only. Actual quotes depend on medical underwriting and insurer tariffs."],
    ),
    tool(
        "health-cover-gap", "insurance", "Health Cover Gap", "🏥",
        "Check whether your family's health insurance is adequate for the city you live in.",
        eyebrow="Insurance",
        formula="Per-member base cover × family factor × condition factor − existing cover",
        guide="Employer cover is temporary and often has sub-limits. Buy a portable family floater for the gap.",
        fields=[
            field("members", "Family members", 4, "people", minimum=1, maximum=10, step=1),
            field("tier", "City tier", "metro", kind="select",
                  options=[["metro", "Metro"], ["tier2", "Tier 2"], ["tier3", "Tier 3"]]),
            field("existing", "Personal health cover", 500000, "₹", minimum=0, step=50000),
            field("employer", "Employer cover", 0, "₹", minimum=0, step=50000),
            field("condition", "Pre-existing conditions", "none", kind="select",
                  options=[["none", "None"], ["one", "One member"], ["multiple", "Multiple"]]),
        ],
        outcomes=["Recommended cover", "Cover gap", "Estimated premium range"],
        notes=["Room rent caps, co-pays and disease sub-limits matter as much as the headline sum insured."],
    ),
    tool(
        "emergency-fund", "insurance", "Emergency Fund Planner", "🛟",
        "Find the corpus you need to absorb job loss or shocks without selling investments.",
        eyebrow="Insurance",
        formula="Monthly essential expenses × target months of coverage",
        guide="Increase target months when income is variable or you have more dependents.",
        fields=[
            field("expenses", "Monthly essential expenses", 60000, "₹", minimum=1, step=1000),
            field("dependents", "Dependents", 2, "people", minimum=0, maximum=8, step=1),
            field("stability", "Income stability", "stable", kind="select",
                  options=[["stable", "Stable salaried"], ["contract", "Contract / variable"], ["business", "Business owner"]]),
            field("corpus", "Current emergency corpus", 100000, "₹", minimum=0, step=10000),
            field("monthsToBuild", "Months to build the fund", 12, "months", minimum=1, maximum=36, step=1),
        ],
        outcomes=["Target corpus", "Current coverage months", "Gap", "Monthly saving required"],
    ),
    tool(
        "retirement-corpus", "personal", "Retirement Corpus Calculator", "🌴",
        "Estimate the corpus needed at retirement and the monthly SIP to get there.",
        eyebrow="Personal Finance",
        formula="Growing-annuity need at retirement, discounted by expected return and inflation",
        guide="Use today's monthly expenses and be conservative on return. Review every year.",
        fields=[
            field("age", "Current age", 32, "years", minimum=18, maximum=70, step=1),
            field("retire", "Retirement age", 60, "years", minimum=40, maximum=75, step=1),
            field("life", "Planning until age", 85, "years", minimum=60, maximum=100, step=1),
            field("monthly", "Monthly expenses today", 60000, "₹", minimum=1, step=1000),
            field("inflation", "Inflation", 6, "%", minimum=0, maximum=15, step=0.5),
            field("return", "Expected return before retirement", 10, "% p.a.", minimum=1, maximum=20, step=0.5),
            field("corpus", "Existing retirement corpus", 1000000, "₹", minimum=0, step=50000),
        ],
        outcomes=["Corpus needed", "Annual expense at retirement", "Monthly SIP required", "Existing corpus FV"],
        notes=["This model assumes constant inflation and returns. Stress-test with lower return assumptions."],
    ),
    tool(
        "goal-savings", "personal", "Goal Savings Calculator", "🎯",
        "Work out the lumpsum or monthly investment needed for a time-bound financial goal.",
        eyebrow="Personal Finance",
        formula="Future value of lumpsum and annuity solved for the required contribution",
        guide="Set the target to the inflation-adjusted amount you expect to need, not today's sticker price.",
        fields=[
            field("target", "Goal amount", 2000000, "₹", minimum=1, step=50000),
            field("current", "Current earmarked savings", 300000, "₹", minimum=0, step=10000),
            field("years", "Years to goal", 5, "years", minimum=1, maximum=40, step=1),
            field("return", "Expected annual return", 8, "% p.a.", minimum=0, maximum=25, step=0.5),
        ],
        outcomes=["Monthly SIP needed", "Lumpsum needed today", "Shortfall without returns"],
    ),
    tool(
        "budget-split", "personal", "50/30/20 Budget Planner", "🧭",
        "Split take-home pay into needs, wants and savings with a fixed-obligation check.",
        eyebrow="Personal Finance",
        formula="Needs 50% + wants 30% + savings 20% of take-home income",
        guide="Count EMIs under needs. If needs exceed 50%, trim fixed costs before tightening savings.",
        fields=[
            field("income", "Monthly take-home", 120000, "₹", minimum=1, step=1000),
            field("fixed", "Fixed obligations", 50000, "₹", minimum=0, step=1000),
            field("goal", "Monthly savings goal", 30000, "₹", minimum=0, step=1000),
        ],
        outcomes=["Needs budget", "Wants budget", "Savings budget", "Surplus or shortfall"],
    ),
    tool(
        "inflation-adjuster", "personal", "Inflation Adjuster", "📉",
        "Convert an amount between today's money and a future year at a chosen inflation rate.",
        eyebrow="Personal Finance",
        formula="Future value = amount × (1 + inflation)^years; present value divides instead",
        guide="Use it to turn a future goal into today's rupees, or today's salary into a future equivalent.",
        fields=[
            field("amount", "Amount", 100000, "₹", minimum=0, step=1000),
            field("years", "Number of years", 10, "years", minimum=0.5, maximum=50, step=0.5),
            field("inflation", "Inflation rate", 6, "%", minimum=0, maximum=20, step=0.5),
            field("direction", "Convert to", "future", kind="select",
                  options=[["future", "Future value"], ["present", "Today's value"]]),
        ],
        outcomes=["Adjusted value", "Purchasing-power change", "Multiplier"],
    ),
    tool(
        "net-worth", "personal", "Net Worth Snapshot", "🧳",
        "Add up financial and physical assets, subtract liabilities and see your real balance sheet.",
        eyebrow="Personal Finance",
        formula="Net worth = total assets − total liabilities",
        guide="Value property conservatively and include all outstanding loans and credit-card dues.",
        fields=[
            field("cash", "Cash on hand", 200000, "₹", minimum=0, step=10000),
            field("bank", "Bank deposits", 500000, "₹", minimum=0, step=10000),
            field("funds", "Mutual funds / shares", 1100000, "₹", minimum=0, step=10000),
            field("property", "Property value", 5000000, "₹", minimum=0, step=50000),
            field("gold", "Gold and other assets", 300000, "₹", minimum=0, step=10000),
            field("homeLoan", "Home loan outstanding", 2500000, "₹", minimum=0, step=50000),
            field("otherLoan", "Other loans", 300000, "₹", minimum=0, step=10000),
            field("card", "Credit-card dues", 50000, "₹", minimum=0, step=5000),
        ],
        outcomes=["Total assets", "Total liabilities", "Net worth", "Financial asset share"],
    ),
]


ALL_TOOLS = LEGACY_TOOLS + TOOLS


def category_map():
    return {category["id"]: category for category in TOOL_CATEGORIES}


def tool_by_id(tool_id):
    for item in ALL_TOOLS:
        if item["id"] == tool_id:
            return item
    return None


def tools_by_category(category_id):
    return [item for item in ALL_TOOLS if item["category"] == category_id]


def catalog_summary():
    return {
        "total_tools": len(ALL_TOOLS),
        "generated_tools": len(TOOLS),
        "categories": len(TOOL_CATEGORIES),
    }
