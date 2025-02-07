import streamlit as st
from decimal import Decimal, InvalidOperation
import re
from datetime import datetime, timedelta
import json
import os

# File to store settings
SETTINGS_FILE = "app_settings.json"

def load_settings():
    """Load settings from file"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                settings = json.load(f)
                return settings
        except Exception:
            return get_default_settings()
    return get_default_settings()

def save_settings():
    """Save current settings to file"""
    settings = {
        'currency': st.session_state.currency,
        'theme': st.session_state.theme,
        'notifications_enabled': st.session_state.notifications_enabled,
        'critical_warning_enabled': st.session_state.critical_warning_enabled,
        'expense_history': [
            {**expense, 'date': expense['date'].isoformat()} 
            for expense in st.session_state.expense_history
        ]
    }
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f)
    except Exception as e:
        st.error(f"Failed to save settings: {str(e)}")

def get_default_settings():
    """Return default settings"""
    return {
        'currency': 'USD',
        'theme': 'light',
        'notifications_enabled': True,
        'critical_warning_enabled': True,
        'expense_history': []
    }

# Page configuration
st.set_page_config(
    page_title="Budget & Expense Tracker",
    page_icon="🧮",
    layout="centered"
)

# Initialize session state from stored settings
if 'initialized' not in st.session_state:
    settings = load_settings()
    st.session_state.page = 'main_menu'
    st.session_state.currency = settings['currency']
    st.session_state.theme = settings['theme']
    st.session_state.notifications_enabled = settings['notifications_enabled']
    st.session_state.critical_warning_enabled = settings['critical_warning_enabled']
    st.session_state.budget_type = None
    st.session_state.budget_amount = None
    st.session_state.budget_start_date = None
    st.session_state.expenses = []
    st.session_state.expense_history = [
        {**expense, 'date': datetime.fromisoformat(expense['date'])}
        for expense in settings['expense_history']
    ]
    st.session_state.initialized = True

# Currency configuration
CURRENCIES = {
    'USD': {'symbol': '$', 'name': 'US Dollar'},
    'EUR': {'symbol': '€', 'name': 'Euro'},
    'JPY': {'symbol': '¥', 'name': 'Japanese Yen'},
    'GBP': {'symbol': '£', 'name': 'British Pound'},
    'CNY': {'symbol': '¥', 'name': 'Chinese Yuan'},
}

EXPENSE_CATEGORIES = [
    'Food',
    'Gas',
    'Utilities',
    'Rent/Mortgage',
    'Transportation',
    'Entertainment',
    'Healthcare',
    'Shopping',
    'Other'
]

# Custom CSS
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
    }
    .menu-button {
        margin: 10px 0;
    }
    .currency-selector {
        margin-bottom: 20px;
    }
    .budget-status {
        padding: 1.5rem;
        margin: 1rem 0;
        border-radius: 1rem;
        text-align: center;
    }
    .budget-ok { background-color: #d4edda; color: #155724; }
    .budget-warning { background-color: #fff3cd; color: #856404; }
    .budget-exceeded { background-color: #f8d7da; color: #721c24; }
    .critical-warning { background-color: #dc3545; color: white; }
    .remaining-budget {
        font-size: clamp(1.5rem, 5vw, 2.5rem);
        font-weight: bold;
        margin: 1rem 0;
    }
    .notification {
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0.5rem;
        font-weight: bold;
    }
    /* Mobile responsive adjustments */
    @media (max-width: 768px) {
        .budget-status {
            padding: 1rem;
        }
        .notification {
            padding: 0.75rem;
        }
        .stButton>button {
            padding: 0.5rem;
            font-size: 0.9rem;
        }
    }
    </style>
""", unsafe_allow_html=True)

def format_amount(amount, currency='USD'):
    """Format amount with currency symbol"""
    symbol = CURRENCIES[currency]['symbol']
    return f"{symbol}{amount:.2f}"

def check_budget_reset():
    """Check if budget needs to be reset based on the interval"""
    if not st.session_state.budget_start_date:
        return

    now = datetime.now()
    start_date = st.session_state.budget_start_date

    reset_needed = False
    if st.session_state.budget_type == "Daily":
        reset_needed = (now.date() > start_date.date())
    elif st.session_state.budget_type == "Weekly":
        reset_needed = (now - start_date).days >= 7
    elif st.session_state.budget_type == "Monthly":
        reset_needed = (now.year > start_date.year or 
                       (now.year == start_date.year and now.month > start_date.month))
    elif st.session_state.budget_type == "Yearly":
        reset_needed = now.year > start_date.year

    if reset_needed:
        st.session_state.budget_start_date = now
        st.session_state.expenses = []

