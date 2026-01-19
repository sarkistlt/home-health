#!/usr/bin/env python3
"""
Home Health Pivot Analytics Engine

Recreates the exact pivot analysis from your Excel files using real PDF data.
This generates the 7 key pivot tables you need for your web application.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging
from pathlib import Path

class HomeHealthAnalytics:
    """Analytics engine for home health billing data."""

    def __init__(self):
        """Initialize the analytics engine."""
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Service cost mapping (based on industry standards)
        self.service_costs = {
            'SN': 140,   # Skilled Nursing
            'HHA': 100,  # Home Health Aide
            'PT': 175,   # Physical Therapy
            'OT': 160,   # Occupational Therapy
            'ST': 180,   # Speech Therapy
            'MSW': 125,  # Medical Social Worker
            'MEDS': 50   # Medications
        }

    def load_extracted_data(self, data_file: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load the extracted PDF data."""
        self.logger.info(f"Loading extracted data from: {data_file}")

        try:
            claims_df = pd.read_excel(data_file, sheet_name='AR Claims')
            visits_df = pd.read_excel(data_file, sheet_name='Patient Visits')

            # Clean and prepare data
            claims_df = self._clean_claims_data(claims_df)
            visits_df = self._clean_visits_data(visits_df)

            self.logger.info(f"Loaded {len(claims_df)} claims and {len(visits_df)} visits")
            return claims_df, visits_df

        except Exception as e:
            self.logger.error(f"Error loading data: {e}")
            raise

    def _clean_claims_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize claims data."""
        # Ensure numeric columns
        numeric_cols = ['SN', 'HHA', 'PT', 'OT', 'ST', 'MSW', 'MEDS', 'Total Visits',
                       'Total Amount', 'Expected Payment', 'Posted Payments', 'Net Adjust.', 'Balance']

        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Ensure date columns
        date_cols = ['Claim Period Start', 'Claim Period End']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')

        # Add calculated fields
        df['Cycle Start'] = df['Claim Period Start']
        df['Cycle End'] = df['Claim Period End']
        df['Insurance'] = df['Stat']  # Map status to insurance for compatibility

        return df

    def _clean_visits_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize visits data."""
        # Ensure numeric columns
        numeric_cols = ['Qty', 'Amount']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Ensure date columns
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')

        # Add cleaned patient name for matching
        if 'Patient Name & Number' in df.columns:
            df['Patient Name Clean'] = df['Patient Name & Number'].str.extract(r'([^(]+)')[0].str.strip()
        elif 'Patient Name' in df.columns:
            df['Patient Name Clean'] = df['Patient Name'].str.strip()

        return df

    def create_master_transformed_data(self, claims_df: pd.DataFrame, visits_df: pd.DataFrame) -> pd.DataFrame:
        """
        Create master transformed data - service-level records combining claims and visits.
        This replicates the 'Master Transformed' tab from your Excel file.
        """
        self.logger.info("Creating master transformed data...")

        service_records = []

        for _, claim in claims_df.iterrows():
            patient_name = claim['Patient Name']

            # For each service type with visits
            for service in ['SN', 'HHA', 'PT', 'OT', 'ST', 'MSW', 'MEDS']:
                if service in claim and claim[service] > 0:
                    visits = int(claim[service])
                    cost_per_visit = self.service_costs.get(service, 125)
                    total_cost = visits * cost_per_visit

                    # Find matching visits for provider information
                    matching_visits = visits_df[
                        (visits_df['Patient Name Clean'] == patient_name) &
                        (visits_df['Claim #'].astype(str) == str(claim['Claim Code']))
                    ]

                    # Get provider name from visits
                    if len(matching_visits) > 0:
                        provider = matching_visits['Caregiver'].mode()[0] if len(matching_visits['Caregiver'].mode()) > 0 else 'Unknown Provider'
                    else:
                        provider = 'Unknown Provider'

                    service_record = {
                        'Patient Name': patient_name,
                        'Cycle Start': claim['Cycle Start'],
                        'Cycle End': claim['Cycle End'],
                        'Claim Code': claim['Claim Code'],
                        'Insurance': claim['Insurance'],
                        'Service Type': service,
                        'Provider Name': provider,
                        'Service Visits': visits,
                        'Cost per Visit': cost_per_visit,
                        'Total Cost': total_cost,
                        'File Status': 'Processed',
                        'Claim Amount': claim['Total Amount'],
                        'Total Amount Billed': claim['Total Amount'],
                        'Expected Payment': claim['Expected Payment'],
                        'Posted Payments': claim['Posted Payments'],
                        'Net Adjust.': claim['Net Adjust.'],
                        'Balance': claim['Balance']
                    }

                    service_records.append(service_record)

        master_df = pd.DataFrame(service_records)
        self.logger.info(f"Created {len(master_df)} master service records")
        return master_df

    def create_revenue_by_claim(self, claims_df: pd.DataFrame) -> pd.DataFrame:
        """Create Revenue by Claim analysis."""
        self.logger.info("Creating Revenue by Claim analysis...")

        revenue_df = claims_df.groupby(['Patient Name', 'Claim Code']).agg({
            'Cycle Start': 'first',
            'Cycle End': 'first',
            'Insurance': 'first',
            'Total Amount': 'sum',
            'Expected Payment': 'sum',
            'Posted Payments': 'sum',
            'Balance': 'sum',
            'Net Adjust.': 'sum'
        }).reset_index()

        revenue_df.columns = [
            'Patient Name', 'Claim Code', 'Cycle Start', 'Cycle End',
            'Insurance', 'Total Amount Billed', 'Expected Payment',
            'Actual Payment Received', 'Remaining Balance', 'Net Adjustment'
        ]

        # Add placeholder date columns
        revenue_df['Payment Requested At'] = pd.NaT
        revenue_df['Payment Received At'] = pd.NaT
        revenue_df['Days to Payment'] = 0

        return revenue_df

    def create_service_costs(self, master_df: pd.DataFrame) -> pd.DataFrame:
        """Create Service Costs analysis."""
        self.logger.info("Creating Service Costs analysis...")

        service_costs_df = master_df[[
            'Patient Name', 'Cycle Start', 'Cycle End', 'Service Type',
            'Provider Name', 'Service Visits', 'Cost per Visit', 'Total Cost',
            'File Status', 'Claim Amount'
        ]].copy()

        return service_costs_df

    def create_profitability_by_patient(self, master_df: pd.DataFrame) -> pd.DataFrame:
        """Create Profitability by Patient analysis."""
        self.logger.info("Creating Profitability by Patient analysis...")

        profit_df = master_df.groupby(['Patient Name', 'Cycle Start', 'Cycle End']).agg({
            'Total Amount Billed': 'first',
            'Posted Payments': 'first',
            'Total Cost': 'sum'
        }).reset_index()

        profit_df.columns = [
            'Patient Name', 'Cycle Start', 'Cycle End',
            'Total Revenue Billed', 'Total Revenue Received', 'Total Cost'
        ]

        profit_df['Gross Profit'] = profit_df['Total Revenue Received'] - profit_df['Total Cost']
        profit_df['Gross Margin %'] = (
            (profit_df['Gross Profit'] / profit_df['Total Revenue Billed']) * 100
        ).round(1).fillna(0)

        return profit_df

    def create_provider_performance(self, master_df: pd.DataFrame) -> pd.DataFrame:
        """Create Provider Performance analysis."""
        self.logger.info("Creating Provider Performance analysis...")

        provider_df = master_df.groupby(['Provider Name', 'Service Type']).agg({
            'Service Visits': 'sum',
            'Total Cost': 'sum',
            'Cost per Visit': 'mean',
            'Patient Name': 'nunique'
        }).reset_index()

        provider_df.columns = [
            'Provider Name', 'Service Type', 'Total Visits',
            'Total Cost', 'Avg Cost per Visit', '# of Patients Served'
        ]

        provider_df['Avg Cost per Patient'] = (
            provider_df['Total Cost'] / provider_df['# of Patients Served']
        ).round(2)

        return provider_df

    def create_code_performance(self, claims_df: pd.DataFrame) -> pd.DataFrame:
        """Create Code Performance analysis."""
        self.logger.info("Creating Code Performance analysis...")

        code_df = claims_df.groupby('Claim Code').agg({
            'Total Amount': ['count', 'mean'],
            'Expected Payment': 'mean',
            'Posted Payments': ['mean', 'sum'],
            'Net Adjust.': 'mean'
        }).round(2)

        code_df.columns = [
            'Total Claims', 'Avg Billed Amount', 'Avg Expected Payment',
            'Avg Actual Payment', 'Total Received', 'Avg Adjustment'
        ]

        code_df['Avg % Collected'] = (
            (code_df['Avg Actual Payment'] / code_df['Avg Expected Payment']) * 100
        ).round(1).fillna(0)

        code_df.reset_index(inplace=True)
        return code_df

    def create_service_cost_summary(self, master_df: pd.DataFrame) -> pd.DataFrame:
        """Create Service Cost Summary analysis."""
        self.logger.info("Creating Service Cost Summary analysis...")

        service_summary_df = master_df.groupby('Service Type').agg({
            'Service Visits': 'sum',
            'Total Cost': 'sum',
            'Cost per Visit': 'mean'
        }).reset_index()

        service_summary_df.columns = [
            'Service Type', 'Total Visits', 'Total Cost', 'Avg Cost per Visit'
        ]

        service_summary_df['% of Total Cost'] = (
            (service_summary_df['Total Cost'] / service_summary_df['Total Cost'].sum()) * 100
        ).round(1)

        return service_summary_df

    def create_insurance_payer_performance(self, claims_df: pd.DataFrame) -> pd.DataFrame:
        """Create Insurance Payer Performance analysis."""
        self.logger.info("Creating Insurance Payer Performance analysis...")

        insurance_df = claims_df.groupby('Insurance').agg({
            'Claim Code': 'count',
            'Expected Payment': 'mean',
            'Posted Payments': 'mean',
            'Net Adjust.': 'mean'
        }).round(2)

        insurance_df.columns = [
            'Total Claims', 'Avg Expected Payment',
            'Avg Actual Payment', 'Avg Adjustment'
        ]

        insurance_df['Avg Days to Payment'] = 0  # Placeholder
        insurance_df['Avg % Collected'] = (
            (insurance_df['Avg Actual Payment'] / insurance_df['Avg Expected Payment']) * 100
        ).round(1).fillna(0)

        # Reorder columns
        insurance_df = insurance_df[[
            'Total Claims', 'Avg Days to Payment', 'Avg Expected Payment',
            'Avg Actual Payment', 'Avg Adjustment', 'Avg % Collected'
        ]]

        insurance_df.reset_index(inplace=True)
        insurance_df.rename(columns={'Insurance': 'Insurance'}, inplace=True)
        return insurance_df

    def generate_all_analytics(self, claims_df: pd.DataFrame, visits_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """Generate all pivot analytics tables."""
        self.logger.info("Generating all analytics tables...")

        # Create master transformed data first
        master_df = self.create_master_transformed_data(claims_df, visits_df)

        # Generate all pivot tables
        analytics = {
            'Original Claims': claims_df,
            'Original Visits': visits_df,
            'Master Transformed': master_df,
            'Revenue by Claim': self.create_revenue_by_claim(claims_df),
            'Service Costs': self.create_service_costs(master_df),
            'Profitability by Patient': self.create_profitability_by_patient(master_df),
            'Provider Performance': self.create_provider_performance(master_df),
            'Code Performance': self.create_code_performance(claims_df),
            'Service Cost Summary': self.create_service_cost_summary(master_df),
            'Insurance Payer Performance': self.create_insurance_payer_performance(claims_df)
        }

        # Log summary of each table
        for name, df in analytics.items():
            self.logger.info(f"{name}: {len(df)} records")

        return analytics

    def save_analytics(self, analytics: Dict[str, pd.DataFrame], output_dir: str = "analytics_output") -> str:
        """Save all analytics to Excel file."""
        from pathlib import Path

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = output_path / f"home_health_analytics_{timestamp}.xlsx"

        with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
            workbook = writer.book

            # Define formats
            money_format = workbook.add_format({'num_format': '$#,##0.00'})
            percent_format = workbook.add_format({'num_format': '0.0%'})
            date_format = workbook.add_format({'num_format': 'mm/dd/yyyy'})

            for sheet_name, df in analytics.items():
                df.to_excel(writer, sheet_name=sheet_name, index=False)

                # Format columns
                worksheet = writer.sheets[sheet_name]
                for col_num, column in enumerate(df.columns):
                    # Auto-adjust column width
                    max_length = max(len(str(column)), df[column].astype(str).str.len().max())
                    worksheet.set_column(col_num, col_num, min(max_length + 2, 50))

                    # Apply specific formatting
                    if any(word in column.lower() for word in ['amount', 'cost', 'payment', 'balance']):
                        worksheet.set_column(col_num, col_num, None, money_format)
                    elif 'margin' in column.lower() or '% collected' in column.lower():
                        worksheet.set_column(col_num, col_num, None, percent_format)
                    elif 'date' in column.lower() or 'start' in column.lower() or 'end' in column.lower():
                        worksheet.set_column(col_num, col_num, None, date_format)

        self.logger.info(f"Analytics saved to: {output_file}")
        return str(output_file)

    def get_summary_metrics(self, analytics: Dict[str, pd.DataFrame]) -> Dict:
        """Get summary metrics for the dashboard."""
        claims_df = analytics['Original Claims']
        visits_df = analytics['Original Visits']
        master_df = analytics['Master Transformed']

        summary = {
            'total_patients': claims_df['Patient Name'].nunique(),
            'total_claims': len(claims_df),
            'total_visits': len(visits_df),
            'total_billed': claims_df['Total Amount'].sum(),
            'total_collected': claims_df['Posted Payments'].sum(),
            'total_outstanding': claims_df['Balance'].sum(),
            'collection_rate': (claims_df['Posted Payments'].sum() / claims_df['Total Amount'].sum() * 100) if claims_df['Total Amount'].sum() > 0 else 0,
            'avg_claim_amount': claims_df['Total Amount'].mean(),
            'total_service_cost': master_df['Total Cost'].sum(),
            'gross_profit': claims_df['Posted Payments'].sum() - master_df['Total Cost'].sum(),
            'profit_margin': ((claims_df['Posted Payments'].sum() - master_df['Total Cost'].sum()) / claims_df['Posted Payments'].sum() * 100) if claims_df['Posted Payments'].sum() > 0 else 0
        }

        return summary


def main():
    """Main function to test the analytics engine."""
    # Find the most recent extracted data file
    data_files = list(Path("extracted_data").glob("extracted_home_health_data_*.xlsx"))
    if not data_files:
        print("❌ No extracted data files found. Run home_health_extractor.py first.")
        return

    latest_file = max(data_files, key=lambda x: x.stat().st_mtime)

    # Initialize analytics engine
    analytics_engine = HomeHealthAnalytics()

    try:
        # Load data
        claims_df, visits_df = analytics_engine.load_extracted_data(str(latest_file))

        # Generate all analytics
        analytics = analytics_engine.generate_all_analytics(claims_df, visits_df)

        # Save analytics
        output_file = analytics_engine.save_analytics(analytics)

        # Get summary metrics
        summary = analytics_engine.get_summary_metrics(analytics)

        print("\n🎉 ANALYTICS GENERATION COMPLETE!")
        print("="*60)
        print(f"📊 Total Patients: {summary['total_patients']}")
        print(f"📄 Total Claims: {summary['total_claims']}")
        print(f"🏥 Total Visits: {summary['total_visits']}")
        print(f"💰 Total Billed: ${summary['total_billed']:,.2f}")
        print(f"💵 Total Collected: ${summary['total_collected']:,.2f}")
        print(f"📈 Collection Rate: {summary['collection_rate']:.1f}%")
        print(f"⚖️ Outstanding Balance: ${summary['total_outstanding']:,.2f}")
        print(f"💼 Gross Profit: ${summary['gross_profit']:,.2f}")
        print(f"📊 Profit Margin: {summary['profit_margin']:.1f}%")
        print(f"📁 Analytics File: {output_file}")

        return analytics, summary

    except Exception as e:
        print(f"❌ Error: {e}")
        return None, None


if __name__ == "__main__":
    main()