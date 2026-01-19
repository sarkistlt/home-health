#!/usr/bin/env python3
"""
Home Health Agency Dashboard Generator

This script generates comprehensive Excel dashboards with 8 tabs from the
data warehouse, providing executive summaries, patient analytics, revenue
analysis, and operational insights.

Usage:
    python generate_dashboard.py --output outputs/dashboard_202501.xlsx
    python generate_dashboard.py --month 2025-01 --config config.yaml
"""

import argparse
import logging
import sqlite3
import pandas as pd
import numpy as np
import yaml
import os
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import xlsxwriter
from xlsxwriter.utility import xl_rowcol_to_cell
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

class HomeHealthDashboard:
    """Dashboard generator for Home Health Agency analytics."""

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the dashboard generator with configuration."""
        self.config = self._load_config(config_path)
        self.db_path = self.config['database']['path']
        self.generation_time = datetime.now()

        # Setup logging
        self._setup_logging()

        # Dashboard settings
        self.dashboard_tabs = self.config.get('dashboard_tabs', {})
        self.currency_format = self.config.get('output', {}).get('currency_format', '$#,##0.00')
        self.date_format = self.config.get('output', {}).get('date_format', 'mm/dd/yyyy')
        self.percentage_format = self.config.get('output', {}).get('percentage_format', '0.0%')

        self.logger.info("Dashboard generator initialized")

    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            print(f"Configuration file {config_path} not found. Using defaults.")
            return self._get_default_config()
        except yaml.YAMLError as e:
            print(f"Error parsing configuration file: {e}")
            return self._get_default_config()

    def _get_default_config(self) -> Dict:
        """Return default configuration if config file is not available."""
        return {
            'database': {'path': 'home_health_warehouse.db'},
            'output': {
                'dashboard_path': 'outputs/',
                'currency_format': '$#,##0.00',
                'date_format': 'mm/dd/yyyy',
                'percentage_format': '0.0%'
            },
            'logging': {'level': 'INFO'}
        }

    def _setup_logging(self):
        """Configure logging based on configuration."""
        log_config = self.config.get('logging', {})
        log_level = getattr(logging, log_config.get('level', 'INFO'))

        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        self.logger = logging.getLogger(__name__)

    def get_database_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Database file not found: {self.db_path}")
        return sqlite3.connect(self.db_path)

    def get_executive_summary_data(self) -> Dict:
        """Get data for executive summary tab."""
        self.logger.info("Generating executive summary data")

        with self.get_database_connection() as conn:
            # Current month metrics
            current_month = datetime.now().strftime('%Y-%m')

            # Active patients
            active_patients = pd.read_sql_query("""
                SELECT COUNT(DISTINCT patient_id) as count
                FROM patients
                WHERE status = 'Active'
            """, conn).iloc[0]['count']

            # Current month activity
            current_activity = pd.read_sql_query("""
                SELECT
                    COUNT(DISTINCT patient_id) as unique_patients,
                    COUNT(*) as total_visits,
                    SUM(duration_hours) as total_hours,
                    SUM(charge_amount) as total_charges,
                    AVG(charge_amount) as avg_visit_amount
                FROM visits
                WHERE strftime('%Y-%m', visit_date) = ?
            """, conn, params=[current_month])

            # Year to date metrics
            current_year = datetime.now().year
            ytd_activity = pd.read_sql_query("""
                SELECT
                    COUNT(DISTINCT patient_id) as unique_patients_ytd,
                    COUNT(*) as total_visits_ytd,
                    SUM(duration_hours) as total_hours_ytd,
                    SUM(charge_amount) as total_charges_ytd
                FROM visits
                WHERE strftime('%Y', visit_date) = ?
            """, conn, params=[str(current_year)])

            # Outstanding AR
            ar_summary = pd.read_sql_query("""
                SELECT
                    COUNT(*) as total_claims,
                    SUM(balance) as total_balance,
                    AVG(days_outstanding) as avg_days_outstanding
                FROM claims
                WHERE balance > 0
            """, conn)

            # Service mix current month
            service_mix = pd.read_sql_query("""
                SELECT
                    discipline,
                    COUNT(*) as visit_count,
                    SUM(duration_hours) as total_hours,
                    SUM(charge_amount) as total_charges
                FROM visits
                WHERE strftime('%Y-%m', visit_date) = ?
                GROUP BY discipline
                ORDER BY visit_count DESC
            """, conn, params=[current_month])

            # Top performing patients by revenue
            top_patients = pd.read_sql_query("""
                SELECT
                    p.patient_name,
                    COUNT(v.visit_id) as visits,
                    SUM(v.charge_amount) as total_charges
                FROM patients p
                JOIN visits v ON p.patient_id = v.patient_id
                WHERE strftime('%Y-%m', v.visit_date) = ?
                GROUP BY p.patient_id, p.patient_name
                ORDER BY total_charges DESC
                LIMIT 10
            """, conn, params=[current_month])

            return {
                'active_patients': active_patients,
                'current_activity': current_activity,
                'ytd_activity': ytd_activity,
                'ar_summary': ar_summary,
                'service_mix': service_mix,
                'top_patients': top_patients,
                'generation_date': self.generation_time.strftime('%m/%d/%Y %H:%M')
            }

    def get_patient_activity_data(self) -> Dict:
        """Get data for patient activity tab."""
        self.logger.info("Generating patient activity data")

        with self.get_database_connection() as conn:
            # Patient activity summary
            patient_summary = pd.read_sql_query("""
                SELECT
                    p.patient_id,
                    p.patient_name,
                    p.insurance_type,
                    p.admission_date,
                    p.status,
                    COUNT(v.visit_id) as total_visits,
                    SUM(v.duration_hours) as total_hours,
                    SUM(v.charge_amount) as total_charges,
                    MAX(v.visit_date) as last_visit_date,
                    MIN(v.visit_date) as first_visit_date,
                    COUNT(DISTINCT v.caregiver_name) as unique_caregivers,
                    COUNT(DISTINCT v.discipline) as service_types
                FROM patients p
                LEFT JOIN visits v ON p.patient_id = v.patient_id
                WHERE p.status = 'Active'
                GROUP BY p.patient_id, p.patient_name, p.insurance_type, p.admission_date, p.status
                ORDER BY total_visits DESC
            """, conn)

            # Add calculated columns
            if not patient_summary.empty:
                patient_summary['days_since_last_visit'] = (
                    datetime.now().date() - pd.to_datetime(patient_summary['last_visit_date']).dt.date
                ).dt.days

                patient_summary['avg_visit_amount'] = (
                    patient_summary['total_charges'] / patient_summary['total_visits']
                ).round(2)

            # Service utilization by patient
            service_detail = pd.read_sql_query("""
                SELECT
                    p.patient_name,
                    v.discipline,
                    COUNT(*) as visit_count,
                    SUM(v.duration_hours) as hours,
                    SUM(v.charge_amount) as charges
                FROM patients p
                JOIN visits v ON p.patient_id = v.patient_id
                WHERE p.status = 'Active'
                GROUP BY p.patient_id, p.patient_name, v.discipline
                ORDER BY p.patient_name, visit_count DESC
            """, conn)

            return {
                'patient_summary': patient_summary,
                'service_detail': service_detail
            }

    def get_revenue_analysis_data(self) -> Dict:
        """Get data for revenue analysis tab."""
        self.logger.info("Generating revenue analysis data")

        with self.get_database_connection() as conn:
            # Monthly revenue trends (12 months)
            monthly_trends = pd.read_sql_query("""
                SELECT
                    strftime('%Y-%m', visit_date) as month,
                    COUNT(DISTINCT patient_id) as unique_patients,
                    COUNT(*) as total_visits,
                    SUM(charge_amount) as total_revenue,
                    AVG(charge_amount) as avg_visit_revenue
                FROM visits
                WHERE visit_date >= date('now', '-12 months')
                GROUP BY strftime('%Y-%m', visit_date)
                ORDER BY month
            """, conn)

            # Revenue by insurance type
            insurance_revenue = pd.read_sql_query("""
                SELECT
                    p.insurance_type,
                    COUNT(v.visit_id) as visits,
                    SUM(v.charge_amount) as total_revenue,
                    AVG(v.charge_amount) as avg_visit_revenue
                FROM patients p
                JOIN visits v ON p.patient_id = v.patient_id
                WHERE v.visit_date >= date('now', '-3 months')
                GROUP BY p.insurance_type
                ORDER BY total_revenue DESC
            """, conn)

            # Revenue by service type
            service_revenue = pd.read_sql_query("""
                SELECT
                    discipline,
                    COUNT(*) as visits,
                    SUM(charge_amount) as total_revenue,
                    AVG(charge_amount) as avg_visit_revenue,
                    SUM(duration_hours) as total_hours,
                    AVG(duration_hours) as avg_visit_duration
                FROM visits
                WHERE visit_date >= date('now', '-3 months')
                GROUP BY discipline
                ORDER BY total_revenue DESC
            """, conn)

            # Collection analysis (if payments data available)
            collection_analysis = pd.read_sql_query("""
                SELECT
                    strftime('%Y-%m', claim_period_start) as month,
                    COUNT(*) as claims_count,
                    SUM(total_amount) as total_billed,
                    SUM(posted_payments) as total_collected,
                    SUM(balance) as outstanding_balance,
                    CASE
                        WHEN SUM(total_amount) > 0
                        THEN ROUND(SUM(posted_payments) * 100.0 / SUM(total_amount), 2)
                        ELSE 0
                    END as collection_rate
                FROM claims
                WHERE claim_period_start >= date('now', '-12 months')
                GROUP BY strftime('%Y-%m', claim_period_start)
                ORDER BY month
            """, conn)

            return {
                'monthly_trends': monthly_trends,
                'insurance_revenue': insurance_revenue,
                'service_revenue': service_revenue,
                'collection_analysis': collection_analysis
            }

    def get_ar_aging_data(self) -> Dict:
        """Get data for AR aging analysis tab."""
        self.logger.info("Generating AR aging data")

        with self.get_database_connection() as conn:
            # AR aging summary
            aging_summary = pd.read_sql_query("""
                SELECT
                    CASE
                        WHEN days_outstanding <= 30 THEN '0-30 days'
                        WHEN days_outstanding <= 60 THEN '31-60 days'
                        WHEN days_outstanding <= 90 THEN '61-90 days'
                        ELSE '90+ days'
                    END as aging_bucket,
                    COUNT(*) as claim_count,
                    SUM(balance) as total_balance,
                    AVG(days_outstanding) as avg_days_outstanding
                FROM claims
                WHERE balance > 0
                GROUP BY aging_bucket
                ORDER BY
                    CASE aging_bucket
                        WHEN '0-30 days' THEN 1
                        WHEN '31-60 days' THEN 2
                        WHEN '61-90 days' THEN 3
                        ELSE 4
                    END
            """, conn)

            # AR by patient
            patient_ar = pd.read_sql_query("""
                SELECT
                    p.patient_name,
                    p.insurance_type,
                    COUNT(c.claim_id) as claim_count,
                    SUM(c.balance) as total_balance,
                    AVG(c.days_outstanding) as avg_days_outstanding,
                    MAX(c.claim_period_end) as last_claim_date
                FROM patients p
                JOIN claims c ON p.patient_id = c.patient_id
                WHERE c.balance > 0
                GROUP BY p.patient_id, p.patient_name, p.insurance_type
                ORDER BY total_balance DESC
            """, conn)

            # AR by insurance type
            insurance_ar = pd.read_sql_query("""
                SELECT
                    p.insurance_type,
                    COUNT(c.claim_id) as claim_count,
                    SUM(c.balance) as total_balance,
                    AVG(c.days_outstanding) as avg_days_outstanding
                FROM patients p
                JOIN claims c ON p.patient_id = c.patient_id
                WHERE c.balance > 0
                GROUP BY p.insurance_type
                ORDER BY total_balance DESC
            """, conn)

            # Claims detail
            claims_detail = pd.read_sql_query("""
                SELECT
                    c.claim_number,
                    p.patient_name,
                    p.insurance_type,
                    c.claim_period_start,
                    c.claim_period_end,
                    c.total_amount,
                    c.posted_payments,
                    c.balance,
                    c.days_outstanding,
                    CASE
                        WHEN c.days_outstanding <= 30 THEN '0-30 days'
                        WHEN c.days_outstanding <= 60 THEN '31-60 days'
                        WHEN c.days_outstanding <= 90 THEN '61-90 days'
                        ELSE '90+ days'
                    END as aging_bucket
                FROM claims c
                JOIN patients p ON c.patient_id = p.patient_id
                WHERE c.balance > 0
                ORDER BY c.days_outstanding DESC, c.balance DESC
            """, conn)

            return {
                'aging_summary': aging_summary,
                'patient_ar': patient_ar,
                'insurance_ar': insurance_ar,
                'claims_detail': claims_detail
            }

    def get_service_utilization_data(self) -> Dict:
        """Get data for service utilization tab."""
        self.logger.info("Generating service utilization data")

        with self.get_database_connection() as conn:
            # Service utilization summary
            service_summary = pd.read_sql_query("""
                SELECT
                    discipline,
                    COUNT(*) as total_visits,
                    SUM(duration_hours) as total_hours,
                    AVG(duration_hours) as avg_visit_duration,
                    SUM(charge_amount) as total_revenue,
                    AVG(charge_amount) as avg_visit_revenue,
                    COUNT(DISTINCT patient_id) as unique_patients,
                    COUNT(DISTINCT caregiver_name) as unique_caregivers
                FROM visits
                WHERE visit_date >= date('now', '-3 months')
                GROUP BY discipline
                ORDER BY total_visits DESC
            """, conn)

            # Monthly service trends
            service_trends = pd.read_sql_query("""
                SELECT
                    strftime('%Y-%m', visit_date) as month,
                    discipline,
                    COUNT(*) as visits,
                    SUM(duration_hours) as hours,
                    SUM(charge_amount) as revenue
                FROM visits
                WHERE visit_date >= date('now', '-12 months')
                GROUP BY strftime('%Y-%m', visit_date), discipline
                ORDER BY month, discipline
            """, conn)

            # Service mix by patient
            patient_service_mix = pd.read_sql_query("""
                SELECT
                    p.patient_name,
                    p.insurance_type,
                    v.discipline,
                    COUNT(*) as visits,
                    SUM(v.duration_hours) as hours,
                    SUM(v.charge_amount) as revenue,
                    AVG(v.charge_amount) as avg_visit_revenue
                FROM patients p
                JOIN visits v ON p.patient_id = v.patient_id
                WHERE v.visit_date >= date('now', '-1 month')
                    AND p.status = 'Active'
                GROUP BY p.patient_id, p.patient_name, p.insurance_type, v.discipline
                ORDER BY p.patient_name, visits DESC
            """, conn)

            # Episode analysis
            episode_analysis = pd.read_sql_query("""
                SELECT
                    p.patient_name,
                    p.insurance_type,
                    MIN(v.visit_date) as episode_start,
                    MAX(v.visit_date) as episode_end,
                    COUNT(*) as total_visits,
                    SUM(v.duration_hours) as total_hours,
                    SUM(v.charge_amount) as total_revenue,
                    COUNT(DISTINCT v.discipline) as service_types,
                    COUNT(DISTINCT v.caregiver_name) as caregivers_involved
                FROM patients p
                JOIN visits v ON p.patient_id = v.patient_id
                WHERE p.status = 'Active'
                GROUP BY p.patient_id, p.patient_name, p.insurance_type
                HAVING COUNT(*) > 0
                ORDER BY total_visits DESC
            """, conn)

            return {
                'service_summary': service_summary,
                'service_trends': service_trends,
                'patient_service_mix': patient_service_mix,
                'episode_analysis': episode_analysis
            }

    def get_caregiver_productivity_data(self) -> Dict:
        """Get data for caregiver productivity tab."""
        self.logger.info("Generating caregiver productivity data")

        with self.get_database_connection() as conn:
            # Caregiver productivity summary
            caregiver_summary = pd.read_sql_query("""
                SELECT
                    caregiver_name,
                    COUNT(*) as total_visits,
                    COUNT(DISTINCT patient_id) as unique_patients,
                    SUM(duration_hours) as total_hours,
                    AVG(duration_hours) as avg_visit_duration,
                    SUM(charge_amount) as total_revenue,
                    AVG(charge_amount) as avg_visit_revenue,
                    MIN(visit_date) as first_visit,
                    MAX(visit_date) as last_visit
                FROM visits
                WHERE visit_date >= date('now', '-3 months')
                    AND caregiver_name IS NOT NULL
                    AND caregiver_name != ''
                GROUP BY caregiver_name
                ORDER BY total_visits DESC
            """, conn)

            # Caregiver service mix
            caregiver_services = pd.read_sql_query("""
                SELECT
                    caregiver_name,
                    discipline,
                    COUNT(*) as visits,
                    SUM(duration_hours) as hours,
                    SUM(charge_amount) as revenue
                FROM visits
                WHERE visit_date >= date('now', '-3 months')
                    AND caregiver_name IS NOT NULL
                    AND caregiver_name != ''
                GROUP BY caregiver_name, discipline
                ORDER BY caregiver_name, visits DESC
            """, conn)

            # Monthly productivity trends
            monthly_productivity = pd.read_sql_query("""
                SELECT
                    strftime('%Y-%m', visit_date) as month,
                    caregiver_name,
                    COUNT(*) as visits,
                    SUM(duration_hours) as hours,
                    SUM(charge_amount) as revenue
                FROM visits
                WHERE visit_date >= date('now', '-6 months')
                    AND caregiver_name IS NOT NULL
                    AND caregiver_name != ''
                GROUP BY strftime('%Y-%m', visit_date), caregiver_name
                ORDER BY month, caregiver_name
            """, conn)

            # Patient assignments
            patient_assignments = pd.read_sql_query("""
                SELECT
                    caregiver_name,
                    p.patient_name,
                    p.insurance_type,
                    COUNT(v.visit_id) as visits,
                    SUM(v.duration_hours) as hours,
                    MAX(v.visit_date) as last_visit,
                    SUM(v.charge_amount) as revenue
                FROM visits v
                JOIN patients p ON v.patient_id = p.patient_id
                WHERE v.visit_date >= date('now', '-3 months')
                    AND v.caregiver_name IS NOT NULL
                    AND v.caregiver_name != ''
                    AND p.status = 'Active'
                GROUP BY v.caregiver_name, p.patient_id, p.patient_name, p.insurance_type
                ORDER BY v.caregiver_name, visits DESC
            """, conn)

            return {
                'caregiver_summary': caregiver_summary,
                'caregiver_services': caregiver_services,
                'monthly_productivity': monthly_productivity,
                'patient_assignments': patient_assignments
            }

    def get_monthly_trends_data(self) -> Dict:
        """Get data for monthly trends tab."""
        self.logger.info("Generating monthly trends data")

        with self.get_database_connection() as conn:
            # 12-month rolling metrics
            monthly_metrics = pd.read_sql_query("""
                SELECT
                    strftime('%Y-%m', visit_date) as month,
                    COUNT(DISTINCT patient_id) as unique_patients,
                    COUNT(*) as total_visits,
                    SUM(duration_hours) as total_hours,
                    SUM(charge_amount) as total_revenue,
                    AVG(charge_amount) as avg_visit_revenue,
                    AVG(duration_hours) as avg_visit_duration,
                    COUNT(DISTINCT caregiver_name) as active_caregivers
                FROM visits
                WHERE visit_date >= date('now', '-12 months')
                GROUP BY strftime('%Y-%m', visit_date)
                ORDER BY month
            """, conn)

            # Year-over-year comparison
            yoy_comparison = pd.read_sql_query("""
                SELECT
                    strftime('%m', visit_date) as month_num,
                    strftime('%Y', visit_date) as year,
                    COUNT(*) as visits,
                    SUM(charge_amount) as revenue,
                    COUNT(DISTINCT patient_id) as patients
                FROM visits
                WHERE visit_date >= date('now', '-24 months')
                GROUP BY strftime('%Y', visit_date), strftime('%m', visit_date)
                ORDER BY year, month_num
            """, conn)

            # Seasonal patterns
            seasonal_patterns = pd.read_sql_query("""
                SELECT
                    strftime('%m', visit_date) as month,
                    COUNT(*) as avg_visits,
                    SUM(charge_amount) as avg_revenue,
                    COUNT(DISTINCT patient_id) as avg_patients
                FROM visits
                WHERE visit_date >= date('now', '-24 months')
                GROUP BY strftime('%m', visit_date)
                ORDER BY month
            """, conn)

            # Growth rates
            if not monthly_metrics.empty:
                monthly_metrics = monthly_metrics.copy()
                monthly_metrics['visits_growth'] = monthly_metrics['total_visits'].pct_change() * 100
                monthly_metrics['revenue_growth'] = monthly_metrics['total_revenue'].pct_change() * 100
                monthly_metrics['patients_growth'] = monthly_metrics['unique_patients'].pct_change() * 100

            return {
                'monthly_metrics': monthly_metrics,
                'yoy_comparison': yoy_comparison,
                'seasonal_patterns': seasonal_patterns
            }

    def get_patient_detail_data(self) -> Dict:
        """Get data for patient detail tab."""
        self.logger.info("Generating patient detail data")

        with self.get_database_connection() as conn:
            # Complete patient roster with details
            patient_detail = pd.read_sql_query("""
                SELECT
                    p.patient_id,
                    p.patient_name,
                    p.first_name,
                    p.last_name,
                    p.insurance_type,
                    p.insurance_company,
                    p.admission_date,
                    p.discharge_date,
                    p.status,
                    p.primary_diagnosis,
                    p.primary_physician,
                    p.phone_primary,
                    p.address_line1,
                    p.city,
                    p.state,
                    p.zip_code,
                    COUNT(v.visit_id) as total_visits,
                    SUM(v.duration_hours) as total_hours,
                    SUM(v.charge_amount) as total_charges,
                    MIN(v.visit_date) as first_visit,
                    MAX(v.visit_date) as last_visit,
                    COUNT(DISTINCT v.caregiver_name) as caregivers_assigned,
                    COUNT(DISTINCT v.discipline) as service_types_received
                FROM patients p
                LEFT JOIN visits v ON p.patient_id = v.patient_id
                GROUP BY p.patient_id, p.patient_name, p.first_name, p.last_name,
                         p.insurance_type, p.insurance_company, p.admission_date,
                         p.discharge_date, p.status, p.primary_diagnosis,
                         p.primary_physician, p.phone_primary, p.address_line1,
                         p.city, p.state, p.zip_code
                ORDER BY p.patient_name
            """, conn)

            # Visit history summary
            visit_history = pd.read_sql_query("""
                SELECT
                    p.patient_name,
                    v.visit_date,
                    v.discipline,
                    v.service_description,
                    v.caregiver_name,
                    v.duration_hours,
                    v.charge_amount,
                    v.visit_status
                FROM patients p
                JOIN visits v ON p.patient_id = v.patient_id
                WHERE v.visit_date >= date('now', '-6 months')
                ORDER BY p.patient_name, v.visit_date DESC
            """, conn)

            # Outstanding balances
            patient_balances = pd.read_sql_query("""
                SELECT
                    p.patient_name,
                    COUNT(c.claim_id) as open_claims,
                    SUM(c.balance) as total_balance,
                    MIN(c.claim_period_start) as oldest_claim_date,
                    MAX(c.days_outstanding) as max_days_outstanding
                FROM patients p
                JOIN claims c ON p.patient_id = c.patient_id
                WHERE c.balance > 0
                GROUP BY p.patient_id, p.patient_name
                ORDER BY total_balance DESC
            """, conn)

            return {
                'patient_detail': patient_detail,
                'visit_history': visit_history,
                'patient_balances': patient_balances
            }

    def create_dashboard_workbook(self, output_path: str) -> xlsxwriter.Workbook:
        """Create Excel workbook with formatting."""
        # Create workbook
        workbook = xlsxwriter.Workbook(output_path)

        # Define formats
        self.formats = {
            'title': workbook.add_format({
                'bold': True,
                'font_size': 16,
                'font_color': 'white',
                'bg_color': '#2E75B6',
                'align': 'center',
                'valign': 'vcenter'
            }),
            'header': workbook.add_format({
                'bold': True,
                'font_size': 12,
                'font_color': 'white',
                'bg_color': '#4F81BD',
                'align': 'center',
                'valign': 'vcenter',
                'text_wrap': True,
                'border': 1
            }),
            'currency': workbook.add_format({
                'num_format': self.currency_format,
                'align': 'right'
            }),
            'currency_bold': workbook.add_format({
                'num_format': self.currency_format,
                'bold': True,
                'align': 'right'
            }),
            'date': workbook.add_format({
                'num_format': self.date_format,
                'align': 'center'
            }),
            'percentage': workbook.add_format({
                'num_format': self.percentage_format,
                'align': 'right'
            }),
            'number': workbook.add_format({
                'num_format': '#,##0',
                'align': 'right'
            }),
            'decimal': workbook.add_format({
                'num_format': '#,##0.0',
                'align': 'right'
            }),
            'text': workbook.add_format({
                'align': 'left',
                'valign': 'vcenter'
            }),
            'center': workbook.add_format({
                'align': 'center',
                'valign': 'vcenter'
            }),
            'summary_label': workbook.add_format({
                'bold': True,
                'font_size': 11,
                'align': 'right'
            }),
            'summary_value': workbook.add_format({
                'font_size': 11,
                'num_format': '#,##0',
                'align': 'left',
                'bg_color': '#F2F2F2'
            }),
            'summary_currency': workbook.add_format({
                'font_size': 11,
                'num_format': self.currency_format,
                'align': 'left',
                'bg_color': '#F2F2F2'
            })
        }

        return workbook

    def write_summary_section(self, worksheet, start_row: int, title: str, data: Dict, formats: Dict) -> int:
        """Write a summary section to worksheet and return next row."""
        # Write title
        worksheet.write(start_row, 0, title, formats['title'])
        worksheet.merge_range(start_row, 0, start_row, 3, title, formats['title'])

        current_row = start_row + 2

        # Write key-value pairs
        for label, value in data.items():
            worksheet.write(current_row, 0, label, formats['summary_label'])

            if isinstance(value, (int, float)):
                if 'amount' in label.lower() or 'revenue' in label.lower() or 'balance' in label.lower():
                    worksheet.write(current_row, 1, value, formats['summary_currency'])
                else:
                    worksheet.write(current_row, 1, value, formats['summary_value'])
            else:
                worksheet.write(current_row, 1, str(value), formats['summary_value'])

            current_row += 1

        return current_row + 1

    def write_dataframe_to_worksheet(self, worksheet, df: pd.DataFrame, start_row: int = 0,
                                   start_col: int = 0, title: str = None) -> int:
        """Write DataFrame to worksheet with proper formatting."""
        current_row = start_row

        # Write title if provided
        if title:
            worksheet.write(current_row, start_col, title, self.formats['title'])
            if len(df.columns) > 1:
                worksheet.merge_range(current_row, start_col, current_row, start_col + len(df.columns) - 1, title, self.formats['title'])
            current_row += 2

        if df.empty:
            worksheet.write(current_row, start_col, "No data available", self.formats['text'])
            return current_row + 2

        # Write headers
        for col_idx, column in enumerate(df.columns):
            worksheet.write(current_row, start_col + col_idx, column.replace('_', ' ').title(), self.formats['header'])

        current_row += 1

        # Write data
        for row_idx, row in df.iterrows():
            for col_idx, (column, value) in enumerate(row.items()):
                col_pos = start_col + col_idx

                # Determine format based on column name and value type
                cell_format = self.formats['text']

                if pd.isna(value):
                    value = ""
                elif 'date' in column.lower():
                    if value and str(value) != '':
                        try:
                            value = pd.to_datetime(value).date() if pd.notnull(value) else ""
                            cell_format = self.formats['date']
                        except:
                            cell_format = self.formats['text']
                elif any(word in column.lower() for word in ['amount', 'revenue', 'charges', 'balance', 'payment']):
                    cell_format = self.formats['currency']
                elif any(word in column.lower() for word in ['rate', 'percentage', 'pct']):
                    cell_format = self.formats['percentage']
                elif any(word in column.lower() for word in ['visits', 'hours', 'count', 'days', 'claims']):
                    cell_format = self.formats['number']
                elif isinstance(value, (int, float)) and column.lower() not in ['patient_id', 'claim_number']:
                    cell_format = self.formats['decimal']

                worksheet.write(current_row, col_pos, value, cell_format)

            current_row += 1

        # Auto-fit columns
        for col_idx, column in enumerate(df.columns):
            max_length = max(len(str(column)), df[column].astype(str).str.len().max())
            worksheet.set_column(start_col + col_idx, start_col + col_idx, min(max_length + 2, 50))

        return current_row + 1

    def create_executive_summary_tab(self, workbook: xlsxwriter.Workbook, data: Dict):
        """Create executive summary tab."""
        worksheet = workbook.add_worksheet('Executive Summary')

        # Set column widths
        worksheet.set_column('A:A', 25)
        worksheet.set_column('B:B', 15)
        worksheet.set_column('C:D', 20)

        current_row = 0

        # Header
        worksheet.write(current_row, 0, f"Home Health Agency Dashboard - {data['generation_date']}", self.formats['title'])
        worksheet.merge_range(current_row, 0, current_row, 3, f"Home Health Agency Dashboard - {data['generation_date']}", self.formats['title'])
        current_row += 3

        # Current month summary
        if not data['current_activity'].empty:
            current_data = data['current_activity'].iloc[0]
            summary_data = {
                'Active Patients': data['active_patients'],
                'Unique Patients This Month': int(current_data['unique_patients']) if pd.notna(current_data['unique_patients']) else 0,
                'Total Visits This Month': int(current_data['total_visits']) if pd.notna(current_data['total_visits']) else 0,
                'Total Hours This Month': round(current_data['total_hours'], 1) if pd.notna(current_data['total_hours']) else 0,
                'Total Revenue This Month': current_data['total_charges'] if pd.notna(current_data['total_charges']) else 0,
                'Average Visit Amount': current_data['avg_visit_amount'] if pd.notna(current_data['avg_visit_amount']) else 0
            }

            current_row = self.write_summary_section(worksheet, current_row, 'Current Month Performance', summary_data, self.formats)

        # YTD summary
        if not data['ytd_activity'].empty:
            ytd_data = data['ytd_activity'].iloc[0]
            ytd_summary = {
                'YTD Unique Patients': int(ytd_data['unique_patients_ytd']) if pd.notna(ytd_data['unique_patients_ytd']) else 0,
                'YTD Total Visits': int(ytd_data['total_visits_ytd']) if pd.notna(ytd_data['total_visits_ytd']) else 0,
                'YTD Total Hours': round(ytd_data['total_hours_ytd'], 1) if pd.notna(ytd_data['total_hours_ytd']) else 0,
                'YTD Total Revenue': ytd_data['total_charges_ytd'] if pd.notna(ytd_data['total_charges_ytd']) else 0
            }

            current_row = self.write_summary_section(worksheet, current_row, 'Year-to-Date Performance', ytd_summary, self.formats)

        # AR summary
        if not data['ar_summary'].empty:
            ar_data = data['ar_summary'].iloc[0]
            ar_summary_data = {
                'Outstanding Claims': int(ar_data['total_claims']) if pd.notna(ar_data['total_claims']) else 0,
                'Total AR Balance': ar_data['total_balance'] if pd.notna(ar_data['total_balance']) else 0,
                'Average Days Outstanding': round(ar_data['avg_days_outstanding'], 1) if pd.notna(ar_data['avg_days_outstanding']) else 0
            }

            current_row = self.write_summary_section(worksheet, current_row, 'Accounts Receivable Summary', ar_summary_data, self.formats)

        # Service mix table
        current_row = self.write_dataframe_to_worksheet(worksheet, data['service_mix'], current_row, 0, 'Service Mix - Current Month')

        # Top patients table
        current_row = self.write_dataframe_to_worksheet(worksheet, data['top_patients'], current_row, 0, 'Top 10 Patients by Revenue - Current Month')

    def create_patient_activity_tab(self, workbook: xlsxwriter.Workbook, data: Dict):
        """Create patient activity tab."""
        worksheet = workbook.add_worksheet('Patient Activity')

        current_row = 0

        # Patient summary
        current_row = self.write_dataframe_to_worksheet(
            worksheet, data['patient_summary'], current_row, 0, 'Patient Activity Summary'
        )

        # Service detail
        current_row = self.write_dataframe_to_worksheet(
            worksheet, data['service_detail'], current_row, 0, 'Service Utilization by Patient'
        )

    def create_revenue_analysis_tab(self, workbook: xlsxwriter.Workbook, data: Dict):
        """Create revenue analysis tab."""
        worksheet = workbook.add_worksheet('Revenue Analysis')

        current_row = 0

        # Monthly trends
        current_row = self.write_dataframe_to_worksheet(
            worksheet, data['monthly_trends'], current_row, 0, 'Monthly Revenue Trends (12 Months)'
        )

        # Insurance revenue
        current_row = self.write_dataframe_to_worksheet(
            worksheet, data['insurance_revenue'], current_row, 0, 'Revenue by Insurance Type'
        )

        # Service revenue
        current_row = self.write_dataframe_to_worksheet(
            worksheet, data['service_revenue'], current_row, 0, 'Revenue by Service Type'
        )

        # Collection analysis
        current_row = self.write_dataframe_to_worksheet(
            worksheet, data['collection_analysis'], current_row, 0, 'Collection Analysis'
        )

    def create_ar_aging_tab(self, workbook: xlsxwriter.Workbook, data: Dict):
        """Create AR aging tab."""
        worksheet = workbook.add_worksheet('AR Aging')

        current_row = 0

        # Aging summary
        current_row = self.write_dataframe_to_worksheet(
            worksheet, data['aging_summary'], current_row, 0, 'AR Aging Summary'
        )

        # Patient AR
        current_row = self.write_dataframe_to_worksheet(
            worksheet, data['patient_ar'], current_row, 0, 'AR by Patient'
        )

        # Insurance AR
        current_row = self.write_dataframe_to_worksheet(
            worksheet, data['insurance_ar'], current_row, 0, 'AR by Insurance Type'
        )

        # Claims detail
        current_row = self.write_dataframe_to_worksheet(
            worksheet, data['claims_detail'], current_row, 0, 'Outstanding Claims Detail'
        )

    def create_service_utilization_tab(self, workbook: xlsxwriter.Workbook, data: Dict):
        """Create service utilization tab."""
        worksheet = workbook.add_worksheet('Service Utilization')

        current_row = 0

        # Service summary
        current_row = self.write_dataframe_to_worksheet(
            worksheet, data['service_summary'], current_row, 0, 'Service Utilization Summary'
        )

        # Patient service mix
        current_row = self.write_dataframe_to_worksheet(
            worksheet, data['patient_service_mix'], current_row, 0, 'Service Mix by Patient'
        )

        # Episode analysis
        current_row = self.write_dataframe_to_worksheet(
            worksheet, data['episode_analysis'], current_row, 0, 'Episode Analysis'
        )

    def create_caregiver_productivity_tab(self, workbook: xlsxwriter.Workbook, data: Dict):
        """Create caregiver productivity tab."""
        worksheet = workbook.add_worksheet('Caregiver Productivity')

        current_row = 0

        # Caregiver summary
        current_row = self.write_dataframe_to_worksheet(
            worksheet, data['caregiver_summary'], current_row, 0, 'Caregiver Productivity Summary'
        )

        # Patient assignments
        current_row = self.write_dataframe_to_worksheet(
            worksheet, data['patient_assignments'], current_row, 0, 'Patient Assignments'
        )

    def create_monthly_trends_tab(self, workbook: xlsxwriter.Workbook, data: Dict):
        """Create monthly trends tab."""
        worksheet = workbook.add_worksheet('Monthly Trends')

        current_row = 0

        # Monthly metrics
        current_row = self.write_dataframe_to_worksheet(
            worksheet, data['monthly_metrics'], current_row, 0, '12-Month Rolling Metrics'
        )

        # YoY comparison
        current_row = self.write_dataframe_to_worksheet(
            worksheet, data['yoy_comparison'], current_row, 0, 'Year-over-Year Comparison'
        )

        # Seasonal patterns
        current_row = self.write_dataframe_to_worksheet(
            worksheet, data['seasonal_patterns'], current_row, 0, 'Seasonal Patterns'
        )

    def create_patient_detail_tab(self, workbook: xlsxwriter.Workbook, data: Dict):
        """Create patient detail tab."""
        worksheet = workbook.add_worksheet('Patient Detail')

        current_row = 0

        # Patient detail
        current_row = self.write_dataframe_to_worksheet(
            worksheet, data['patient_detail'], current_row, 0, 'Complete Patient Roster'
        )

        # Patient balances
        if not data['patient_balances'].empty:
            current_row = self.write_dataframe_to_worksheet(
                worksheet, data['patient_balances'], current_row, 0, 'Outstanding Patient Balances'
            )

    def generate_dashboard(self, output_path: str = None) -> str:
        """Generate complete dashboard and return file path."""
        if output_path is None:
            timestamp = self.generation_time.strftime('%Y%m%d_%H%M%S')
            output_dir = self.config.get('output', {}).get('dashboard_path', 'outputs/')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f'HHA_Dashboard_{timestamp}.xlsx')

        self.logger.info(f"Generating dashboard: {output_path}")

        try:
            # Collect all data
            executive_data = self.get_executive_summary_data()
            patient_data = self.get_patient_activity_data()
            revenue_data = self.get_revenue_analysis_data()
            ar_data = self.get_ar_aging_data()
            service_data = self.get_service_utilization_data()
            caregiver_data = self.get_caregiver_productivity_data()
            trends_data = self.get_monthly_trends_data()
            detail_data = self.get_patient_detail_data()

            # Create workbook
            workbook = self.create_dashboard_workbook(output_path)

            # Create tabs
            self.create_executive_summary_tab(workbook, executive_data)
            self.create_patient_activity_tab(workbook, patient_data)
            self.create_revenue_analysis_tab(workbook, revenue_data)
            self.create_ar_aging_tab(workbook, ar_data)
            self.create_service_utilization_tab(workbook, service_data)
            self.create_caregiver_productivity_tab(workbook, caregiver_data)
            self.create_monthly_trends_tab(workbook, trends_data)
            self.create_patient_detail_tab(workbook, detail_data)

            # Close workbook
            workbook.close()

            self.logger.info(f"Dashboard generated successfully: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Error generating dashboard: {e}")
            raise


def main():
    """Main entry point for dashboard generator."""
    parser = argparse.ArgumentParser(description='Home Health Agency Dashboard Generator')
    parser.add_argument('--config', default='config.yaml', help='Configuration file path')
    parser.add_argument('--output', help='Output file path')
    parser.add_argument('--month', help='Month to focus on (YYYY-MM)')

    args = parser.parse_args()

    try:
        # Initialize dashboard generator
        dashboard = HomeHealthDashboard(args.config)

        # Generate dashboard
        output_path = dashboard.generate_dashboard(args.output)

        print(f"\nDashboard generated successfully!")
        print(f"File: {output_path}")
        print(f"Generated at: {dashboard.generation_time.strftime('%m/%d/%Y %H:%M:%S')}")

    except Exception as e:
        print(f"Dashboard generation failed: {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())