import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

def generate_sample_data():
    """Generate sample claims and visits data files for demo purposes"""
    
    # Set seed for reproducibility
    random.seed(42)
    np.random.seed(42)
    
    # Generate patient names
    first_names = ['John', 'Maria', 'Robert', 'Linda', 'Michael', 'Patricia', 'David', 'Jennifer', 
                   'James', 'Elizabeth', 'William', 'Barbara', 'Richard', 'Susan', 'Joseph', 'Jessica',
                   'Thomas', 'Sarah', 'Charles', 'Karen', 'Christopher', 'Nancy', 'Daniel', 'Betty',
                   'Matthew', 'Helen', 'Anthony', 'Sandra', 'Mark', 'Donna']
    
    last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
                  'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson',
                  'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee', 'Perez', 'Thompson']
    
    # Generate provider/caregiver names
    providers = [
        '15 - Avagyan, Lilit',
        '17 - Movsisyan, Nensi', 
        '23 - Johnson, Sarah',
        '31 - Williams, Michael',
        '42 - Chen, Lisa',
        '55 - Patel, Raj',
        '67 - Thompson, Jessica',
        '78 - Garcia, Maria'
    ]
    
    # Insurance types
    insurance_types = ['Sent', 'Pending', 'Processed']
    
    # Policy prefixes
    policy_prefixes = ['1UR1NT5MD', '1UF6ER8VK', '9YN3E57NE', '2AH5PP4CN', '8XE1R05QP']
    
    # ==========================================
    # GENERATE CLAIMS DATA
    # ==========================================
    claims_data = []
    claim_counter = 10
    
    for i in range(100):
        patient_name = f"{random.choice(last_names)}, {random.choice(first_names)}"
        policy_number = f"{random.choice(policy_prefixes)}{random.randint(10, 99)}"
        claim_code = random.randint(20, 90)
        
        # Generate date range
        start_date = datetime(2025, random.randint(1, 8), random.randint(1, 28))
        end_date = start_date + timedelta(days=random.randint(7, 30))
        claim_period = f"{start_date.strftime('%m/%d/%y')} - {end_date.strftime('%m/%d/%y')}"
        
        # Generate service visits (ensure at least one service has visits)
        services = {'SN': 0, 'HHA': 0, 'PT': 0, 'OT': 0, 'ST': 0, 'MSW': 0, 'MEDS': 0}
        num_services = random.randint(1, 3)  # How many different services
        selected_services = random.sample(list(services.keys()), num_services)
        
        for service in selected_services:
            services[service] = random.randint(1, 12)
        
        total_visits = sum(services.values())
        
        # Generate financial data
        total_amount = round(random.uniform(1000, 8000), 2)
        expected_payment = round(total_amount * random.uniform(0.6, 0.9), 2)
        posted_payment = round(expected_payment * random.uniform(0, 1.0), 2)
        net_adjust = round(total_amount - expected_payment, 2)
        balance = round(expected_payment - posted_payment, 2)
        
        claims_data.append({
            'Code': claim_counter,
            'Patient Name': patient_name,
            'Policy Number': policy_number,
            'Claim Code': claim_code,
            'Claim Period': claim_period,
            'Stat': random.choice(insurance_types),
            'SN': services['SN'],
            'HHA': services['HHA'],
            'PT': services['PT'],
            'OT': services['OT'],
            'ST': services['ST'],
            'MSW': services['MSW'],
            'MEDS': services['MEDS'],
            'Total Visits': total_visits,
            'Total Amount': total_amount,
            'Expected Payment': expected_payment,
            'Posted Payments': posted_payment,
            'Net Adjust.': net_adjust,
            'Balance': balance
        })
        
        claim_counter += 1
    
    claims_df = pd.DataFrame(claims_data)
    
    # ==========================================
    # GENERATE PATIENT VISITS DATA
    # ==========================================
    visits_data = []
    visit_id = 100
    
    # Service type mapping
    service_descriptions = {
        'SN': ['551 - LVN Follow up visit', '551 - SN Assessment', '551 - SN Discharge'],
        'HHA': ['601 - HHA Personal Care', '601 - HHA Assistance', '601 - HHA Support'],
        'PT': ['751 - PT Evaluation', '751 - PT Treatment', '751 - PT Follow up'],
        'OT': ['801 - OT Assessment', '801 - OT Treatment', '801 - OT Follow up'],
        'RN': ['551 - RN Eval', '551 - RN Follow up', '551 - RN Discharge']
    }
    
    # For each claim, generate corresponding visits
    for _, claim in claims_df.iterrows():
        # Determine which services have visits
        services_with_visits = []
        if claim['SN'] > 0:
            services_with_visits.extend(['SN'] * int(claim['SN']))
        if claim['HHA'] > 0:
            services_with_visits.extend(['HHA'] * int(claim['HHA']))
        if claim['PT'] > 0:
            services_with_visits.extend(['PT'] * int(claim['PT']))
        if claim['OT'] > 0:
            services_with_visits.extend(['OT'] * int(claim['OT']))
        if claim['ST'] > 0:
            services_with_visits.extend(['ST'] * int(claim['ST']))
        
        # Parse claim period
        period_parts = claim['Claim Period'].split(' - ')
        start_date = datetime.strptime(period_parts[0], '%m/%d/%y')
        end_date = datetime.strptime(period_parts[1], '%m/%d/%y')
        
        # Generate individual visits spread across the claim period
        if services_with_visits:
            days_in_period = (end_date - start_date).days
            for i, service_type in enumerate(services_with_visits):
                # Spread visits across the period
                if len(services_with_visits) > 1:
                    visit_date = start_date + timedelta(days=min(i * 2, days_in_period))
                else:
                    visit_date = start_date
                
                # Assign provider based on service type - consistent providers for same service
                if service_type == 'SN':
                    provider = random.choice(providers[:3])  # Skilled nurses
                elif service_type == 'HHA':
                    provider = random.choice(providers[3:5])  # Home health aides
                elif service_type == 'PT':
                    provider = random.choice(providers[5:7])  # Physical therapists
                elif service_type == 'OT':
                    provider = providers[7]  # Occupational therapist
                else:
                    provider = random.choice(providers)  # Any provider
            
            # Determine cost per visit
            if service_type == 'HHA':
                cost = 65.00
            elif service_type in ['SN', 'RN']:
                cost = 140.00
            elif service_type == 'PT':
                cost = 125.00
            else:
                cost = 100.00
            
            visits_data.append({
                'Patient Name & Number': f"{claim['Patient Name']} ({claim['Code']:02d})",
                'HIC/Policy #': claim['Policy Number'],
                'Date': visit_date.strftime('%m/%d/%Y'),
                'Code & Description': random.choice(service_descriptions.get(service_type, ['General Visit'])),
                'Insurance': 'CMS - Medicare PPS',
                'Caregiver': provider,
                'Qty': 1.00,
                'Time In': f"{random.randint(8, 15):02d}:{random.choice(['00', '15', '30', '45'])}AM",
                'Time Out': f"{random.randint(9, 16):02d}:{random.choice(['00', '15', '30', '45'])}AM",
                'Amount': cost,
                'Notes In': '✓',
                'Billable': '✓',
                'Claim #': claim['Code']
            })
            
            visit_id += 1
    
    visits_df = pd.DataFrame(visits_data)
    
    # Save to Excel files
    print("Generating sample data files...")
    
    # Save claims data
    claims_file = 'sample_claims_data.xlsx'
    with pd.ExcelWriter(claims_file, engine='xlsxwriter') as writer:
        claims_df.to_excel(writer, sheet_name='Claims Receivable', index=False)
        workbook = writer.book
        worksheet = writer.sheets['Claims Receivable']
        worksheet.set_column('A:S', 12)
        
        # Add formatting
        money_format = workbook.add_format({'num_format': '$#,##0.00'})
        worksheet.set_column('O:S', 12, money_format)
    
    print(f"✓ Created {claims_file} with {len(claims_df)} claims")
    
    # Save visits data
    visits_file = 'sample_visits_data.xlsx'
    with pd.ExcelWriter(visits_file, engine='xlsxwriter') as writer:
        visits_df.to_excel(writer, sheet_name='Patient Visits List', index=False)
        workbook = writer.book
        worksheet = writer.sheets['Patient Visits List']
        worksheet.set_column('A:M', 15)
        
        # Add formatting
        money_format = workbook.add_format({'num_format': '$#,##0.00'})
        worksheet.set_column('J:J', 12, money_format)
    
    print(f"✓ Created {visits_file} with {len(visits_df)} visits")
    
    # Display summary
    print("\nSample data summary:")
    print(f"  • Total patients: {claims_df['Patient Name'].nunique()}")
    print(f"  • Total claims: {len(claims_df)}")
    print(f"  • Total visits: {len(visits_df)}")
    print(f"  • Service types: SN, HHA, PT, OT, ST, MSW, MEDS")
    print(f"  • Providers: {len(providers)} different caregivers")
    
    return claims_file, visits_file

if __name__ == "__main__":
    print("=" * 60)
    print("SAMPLE DATA GENERATOR FOR HOME HEALTH SYSTEM")
    print("=" * 60)
    generate_sample_data()
    print("\n✅ Sample files ready for processing!")
    print("Run the main processor script to analyze these files.")