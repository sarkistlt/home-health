#!/usr/bin/env python3
"""
Profitability Analysis Module

Analyzes profitability by matching Claims (revenue) with Employee Costs.
Provides overall and physician-level profitability with clear inconsistency tracking.
"""

import pandas as pd
from pathlib import Path
from difflib import SequenceMatcher
from datetime import datetime
from typing import Dict, List, Tuple, Any
import json


class ProfitabilityAnalyzer:
    """Analyzes home health profitability from claims and employee costs."""

    def __init__(self,
                 claims_path: str = "data/excel/Claim List.csv",
                 costs_path: str = "data/excel/employee_costs.xlsx"):
        self.claims_path = Path(claims_path)
        self.costs_path = Path(costs_path)
        self.claims_df = None
        self.costs_df = None
        self.matched_costs = None
        self.unmatched_costs = None
        self.overhead_costs = None

    def load_data(self) -> bool:
        """Load claims and costs data from source files."""
        try:
            self.claims_df = pd.read_csv(self.claims_path)
            self.costs_df = pd.read_excel(self.costs_path)

            # Clean up data types
            self.costs_df['Patient_Name'] = self.costs_df['Patient_Name'].astype(str).replace('nan', '')
            self.claims_df['Patient Name'] = self.claims_df['Patient Name'].astype(str)

            return True
        except Exception as e:
            print(f"Error loading data: {e}")
            return False

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize patient name for matching."""
        if pd.isna(name) or name == '' or name == 'nan':
            return ''
        name = str(name).strip().lower()
        name = name.replace('.', '').replace(',', ' ').replace('/', ' ')
        parts = name.split()
        return ' '.join(sorted(parts))

    def _build_physician_lookup(self) -> Tuple[Dict, Dict]:
        """Build lookup dictionaries from claims data."""
        self.claims_df['norm_name'] = self.claims_df['Patient Name'].apply(self.normalize_name)
        physician_lookup = self.claims_df.groupby('norm_name')['Primary Physician'].first().to_dict()
        patient_name_lookup = self.claims_df.groupby('norm_name')['Patient Name'].first().to_dict()
        return physician_lookup, patient_name_lookup

    def _categorize_cost_record(self, row: pd.Series,
                                 physician_lookup: Dict,
                                 patient_name_lookup: Dict) -> Tuple[str, str, str]:
        """Categorize a cost record as matched, unmatched, or overhead."""
        patient = str(row['Patient_Name']).strip()
        norm = row['norm_name']

        if patient == '' or patient == 'nan':
            return ('NO_PATIENT', None, None)

        # Check if it's overhead/admin keywords
        overhead_keywords = ['total', 'note', 'office', 'intake', 'pay', 'attached',
                           'october', 'expense', 'see ', 'monthly']
        if any(kw in patient.lower() for kw in overhead_keywords):
            return ('OVERHEAD', None, None)

        # Try exact match
        if norm in physician_lookup:
            return ('MATCHED', physician_lookup[norm], patient_name_lookup[norm])

        # Try fuzzy match
        best_match = None
        best_score = 0
        best_claim_name = None
        for claim_norm, physician in physician_lookup.items():
            score = SequenceMatcher(None, norm, claim_norm).ratio()
            if score > best_score and score > 0.7:
                best_score = score
                best_match = physician
                best_claim_name = patient_name_lookup[claim_norm]

        if best_match:
            return ('MATCHED', best_match, best_claim_name)

        return ('UNMATCHED', None, None)

    def analyze(self) -> Dict[str, Any]:
        """Run full profitability analysis."""
        if self.claims_df is None or self.costs_df is None:
            if not self.load_data():
                return {"error": "Failed to load data"}

        # Build lookups
        physician_lookup, patient_name_lookup = self._build_physician_lookup()

        # Normalize cost patient names
        self.costs_df['norm_name'] = self.costs_df['Patient_Name'].apply(self.normalize_name)

        # Categorize all cost records
        results = self.costs_df.apply(
            lambda row: self._categorize_cost_record(row, physician_lookup, patient_name_lookup),
            axis=1
        )
        self.costs_df['Category'] = [r[0] for r in results]
        self.costs_df['Matched_Physician'] = [r[1] for r in results]
        self.costs_df['Matched_Claim_Patient'] = [r[2] for r in results]

        # Split into categories
        self.matched_costs = self.costs_df[self.costs_df['Category'] == 'MATCHED'].copy()
        self.unmatched_costs = self.costs_df[self.costs_df['Category'] == 'UNMATCHED'].copy()
        self.overhead_costs = self.costs_df[self.costs_df['Category'].isin(['OVERHEAD', 'NO_PATIENT'])].copy()

        # Build results
        return self._build_results()

    def _build_results(self) -> Dict[str, Any]:
        """Build the complete results dictionary."""
        # Overall metrics
        total_revenue = float(self.claims_df['Paid Amount'].sum())
        total_costs = float(self.costs_df['Total_Amount'].sum())
        matched_costs_total = float(self.matched_costs['Total_Amount'].sum())
        unmatched_costs_total = float(self.unmatched_costs['Total_Amount'].sum())
        overhead_costs_total = float(self.overhead_costs['Total_Amount'].sum())

        gross_profit = total_revenue - total_costs
        profit_margin = (gross_profit / total_revenue * 100) if total_revenue > 0 else 0

        overall = {
            "total_revenue": total_revenue,
            "total_costs": total_costs,
            "matched_costs": matched_costs_total,
            "unmatched_costs": unmatched_costs_total,
            "overhead_costs": overhead_costs_total,
            "gross_profit": gross_profit,
            "profit_margin": round(profit_margin, 1),
            "total_claims": len(self.claims_df),
            "unique_patients": int(self.claims_df['Patient Name'].nunique()),
            "unique_physicians": int(self.claims_df['Primary Physician'].nunique())
        }

        # Physician-level profitability
        revenue_by_physician = self.claims_df.groupby('Primary Physician').agg({
            'Paid Amount': 'sum',
            'Claim Amount': 'sum',
            'Patient Name': 'nunique',
            'Claim Code': 'count'
        }).rename(columns={
            'Patient Name': 'patients',
            'Claim Code': 'claims',
            'Paid Amount': 'revenue',
            'Claim Amount': 'billed'
        })

        costs_by_physician = self.matched_costs.groupby('Matched_Physician')['Total_Amount'].sum()

        physician_data = []
        for physician in revenue_by_physician.index:
            row = revenue_by_physician.loc[physician]
            direct_cost = float(costs_by_physician.get(physician, 0))
            revenue = float(row['revenue'])
            profit = revenue - direct_cost
            margin = (profit / revenue * 100) if revenue > 0 else 0

            physician_data.append({
                "physician": physician,
                "revenue": revenue,
                "billed": float(row['billed']),
                "direct_costs": direct_cost,
                "profit": profit,
                "margin": round(margin, 1),
                "patients": int(row['patients']),
                "claims": int(row['claims']),
                "has_matched_costs": direct_cost > 0
            })

        # Sort by revenue descending
        physician_data.sort(key=lambda x: x['revenue'], reverse=True)

        # Unmatched patient costs (inconsistencies)
        unmatched_data = []
        for _, row in self.unmatched_costs.iterrows():
            if pd.notna(row['Total_Amount']) and row['Total_Amount'] > 0:
                unmatched_data.append({
                    "patient_name": str(row['Patient_Name']),
                    "employee": str(row['Physician']) if pd.notna(row['Physician']) else '',
                    "amount": float(row['Total_Amount']),
                    "date": str(row['Date'])[:10] if pd.notna(row['Date']) else ''
                })

        # Also include those with no amount but have patient names (for reference)
        for _, row in self.unmatched_costs.iterrows():
            if pd.isna(row['Total_Amount']) or row['Total_Amount'] == 0:
                patient = str(row['Patient_Name'])
                if patient and patient != 'nan':
                    unmatched_data.append({
                        "patient_name": patient,
                        "employee": str(row['Physician']) if pd.notna(row['Physician']) else '',
                        "amount": 0,
                        "date": str(row['Date'])[:10] if pd.notna(row['Date']) else ''
                    })

        # Sort by amount descending
        unmatched_data.sort(key=lambda x: x['amount'], reverse=True)

        # Overhead costs by employee
        overhead_data = []
        overhead_by_employee = self.overhead_costs.groupby('Physician')['Total_Amount'].sum().sort_values(ascending=False)
        for employee, amount in overhead_by_employee.items():
            overhead_data.append({
                "employee": str(employee),
                "amount": float(amount)
            })

        return {
            "overall": overall,
            "by_physician": physician_data,
            "unmatched_patients": unmatched_data,
            "overhead": overhead_data,
            "generated_at": datetime.now().isoformat()
        }

    def export_to_excel(self, output_path: str = None) -> str:
        """Export profitability analysis to Excel."""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"outputs/Profitability_Analysis_{timestamp}.xlsx"

        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Run analysis if not done
        results = self.analyze()

        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Sheet 1: Overall Summary
            overall_df = pd.DataFrame([{
                'Metric': 'Total Revenue (Paid)',
                'Amount': results['overall']['total_revenue']
            }, {
                'Metric': 'Total Costs',
                'Amount': results['overall']['total_costs']
            }, {
                'Metric': '  - Matched to Physicians',
                'Amount': results['overall']['matched_costs']
            }, {
                'Metric': '  - Unmatched Patient Costs',
                'Amount': results['overall']['unmatched_costs']
            }, {
                'Metric': '  - Overhead/Admin',
                'Amount': results['overall']['overhead_costs']
            }, {
                'Metric': 'Gross Profit',
                'Amount': results['overall']['gross_profit']
            }, {
                'Metric': 'Profit Margin (%)',
                'Amount': results['overall']['profit_margin']
            }])
            overall_df.to_excel(writer, sheet_name='Overall Summary', index=False)

            # Sheet 2: By Physician
            physician_df = pd.DataFrame(results['by_physician'])
            physician_df.columns = ['Physician', 'Revenue', 'Billed', 'Direct Costs',
                                   'Profit', 'Margin %', 'Patients', 'Claims', 'Has Matched Costs']
            physician_df.to_excel(writer, sheet_name='By Physician', index=False)

            # Sheet 3: Unmatched Patients (Inconsistencies)
            if results['unmatched_patients']:
                unmatched_df = pd.DataFrame(results['unmatched_patients'])
                unmatched_df.columns = ['Patient Name (in Costs)', 'Employee', 'Amount', 'Date']
                unmatched_df.to_excel(writer, sheet_name='Unmatched Patients', index=False)

            # Sheet 4: Overhead Costs
            if results['overhead']:
                overhead_df = pd.DataFrame(results['overhead'])
                overhead_df.columns = ['Employee/Category', 'Amount']
                overhead_df.to_excel(writer, sheet_name='Overhead Costs', index=False)

            # Format worksheets
            for sheet_name in writer.sheets:
                ws = writer.sheets[sheet_name]
                for column in ws.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    ws.column_dimensions[column_letter].width = adjusted_width

        return output_path


def main():
    """Run profitability analysis and print results."""
    analyzer = ProfitabilityAnalyzer()
    results = analyzer.analyze()

    print("=" * 70)
    print("OVERALL PROFITABILITY")
    print("=" * 70)
    o = results['overall']
    print(f"Total Revenue:        ${o['total_revenue']:>12,.2f}")
    print(f"Total Costs:          ${o['total_costs']:>12,.2f}")
    print(f"  - Matched:          ${o['matched_costs']:>12,.2f}")
    print(f"  - Unmatched:        ${o['unmatched_costs']:>12,.2f}")
    print(f"  - Overhead:         ${o['overhead_costs']:>12,.2f}")
    print(f"Gross Profit:         ${o['gross_profit']:>12,.2f}")
    print(f"Profit Margin:        {o['profit_margin']:>11.1f}%")

    print("\n" + "=" * 70)
    print("TOP 10 PHYSICIANS BY REVENUE")
    print("=" * 70)
    for p in results['by_physician'][:10]:
        cost_str = f"${p['direct_costs']:>8,.0f}" if p['direct_costs'] > 0 else "       -"
        print(f"{p['physician'][:35]:<36} ${p['revenue']:>10,.0f} {cost_str} {p['margin']:>6.1f}%")

    # Export to Excel
    output_path = analyzer.export_to_excel()
    print(f"\nExported to: {output_path}")


if __name__ == "__main__":
    main()
