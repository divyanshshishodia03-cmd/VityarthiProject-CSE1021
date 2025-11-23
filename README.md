# VityarthiProject-CSE1021
# PERSONAL BUDGET ANALYSER
1. Problem Definition

People often struggle to track their daily expenses and end up overspending. There is a need for a simple tool that helps users record income, monitor spending, and analyse where their money goes.

2. Objectives

Track daily income and expenses

Set and monitor monthly budget limits

Provide summaries and category-wise analysis

Help users control spending and improve money management

3. Requirement Analysis
Functional Requirements

Add income/expense transactions

Set/view monthly budget

Generate monthly summary and category breakdown

Edit/delete transactions

Export data (CSV) and show graphs

Non-Functional Requirements

Usable and simple interface

Reliable data storage (SQLite)

Good performance for many transactions

Easily maintainable modular code

4. Top-Down Design / Modularization

System divided into:

Storage Module (database operations)

Budget Module (manage monthly budget)

Transaction Module (add/edit/delete/view transactions)

Report Module (summary, analysis, charts)

User Interface Module (menu-driven CLI)

5. Algorithm (Brief)

Add Transaction Algorithm

Input date, amount, category, type

Validate details

Save to database

Monthly Summary Algorithm

Retrieve all transactions for selected month

Calculate total income, total expense, balance

Display results

Category Breakdown Algorithm

Filter expenses

Group by category

Sum amounts and show

6. Implementation

Python-based program

SQLite database for storage

Matplotlib for charts

Modular classes and functions
(Full code is in pbudget.py)

7. Testing

Verified adding, editing, deleting transactions

Checked monthly summary accuracy

Verified budget exceed alert

Tested CSV export and chart generation

8. Conclusion

The Personal Budget Analyzer helps users manage finances effectively by tracking spending, analysing expenses, and maintaining budgets. The project applies key programming concepts like modular design, algorithms, and database handling in a real-world problem.
