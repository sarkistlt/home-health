import pandas as pd
import numpy as np
from datetime import datetime
import sys
from pathlib import Path

#home health

def process_home_health_post_transform():
    """Processor that creates exact tab structure with specified columns"""
    
    print("=" * 70)
    print("HOME HEALTH POST-TRANSFORM PROCESSOR")
    print("=" * 70)
    
    # File names
    claims_file = 'sample_claims_data.xlsx'
    visits_file = 'sample_visits_data.xlsx'
    
    # Check if files exist
    if not Path(claims_file).exists() or not Path(visits_file).exists():
        print(f"\n⚠️  Sample files not found!")
        print(f"Please run 'generate_sample_data.py' first")
        return
    
    # Load data
    print(f"\n📂 Loading data files...")
    claims_df = pd.read_excel(claims_file)
    visits_df = pd.read_excel(visits_file)
    print(f"  ✓ Loaded {len(claims_df)} claims and {len(visits_df)} visits")
    
    # Clean numeric columns
    numeric_cols = ['SN', 'HHA', 'PT', 'OT', 'ST', 'MSW', 'MEDS', 'Total Visits',
                   'Total Amount', 'Expected Payment', 'Posted Payments', 'Net Adjust.', 'Balance']
    for col in numeric_cols:
        if col in claims_df.columns:
            claims_df[col] = pd.to_numeric(claims_df[col], errors='coerce').fillna(0)
    
    # Parse dates from claim period
    def parse_claim_dates(period):
        try:
            parts = period.split(' - ')
            start = datetime.strptime(parts[0], '%m/%d/%y')
            end = datetime.strptime(parts[1], '%m/%d/%y')
            return start, end
        except:
            return None, None
    
    claims_df[['Cycle Start', 'Cycle End']] = claims_df['Claim Period'].apply(
        lambda x: pd.Series(parse_claim_dates(x))
    )
    
    # Extract patient name from visits
    visits_df['Patient Name Clean'] = visits_df['Patient Name & Number'].str.extract(r'([^(]+)')[0].str.strip()
    
    # Create master service-level data
    print("\n🔄 Creating service-level records...")
    service_records = []
    
    for _, claim in claims_df.iterrows():
        # For each service type with visits
        for service in ['SN', 'HHA', 'PT', 'OT', 'ST', 'MSW', 'MEDS']:
            if service in claims_df.columns and claim[service] > 0:
                # Find matching visits for this patient and claim
                matching_visits = visits_df[
                    (visits_df['Patient Name Clean'] == claim['Patient Name']) &
                    (visits_df['Claim #'] == claim['Code'])
                ]
                
                # Get provider for this service type (simplified - would need better mapping)
                if len(matching_visits) > 0:
                    provider = matching_visits['Caregiver'].mode()[0] if len(matching_visits['Caregiver'].mode()) > 0 else 'Unknown Provider'
                else:
                    provider = 'Unknown Provider'
                
                # Calculate costs
                visits = claim[service]
                cost_per_visit = 140 if service in ['SN', 'RN'] else 100 if service == 'HHA' else 125
                total_cost = visits * cost_per_visit
                
                service_records.append({
                    'Patient Name': claim['Patient Name'],
                    'Cycle Start': claim['Cycle Start'],
                    'Cycle End': claim['Cycle End'],
                    'Claim Code': claim['Claim Code'],
                    'Insurance': claim['Stat'],
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
                })
    
    service_df = pd.DataFrame(service_records)
    
    # Create output file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'HomeHealth_Post_Transform_{timestamp}.xlsx'
    
    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
        workbook = writer.book
        money_format = workbook.add_format({'num_format': '$#,##0.00'})
        percent_format = workbook.add_format({'num_format': '0.0%'})
        date_format = workbook.add_format({'num_format': 'mm/dd/yyyy'})
        
        # TAB 1: Original Claims Data
        print("\n📊 Creating TAB 1: Original Claims Data...")
        claims_df.to_excel(writer, sheet_name='Original Claims', index=False)
        
        # TAB 2: Original Visits Data
        print("📊 Creating TAB 2: Original Visits Data...")
        visits_df.to_excel(writer, sheet_name='Original Visits', index=False)
        
        # TAB 3: Master Transformed Data
        print("📊 Creating TAB 3: Master Transformed Data...")
        service_df.to_excel(writer, sheet_name='Master Transformed', index=False)
        
        # TAB 4: Revenue by Claim
        print("📊 Creating TAB 4: Revenue by Claim...")
        revenue_by_claim = claims_df.groupby(['Patient Name', 'Claim Code']).agg({
            'Cycle Start': 'first',
            'Cycle End': 'first',
            'Stat': 'first',
            'Total Amount': 'sum',
            'Expected Payment': 'sum',
            'Posted Payments': 'sum',
            'Balance': 'sum',
            'Net Adjust.': 'sum'
        }).reset_index()
        
        revenue_by_claim.columns = [
            'Patient Name', 'Claim Code', 'Cycle Start', 'Cycle End', 
            'Insurance', 'Total Amount Billed', 'Expected Payment',
            'Actual Payment Received', 'Remaining Balance', 'Net Adjustment'
        ]
        
        # Add placeholder date columns
        revenue_by_claim['Payment Requested At'] = pd.NaT
        revenue_by_claim['Payment Received At'] = pd.NaT
        revenue_by_claim['Days to Payment'] = 0
        
        revenue_by_claim.to_excel(writer, sheet_name='Revenue by Claim', index=False)
        
        # TAB 5: Service Costs
        print("📊 Creating TAB 5: Service Costs...")
        service_costs = service_df[[
            'Patient Name', 'Cycle Start', 'Cycle End', 'Service Type',
            'Provider Name', 'Service Visits', 'Cost per Visit', 'Total Cost',
            'File Status', 'Claim Amount'
        ]].copy()
        
        service_costs.to_excel(writer, sheet_name='Service Costs', index=False)
        
        # TAB 6: Profitability by Patient
        print("📊 Creating TAB 6: Profitability by Patient...")
        patient_profit = service_df.groupby(['Patient Name', 'Cycle Start', 'Cycle End']).agg({
            'Total Amount Billed': 'first',
            'Posted Payments': 'first',
            'Total Cost': 'sum'
        }).reset_index()
        
        patient_profit.columns = [
            'Patient Name', 'Cycle Start', 'Cycle End',
            'Total Revenue Billed', 'Total Revenue Received', 'Total Cost'
        ]
        
        patient_profit['Gross Profit'] = patient_profit['Total Revenue Received'] - patient_profit['Total Cost']
        patient_profit['Gross Margin %'] = (
            (patient_profit['Gross Profit'] / patient_profit['Total Revenue Billed']) * 100
        ).round(1).fillna(0)
        
        patient_profit.to_excel(writer, sheet_name='Profitability by Patient', index=False)
        
        # TAB 7: Provider Performance
        print("📊 Creating TAB 7: Provider Performance...")
        provider_perf = service_df.groupby(['Provider Name', 'Service Type']).agg({
            'Service Visits': 'sum',
            'Total Cost': 'sum',
            'Cost per Visit': 'mean',
            'Patient Name': 'nunique'
        }).reset_index()
        
        provider_perf.columns = [
            'Provider Name', 'Service Type', 'Total Visits',
            'Total Cost', 'Avg Cost per Visit', '# of Patients Served'
        ]
        
        provider_perf['Avg Cost per Patient'] = (
            provider_perf['Total Cost'] / provider_perf['# of Patients Served']
        ).round(2)
        
        provider_perf.to_excel(writer, sheet_name='Provider Performance', index=False)
        
        # TAB 8: Code Performance
        print("📊 Creating TAB 8: Code Performance...")
        code_perf = claims_df.groupby('Claim Code').agg({
            'Total Amount': ['count', 'mean'],
            'Expected Payment': 'mean',
            'Posted Payments': ['mean', 'sum'],
            'Net Adjust.': 'mean'
        }).round(2)
        
        code_perf.columns = [
            'Total Claims', 'Avg Billed Amount', 'Avg Expected Payment',
            'Avg Actual Payment', 'Total Received', 'Avg Adjustment'
        ]
        
        code_perf['Avg % Collected'] = (
            (code_perf['Avg Actual Payment'] / code_perf['Avg Expected Payment']) * 100
        ).round(1).fillna(0)
        
        code_perf.reset_index(inplace=True)
        code_perf.to_excel(writer, sheet_name='Code Performance', index=False)
        
        # TAB 9: Service Cost Summary
        print("📊 Creating TAB 9: Service Cost Summary...")
        service_summary = service_df.groupby('Service Type').agg({
            'Service Visits': 'sum',
            'Total Cost': 'sum',
            'Cost per Visit': 'mean'
        }).reset_index()
        
        service_summary.columns = [
            'Service Type', 'Total Visits', 'Total Cost', 'Avg Cost per Visit'
        ]
        
        service_summary['% of Total Cost'] = (
            (service_summary['Total Cost'] / service_summary['Total Cost'].sum()) * 100
        ).round(1)
        
        service_summary.to_excel(writer, sheet_name='Service Cost Summary', index=False)
        
        # TAB 10: Insurance Payer Performance
        print("📊 Creating TAB 10: Insurance Payer Performance...")
        insurance_perf = claims_df.groupby('Stat').agg({
            'Claim Code': 'count',
            'Expected Payment': 'mean',
            'Posted Payments': 'mean',
            'Net Adjust.': 'mean'
        }).round(2)
        
        insurance_perf.columns = [
            'Total Claims', 'Avg Expected Payment',
            'Avg Actual Payment', 'Avg Adjustment'
        ]
        
        insurance_perf['Avg Days to Payment'] = 0  # Placeholder
        insurance_perf['Avg % Collected'] = (
            (insurance_perf['Avg Actual Payment'] / insurance_perf['Avg Expected Payment']) * 100
        ).round(1).fillna(0)
        
        # Reorder columns
        insurance_perf = insurance_perf[[
            'Total Claims', 'Avg Days to Payment', 'Avg Expected Payment',
            'Avg Actual Payment', 'Avg Adjustment', 'Avg % Collected'
        ]]
        
        insurance_perf.reset_index(inplace=True)
        insurance_perf.rename(columns={'Stat': 'Insurance'}, inplace=True)
        insurance_perf.to_excel(writer, sheet_name='Insurance Payer Performance', index=False)
        
        # Format column widths
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            worksheet.set_column('A:Z', 15)
    
    print("\n" + "=" * 70)
    print("✅ PROCESSING COMPLETE!")
    print("=" * 70)
    print(f"\n📁 Output file: {output_file}")
    print("\nTabs created (10 total):")
    print("  ✓ TAB 1: Original Claims - Raw claims data")
    print("  ✓ TAB 2: Original Visits - Raw visits data")
    print("  ✓ TAB 3: Master Transformed - Service-level records")
    print("  ✓ TAB 4: Revenue by Claim")
    print("  ✓ TAB 5: Service Costs")
    print("  ✓ TAB 6: Profitability by Patient")
    print("  ✓ TAB 7: Provider Performance")
    print("  ✓ TAB 8: Code Performance")
    print("  ✓ TAB 9: Service Cost Summary")
    print("  ✓ TAB 10: Insurance Payer Performance")
    
    return output_file

if __name__ == "__main__":
    try:
        process_home_health_post_transform()
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()