def show_budget_notification(remaining_budget):
    """Show budget notification if enabled"""
    if not st.session_state.notifications_enabled:
        return

    if remaining_budget <= 0:
        st.markdown("""
            <div class="notification critical-warning">
                ⚠️ Warning: Your budget is depleted! Consider adjusting your spending or setting a new budget.
            </div>
        """, unsafe_allow_html=True)
    elif remaining_budget <= (st.session_state.budget_amount * Decimal('0.01')) and st.session_state.critical_warning_enabled:
        st.markdown("""
            <div class="notification critical-warning">
                ⚠️ Critical Warning: Less than 1% of your budget remaining!
            </div>
        """, unsafe_allow_html=True)
    elif remaining_budget < (st.session_state.budget_amount * Decimal('0.2')):
        st.markdown("""
            <div class="notification" style="background-color: #ffc107; color: black;">
                ⚠️ Warning: Less than 20% of your budget remaining!
            </div>
        """, unsafe_allow_html=True)

def main_menu():
    st.title("💰 Budget & Expense Manager")

    # Top bar with settings
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("⚙️ Settings"):
            st.session_state.page = 'settings'

    # Currency selector
    st.markdown("<div class='currency-selector'>", unsafe_allow_html=True)
    currency = st.selectbox(
        "Select your currency:",
        options=list(CURRENCIES.keys()),
        format_func=lambda x: f"{x} ({CURRENCIES[x]['symbol']}) - {CURRENCIES[x]['name']}",
        index=list(CURRENCIES.keys()).index(st.session_state.currency)
    )
    if currency != st.session_state.currency:
        st.session_state.currency = currency
        save_settings()
    st.markdown("</div>", unsafe_allow_html=True)

    # Add history button to main menu
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📊 Budget Tracker", key="budget_btn"):
            st.session_state.page = 'budget'
    with col2:
        if st.button("🧮 Expense Calculator", key="calculator_btn"):
            st.session_state.page = 'calculator'
    with col3:
        if st.button("📈 Cost History", key="history_btn"):
            st.session_state.page = 'history'

def settings():
    st.title("⚙️ Settings")

    # Theme settings
    st.subheader("🎨 Appearance")
    theme = st.select_slider(
        "Theme Mode",
        options=['light', 'dark'],
        value=st.session_state.theme
    )
    if theme != st.session_state.theme:
        st.session_state.theme = theme
        save_settings()
        st.rerun()

    # Notification settings
    st.subheader("🔔 Notifications")

    notifications_enabled = st.toggle(
        "Enable Budget Notifications",
        value=st.session_state.notifications_enabled,
        help="Receive notifications when your budget is running low or depleted."
    )
    if notifications_enabled != st.session_state.notifications_enabled:
        st.session_state.notifications_enabled = notifications_enabled
        save_settings()

    if st.session_state.notifications_enabled:
        critical_warning_enabled = st.toggle(
            "Enable Critical (1%) Warning",
            value=st.session_state.critical_warning_enabled,
            help="Get additional warning when budget falls below 1%"
        )
        if critical_warning_enabled != st.session_state.critical_warning_enabled:
            st.session_state.critical_warning_enabled = critical_warning_enabled
            save_settings()

