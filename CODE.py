#!/usr/bin/env python3
"""
pbudget.py -- Personal Budget Analyzer (interactive CLI)

Features:
- SQLite storage (data/pbudget.db)
- Set / view monthly budget
- Add / edit / delete / list transactions (income/expense)
- Monthly summary (income, expense, balance)
- Category-wise breakdown and bar chart (matplotlib)
- Export transactions to CSV
- Simple input validation and helpful prompts

Run:
    python3 pbudget.py

Dependencies:
- Python 3.8+
- matplotlib (for charts): pip install matplotlib

This script is intentionally single-file for easy submission/run.
"""

import sqlite3
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Tuple
import csv
import sys

# plotting on demand
try:
    import matplotlib.pyplot as plt
except Exception:
    plt = None  # charts will be disabled if matplotlib isn't available

DB_DIR = "/mnt/data"
DB_PATH = os.path.join(DB_DIR, "pbudget.db")

# Ensure data directory exists
os.makedirs(DB_DIR, exist_ok=True)


@dataclass
class Transaction:
    id: Optional[int]
    date: str  # YYYY-MM-DD
    amount: float
    category: str
    type: str  # 'income' or 'expense'
    notes: Optional[str] = None


class StorageManager:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.conn = sqlite3.connect(self.db_path)
        self._create_tables()

    def _create_tables(self):
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS budget (
                id INTEGER PRIMARY KEY,
                month TEXT UNIQUE,
                income REAL,
                limit_amount REAL
            )""")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                amount REAL,
                category TEXT,
                type TEXT,
                notes TEXT
            )""")
        self.conn.commit()

    # Budget
    def set_budget(self, month: str, income: float, limit_amount: float):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO budget (id, month, income, limit_amount) VALUES ((SELECT id FROM budget WHERE month=?), ?, ?, ?)",
            (month, month, income, limit_amount),
        )
        self.conn.commit()

    def get_budget(self, month: str) -> Optional[Tuple[int, str, float, float]]:
        cur = self.conn.cursor()
        cur.execute("SELECT id, month, income, limit_amount FROM budget WHERE month=?", (month,))
        return cur.fetchone()

    # Transactions
    def add_transaction(self, t: Transaction) -> int:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO transactions (date, amount, category, type, notes) VALUES (?, ?, ?, ?, ?)",
            (t.date, t.amount, t.category, t.type, t.notes),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_transaction(self, t: Transaction):
        if t.id is None:
            raise ValueError("Transaction id required")
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE transactions SET date=?, amount=?, category=?, type=?, notes=? WHERE id=?",
            (t.date, t.amount, t.category, t.type, t.notes, t.id),
        )
        self.conn.commit()

    def delete_transaction(self, trans_id: int):
        cur = self.conn.cursor()
        cur.execute("DELETE FROM transactions WHERE id=?", (trans_id,))
        self.conn.commit()

    def list_transactions(self, month: Optional[str] = None) -> List[Transaction]:
        cur = self.conn.cursor()
        if month:
            cur.execute("SELECT id, date, amount, category, type, notes FROM transactions WHERE substr(date,1,7)=? ORDER BY date", (month,))
        else:
            cur.execute("SELECT id, date, amount, category, type, notes FROM transactions ORDER BY date")
        rows = cur.fetchall()
        return [Transaction(id=r[0], date=r[1], amount=r[2], category=r[3], type=r[4], notes=r[5]) for r in rows]

    def close(self):
        self.conn.close()


class Budget:
    def __init__(self, storage: StorageManager, month: str):
        self.storage = storage
        self.month = month

    def set(self, income: float, limit_amount: float):
        if income < 0 or limit_amount < 0:
            raise ValueError("Income and limit must be non-negative")
        self.storage.set_budget(self.month, income, limit_amount)

    def get(self):
        row = self.storage.get_budget(self.month)
        if not row:
            return None
        return {"id": row[0], "month": row[1], "income": row[2], "limit": row[3]}


class TransactionManager:
    def __init__(self, storage: StorageManager):
        self.storage = storage

    def add(self, date: str, amount: float, category: str, ttype: str, notes: Optional[str] = None) -> int:
        # basic validation
        if ttype not in ("income", "expense"):
            raise ValueError("type must be 'income' or 'expense'")
        if amount <= 0:
            raise ValueError("amount must be > 0")
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except Exception:
            raise ValueError("date must be YYYY-MM-DD")
        t = Transaction(id=None, date=date, amount=amount, category=category, type=ttype, notes=notes)
        return self.storage.add_transaction(t)

    def edit(self, t: Transaction):
        if t.id is None:
            raise ValueError("id required")
        self.storage.update_transaction(t)

    def remove(self, trans_id: int):
        self.storage.delete_transaction(trans_id)

    def list_month(self, month: str) -> List[Transaction]:
        return self.storage.list_transactions(month=month)