def budget_tracker():
    st.title("📊 Budget Tracker")

    # Use columns for better mobile layout
    col1, col2 = st.columns([3, 1])
    with col2:
        notifications_status = "🔔" if st.session_state.notifications_enabled else "🔕"
        if st.button(f"{notifications_status} Notifications"):
            st.session_state.page = 'settings'
            st.rerun()

    # Check for budget reset
    if st.session_state.budget_type:
        check_budget_reset()

    if not st.session_state.budget_type:
        budget_type = st.selectbox(
            "Select budget period:",
            ["Daily", "Weekly", "Monthly", "Yearly"],
            key="budget_type_select"
        )

        budget_amount = st.text_input(
            f"Enter your {budget_type.lower()} budget ({CURRENCIES[st.session_state.currency]['symbol']})",
            placeholder="0.00"
        )

        if st.button("Set Budget"):
            try:
                amount = Decimal(re.sub(r'[^\d.]', '', budget_amount))
                if amount <= 0:
                    st.error("Please enter a positive budget amount.")
                else:
                    st.session_state.budget_type = budget_type
                    st.session_state.budget_amount = amount
                    st.session_state.budget_start_date = datetime.now()
                    st.rerun()
            except (InvalidOperation, ValueError):
                st.error("Please enter a valid budget amount.")
    else:
        # Display budget status
        total_expenses = sum(expense['amount'] for expense in st.session_state.expenses)
        remaining_budget = st.session_state.budget_amount - total_expenses

        status_class = "budget-ok"
        if remaining_budget < (st.session_state.budget_amount * Decimal('0.2')):
            status_class = "budget-warning"
        if remaining_budget < 0:
            status_class = "budget-exceeded"

        # Show notification if needed
        show_budget_notification(remaining_budget)

        # Large remaining budget display
        st.markdown(f"""
            <div class="budget-status {status_class}">
                <h4>Remaining {st.session_state.budget_type} Budget</h4>
                <div class="remaining-budget">
                    {format_amount(remaining_budget, st.session_state.currency)}
                </div>
                <p>Total Budget: {format_amount(st.session_state.budget_amount, st.session_state.currency)}</p>
                <p>Total Expenses: {format_amount(total_expenses, st.session_state.currency)}</p>
                <p>Next Reset: {get_next_reset_date()}</p>
            </div>
        """, unsafe_allow_html=True)

        # Add new expense
        st.subheader("Add New Expense")
        category = st.selectbox("Category", EXPENSE_CATEGORIES)
        amount = st.text_input(f"Amount ({CURRENCIES[st.session_state.currency]['symbol']})", placeholder="0.00")
        description = st.text_input("Description (optional)")

        if st.button("Add Expense"):
            try:
                expense_amount = Decimal(re.sub(r'[^\d.]', '', amount))
                if expense_amount <= 0:
                    st.error("Please enter a positive amount.")
                else:
                    add_expense(expense_amount, description, category)
                    st.rerun()
            except (InvalidOperation, ValueError):
                st.error("Please enter a valid amount.")

        # Display expense history (moved to separate function)
        if st.session_state.expenses:
            st.subheader("Expense History")
            for expense in reversed(st.session_state.expenses):
                st.markdown(f"""
                    <div style="padding: 0.5rem; border-bottom: 1px solid #eee;">
                        <p><strong>{expense['date'].strftime('%Y-%m-%d %H:%M')}</strong></p>
                        <p>{expense['category']}: {expense['description']}</p>
                        <p style="color: #dc3545;">Amount: {format_amount(expense['amount'], st.session_state.currency)}</p>
                    </div>
                """, unsafe_allow_html=True)

        if st.button("Reset Budget"):
            st.session_state.budget_type = None
            st.session_state.budget_amount = None
            st.session_state.budget_start_date = None
            st.session_state.expenses = []
            st.rerun()

def get_next_reset_date():
    """Calculate the next budget reset date"""
    if not st.session_state.budget_start_date:
        return "N/A"

    start_date = st.session_state.budget_start_date
    if st.session_state.budget_type == "Daily":
        next_reset = start_date + timedelta(days=1)
    elif st.session_state.budget_type == "Weekly":
        next_reset = start_date + timedelta(days=7)
    elif st.session_state.budget_type == "Monthly":
        next_month = start_date.month + 1
        next_year = start_date.year + (next_month > 12)
        next_month = (next_month - 1) % 12 + 1
        next_reset = start_date.replace(year=next_year, month=next_month)
    else:  # Yearly
        next_reset = start_date.replace(year=start_date.year + 1)

    return next_reset.strftime("%Y-%m-%d")

def expense_calculator():
    st.title("🧮 Expense Calculator")

    expense_type = st.selectbox(
        "Select expense type:",
        EXPENSE_CATEGORIES,
        key="calc_expense_type"
    )

    if expense_type == "Food":
        col1, col2 = st.columns(2)
        with col1:
            item_price = st.text_input(
                f"Price per item ({CURRENCIES[st.session_state.currency]['symbol']})",
                placeholder="0.00"
            )
        with col2:
            quantity = st.text_input("Quantity", placeholder="1")

        price = validate_decimal_input(item_price)
        qty = validate_decimal_input(quantity)

        if price is not None and qty is not None:
            if price < 0 or qty < 0:
                st.error("Please enter positive values only.")
            else:
                total = price * qty
                st.success(f"Total food expense: {format_amount(total, st.session_state.currency)}")

                if st.button("Add to Budget"):
                    add_expense(total, f"Food expense - {qty} items at {format_amount(price, st.session_state.currency)} each", expense_type)
                    st.rerun()
    else:
        col1, col2 = st.columns(2)
        with col1:
            price_per_gallon = st.text_input(
                f"Price per gallon ({CURRENCIES[st.session_state.currency]['symbol']})",
                placeholder="0.00"
            )
        with col2:
            gallons = st.text_input("Number of gallons", placeholder="1.0")

        price = validate_decimal_input(price_per_gallon)
        gal = validate_decimal_input(gallons)

        if price is not None and gal is not None:
            if price < 0 or gal < 0:
                st.error("Please enter positive values only.")
            else:
                total = price * gal
                st.success(f"Total gas expense: {format_amount(total, st.session_state.currency)}")

                if st.button("Add to Budget"):
                    add_expense(total, f"Gas expense - {gal} gallons at {format_amount(price, st.session_state.currency)}/gallon", expense_type)
                    st.rerun()