class ReportGenerator:
    def __init__(self, storage: StorageManager):
        self.storage = storage

    def monthly_summary(self, month: str) -> Dict[str, any]:
        txs = self.storage.list_transactions(month=month)
        total_income = sum(t.amount for t in txs if t.type == "income")
        total_expense = sum(t.amount for t in txs if t.type == "expense")
        balance = total_income - total_expense
        return {"income": total_income, "expense": total_expense, "balance": balance, "transactions": txs}

    def category_breakdown(self, month: str) -> Dict[str, float]:
        txs = self.storage.list_transactions(month=month)
        d: Dict[str, float] = {}
        for t in txs:
            if t.type == "expense":
                d[t.category] = d.get(t.category, 0.0) + t.amount
        return d

    def plot_category_breakdown(self, month: str, save_path: Optional[str] = None):
        if plt is None:
            raise RuntimeError("matplotlib is not available")
        breakdown = self.category_breakdown(month)
        if not breakdown:
            return None
        categories = list(breakdown.keys())
        amounts = [breakdown[c] for c in categories]
        plt.figure(figsize=(8,5))
        plt.bar(categories, amounts)
        plt.title(f"Category-wise Expense Breakdown ({month})")
        plt.xlabel("Category")
        plt.ylabel("Amount")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path)
            plt.close()
            return save_path
        else:
            plt.show()
            plt.close()
            return None


# ---------- Utility functions ----------

def prompt_date(prompt_text="Date (YYYY-MM-DD), leave blank for today: ") -> str:
    s = input(prompt_text).strip()
    if s == "":
        return datetime.today().strftime("%Y-%m-%d")
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return s
    except Exception:
        print("Invalid date format. Use YYYY-MM-DD.")
        return prompt_date(prompt_text)


def prompt_positive_float(prompt_text: str) -> float:
    s = input(prompt_text).strip()
    try:
        v = float(s)
        if v <= 0:
            print("Enter a positive number.")
            return prompt_positive_float(prompt_text)
        return v
    except Exception:
        print("Invalid number.")
        return prompt_positive_float(prompt_text)


def prompt_nonempty(prompt_text: str) -> str:
    s = input(prompt_text).strip()
    if s == "":
        print("Value cannot be empty.")
        return prompt_nonempty(prompt_text)
    return s


def month_from_date(date_str: str) -> str:
    # date_str like YYYY-MM-DD -> YYYY-MM
    return date_str[:7]


def print_transactions(txs: List[Transaction]):
    if not txs:
        print("No transactions found.")
        return
    print(f"{'ID':>3}  {'Date':10}  {'Type':7}  {'Category':12}  {'Amount':10}  Notes")
    print("-"*60)
    for t in txs:
        print(f"{t.id:3d}  {t.date:10}  {t.type:7}  {t.category:12}  {t.amount:10.2f}  {t.notes or ''}")