def validate_decimal_input(value):
    if not value:
        return None
    try:
        cleaned_value = re.sub(r'[^\d.]', '', value)
        return Decimal(cleaned_value)
    except (InvalidOperation, ValueError):
        return None

def add_expense(amount, description, category):
    """Add an expense to both current period and history"""
    expense = {
        'date': datetime.now(),
        'amount': amount,
        'description': description,
        'category': category,
        'currency': st.session_state.currency,
        'budget_type': st.session_state.budget_type,
        'budget_period': f"{st.session_state.budget_start_date.strftime('%Y-%m-%d')} to {get_next_reset_date()}"
    }

    if st.session_state.budget_type:
        st.session_state.expenses.append(expense)
        st.session_state.expense_history.append(expense)
        save_settings()


def expense_history():
    st.title("📈 Cost History Analysis")

    # Filtering options
    st.subheader("Filter Options")
    col1, col2 = st.columns(2)

    with col1:
        selected_category = st.selectbox(
            "Category",
            ["All"] + EXPENSE_CATEGORIES
        )

    with col2:
        date_range = st.selectbox(
            "Time Period",
            ["Last 7 days", "Last 30 days", "Last 3 months", "All time"]
        )

    # Filter expenses based on selection
    filtered_expenses = st.session_state.expense_history.copy()
    if selected_category != "All":
        filtered_expenses = [e for e in filtered_expenses if e['category'] == selected_category]

    now = datetime.now()
    if date_range == "Last 7 days":
        filtered_expenses = [e for e in filtered_expenses if (now - e['date']).days <= 7]
    elif date_range == "Last 30 days":
        filtered_expenses = [e for e in filtered_expenses if (now - e['date']).days <= 30]
    elif date_range == "Last 3 months":
        filtered_expenses = [e for e in filtered_expenses if (now - e['date']).days <= 90]

    # Display summary statistics
    if filtered_expenses:
        total_spent = sum(e['amount'] for e in filtered_expenses)
        avg_per_day = total_spent / max(1, (now - min(e['date'] for e in filtered_expenses)).days)

        st.markdown(f"""
            <div class="budget-status budget-ok">
                <h4>Spending Summary</h4>
                <div class="remaining-budget">
                    {format_amount(total_spent, st.session_state.currency)}
                </div>
                <p>Total Expenses: {len(filtered_expenses)}</p>
                <p>Average per day: {format_amount(avg_per_day, st.session_state.currency)}</p>
            </div>
        """, unsafe_allow_html=True)

        # Display expense history with enhanced details
        st.subheader("Detailed History")
        for expense in sorted(filtered_expenses, key=lambda x: x['date'], reverse=True):
            st.markdown(f"""
                <div style="padding: 1rem; border: 1px solid #eee; border-radius: 0.5rem; margin: 0.5rem 0;">
                    <p><strong>{expense['date'].strftime('%Y-%m-%d %H:%M')}</strong></p>
                    <p>Category: {expense['category']}</p>
                    <p>{expense['description']}</p>
                    <p>Amount: {format_amount(expense['amount'], expense['currency'])}</p>
                    <p style="color: #666;">Budget Period: {expense['budget_period']}</p>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No expenses found for the selected filters.")


# Navigation bar
col1, col2, col3 = st.columns([1, 2, 1])
with col1:
    if st.session_state.page not in ['main_menu', 'settings']:
        if st.button("← Back to Menu"):
            st.session_state.page = 'main_menu'
            st.rerun()
    elif st.session_state.page == 'settings':
        if st.button("← Back"):
            st.session_state.page = 'main_menu'
            st.rerun()

# Main content
if st.session_state.page == 'main_menu':
    main_menu()
elif st.session_state.page == 'budget':
    budget_tracker()
elif st.session_state.page == 'settings':
    settings()
elif st.session_state.page == 'history':
    expense_history()
else:
    expense_calculator()

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666;'>"
    "Made with ❤️ using Streamlit"
    "</div>",
    unsafe_allow_html=True
)