def export_transactions_csv(txs: List[Transaction], path: str):
    with open(path, "w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "date", "type", "category", "amount", "notes"])
        for t in txs:
            writer.writerow([t.id, t.date, t.type, t.category, f"{t.amount:.2f}", t.notes or ""])
    print(f"Exported {len(txs)} transactions to {path}")


# ---------- CLI Menu ----------

def main_menu():
    storage = StorageManager(DB_PATH)
    tm = TransactionManager(storage)
    print("\nPersonal Budget Analyzer (interactive CLI)")
    print("Data DB:", DB_PATH)
    print("Type the number for the action and press Enter.\n")

    while True:
        print("\nMain Menu:")
        print("1) Set / View Monthly Budget")
        print("2) Add Transaction (income/expense)")
        print("3) Edit Transaction")
        print("4) Delete Transaction")
        print("5) List Transactions for a Month")
        print("6) Monthly Summary & Category Breakdown")
        print("7) Export Transactions (CSV)")
        print("8) Plot Category Breakdown (PNG)")
        print("9) Exit")
        choice = input("Choose an option (1-9): ").strip()
        if choice == "1":
            current_month = input("Enter month (YYYY-MM), leave blank for current month: ").strip()
            if current_month == "":
                current_month = datetime.today().strftime("%Y-%m")
            budget = Budget(storage, current_month)
            info = budget.get()
            if info:
                print(f"Budget for {current_month}: income={info['income']:.2f}, limit={info['limit']:.2f}")
                ch = input("Do you want to update it? (y/N): ").strip().lower()
                if ch == "y":
                    income = prompt_positive_float("Monthly income: ")
                    limit = prompt_positive_float("Monthly limit: ")
                    budget.set(income, limit)
                    print("Budget updated.")
            else:
                print(f"No budget set for {current_month}.")
                ch = input("Do you want to create it? (y/N): ").strip().lower()
                if ch == "y":
                    income = prompt_positive_float("Monthly income: ")
                    limit = prompt_positive_float("Monthly limit: ")
                    budget.set(income, limit)
                    print("Budget created.")

        elif choice == "2":
            date = prompt_date()
            ttype = input("Type ('income' or 'expense'): ").strip().lower()
            if ttype not in ("income", "expense"):
                print("Invalid type. Must be 'income' or 'expense'.")
                continue
            amount = prompt_positive_float("Amount: ")
            category = prompt_nonempty("Category (e.g., Food, Travel, Rent): ")
            notes = input("Notes (optional): ").strip() or None
            try:
                tid = tm.add(date=date, amount=amount, category=category, ttype=ttype, notes=notes)
                print(f"Transaction added with id {tid}.")
            except Exception as e:
                print("Failed to add transaction:", e)

        elif choice == "3":
            month = input("Enter month (YYYY-MM) to list, blank for all: ").strip() or None
            txs = storage.list_transactions(month=month) if month else storage.list_transactions()
            print_transactions(txs)
            if not txs:
                continue
            try:
                tid = int(input("Enter ID of transaction to edit: ").strip())
            except Exception:
                print("Invalid id.")
                continue
            # find transaction
            t = next((x for x in txs if x.id == tid), None)
            if not t:
                print("Transaction not found.")
                continue
            print("Leave fields blank to keep current value.")
            new_date = input(f"Date [{t.date}]: ").strip() or t.date
            new_amount_s = input(f"Amount [{t.amount}]: ").strip()
            new_amount = float(new_amount_s) if new_amount_s else t.amount
            new_category = input(f"Category [{t.category}]: ").strip() or t.category
            new_type = input(f"Type ('income'/'expense') [{t.type}]: ").strip().lower() or t.type
            new_notes = input(f"Notes [{t.notes or ''}]: ").strip() or t.notes
            try:
                t_updated = Transaction(id=tid, date=new_date, amount=new_amount, category=new_category, type=new_type, notes=new_notes)
                tm.edit(t_updated)
                print("Transaction updated.")
            except Exception as e:
                print("Failed to update:", e)

        elif choice == "4":
            month = input("Enter month (YYYY-MM) to list, blank for all: ").strip() or None
            txs = storage.list_transactions(month=month) if month else storage.list_transactions()
            print_transactions(txs)
            if not txs:
                continue
            try:
                tid = int(input("Enter ID of transaction to delete: ").strip())
                confirm = input("Are you sure? (y/N): ").strip().lower()
                if confirm == "y":
                    tm.remove(tid)
                    print("Transaction deleted.")
            except Exception as e:
                print("Error deleting transaction:", e)

        elif choice == "5":
            month = input("Enter month (YYYY-MM), leave blank for current month: ").strip()
            if not month:
                month = datetime.today().strftime("%Y-%m")
            txs = storage.list_transactions(month=month)
            print(f"\nTransactions for {month}:")
            print_transactions(txs)

        elif choice == "6":
            month = input("Enter month (YYYY-MM), leave blank for current month: ").strip() or datetime.today().strftime("%Y-%m")
            rg = ReportGenerator(storage)
            summary = rg.monthly_summary(month)
            print(f"\n--- Monthly Summary ({month}) ---")
            print(f"Total Income  : {summary['income']:.2f}")
            print(f"Total Expense : {summary['expense']:.2f}")
            print(f"Balance       : {summary['balance']:.2f}")
            # Budget info
            budget = Budget(storage, month)
            binfo = budget.get()
            if binfo:
                print(f"Budget Limit  : {binfo['limit']:.2f}")
                if summary['expense'] > binfo['limit']:
                    print("ALERT: You have exceeded your budget!")
                else:
                    print("You are within your budget.")
            print("\nCategory-wise expenses:")
            breakdown = rg.category_breakdown(month)
            if not breakdown:
                print("  No expense data.")
            else:
                for cat, amt in breakdown.items():
                    print(f"  {cat:12s} : {amt:.2f}")

        elif choice == "7":
            month = input("Enter month (YYYY-MM) to export, leave blank for all: ").strip() or None
            txs = storage.list_transactions(month=month) if month else storage.list_transactions()
            path = input(f"Enter CSV filename (default: {DB_DIR}/transactions_export.csv): ").strip() or os.path.join(DB_DIR, "transactions_export.csv")
            export_transactions_csv(txs, path)

        elif choice == "8":
            if plt is None:
                print("matplotlib not installed; charts are disabled. Install matplotlib to enable charts.")
                continue
            month = input("Enter month (YYYY-MM), leave blank for current month: ").strip() or datetime.today().strftime("%Y-%m")
            rg = ReportGenerator(storage)
            default_path = os.path.join(DB_DIR, f"category_breakdown_{month}.png")
            path = input(f"Enter filename to save chart (default: {default_path}): ").strip() or default_path
            try:
                saved = rg.plot_category_breakdown(month, save_path=path)
                if saved:
                    print(f"Saved chart to {saved}")
                else:
                    print("No expense data to plot for that month.")
            except Exception as e:
                print("Failed to create chart:", e)

        elif choice == "9":
            print("Exiting. Goodbye!")
            storage.close()
            break
        else:
            print("Invalid option. Please choose 1-9.")


if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting...")
    except Exception as e:
        print("Fatal error:", e)
