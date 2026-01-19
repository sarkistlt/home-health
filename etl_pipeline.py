#!/usr/bin/env python3
"""
Home Health Agency Data Warehouse ETL Pipeline

This script processes PDF reports and Excel files from home health agencies,
extracts patient visit data and accounts receivable information, and stores
it in a SQLite database for historical tracking and analysis.

Usage:
    python etl_pipeline.py --input-dir ./data/pdfs --month 2025-01
    python etl_pipeline.py --config config.yaml --process-all
"""

import argparse
import logging
import sqlite3
import pandas as pd
import numpy as np
import yaml
import os
import re
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import pdfplumber
import tabula
from fuzzywuzzy import fuzz, process
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings('ignore')

class HomeHealthETL:
    """Main ETL pipeline for Home Health Agency data processing."""

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the ETL pipeline with configuration."""
        self.config = self._load_config(config_path)
        self.db_path = self.config['database']['path']
        self.import_batch = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.import_id = None

        # Setup logging
        self._setup_logging()

        # Statistics tracking
        self.stats = {
            'files_processed': 0,
            'records_read': 0,
            'records_imported': 0,
            'records_updated': 0,
            'records_failed': 0,
            'patients_matched': 0,
            'patients_created': 0,
            'start_time': datetime.now()
        }

        self.logger.info(f"ETL Pipeline initialized - Batch ID: {self.import_batch}")

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
            'input_files': {
                'pdf_directory': 'data/pdfs/',
                'excel_directory': 'data/excel/'
            },
            'processing': {
                'batch_size': 1000,
                'name_match_threshold': 0.85,
                'fuzzy_matching': True
            },
            'logging': {'level': 'INFO', 'file': 'logs/etl_pipeline.log'}
        }

    def _setup_logging(self):
        """Configure logging based on configuration."""
        log_config = self.config.get('logging', {})
        log_level = getattr(logging, log_config.get('level', 'INFO'))
        log_file = log_config.get('file', 'logs/etl_pipeline.log')

        # Create logs directory if it doesn't exist
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

        # Configure logging
        logging.basicConfig(
            level=log_level,
            format=log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler() if log_config.get('console_output', True) else logging.NullHandler()
            ]
        )

        self.logger = logging.getLogger(__name__)

    def get_database_connection(self) -> sqlite3.Connection:
        """Get database connection with proper configuration."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def start_import_log(self, file_name: str, file_path: str, file_type: str) -> int:
        """Start import log entry and return import_id."""
        try:
            with self.get_database_connection() as conn:
                cursor = conn.cursor()

                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0

                cursor.execute("""
                    INSERT INTO import_log (
                        import_batch, file_name, file_path, file_type, file_size,
                        records_read, records_imported, records_updated, records_failed,
                        import_status, user_name, machine_name
                    ) VALUES (?, ?, ?, ?, ?, 0, 0, 0, 0, 'In Progress', ?, ?)
                """, (
                    self.import_batch, file_name, file_path, file_type, file_size,
                    os.getenv('USER', 'unknown'), os.uname().nodename
                ))

                import_id = cursor.lastrowid
                conn.commit()
                return import_id
        except Exception as e:
            self.logger.error(f"Failed to start import log: {e}")
            return None

    def update_import_log(self, import_id: int, status: str, error_message: str = None):
        """Update import log with final statistics."""
        if import_id is None:
            return

        try:
            with self.get_database_connection() as conn:
                cursor = conn.cursor()

                duration = (datetime.now() - self.stats['start_time']).total_seconds()

                cursor.execute("""
                    UPDATE import_log SET
                        records_read = ?,
                        records_imported = ?,
                        records_updated = ?,
                        records_failed = ?,
                        import_status = ?,
                        import_duration_seconds = ?,
                        error_message = ?
                    WHERE import_id = ?
                """, (
                    self.stats['records_read'],
                    self.stats['records_imported'],
                    self.stats['records_updated'],
                    self.stats['records_failed'],
                    status,
                    int(duration),
                    error_message,
                    import_id
                ))

                conn.commit()
        except Exception as e:
            self.logger.error(f"Failed to update import log: {e}")

    def extract_patient_id_from_name(self, patient_name: str) -> Tuple[Optional[int], str, str, str]:
        """
        Extract patient ID and name components from patient name string.
        Expected formats:
        - "LastName, FirstName (12345)"
        - "LastName, FirstName"
        - "FirstName LastName (12345)"
        """
        if not patient_name or pd.isna(patient_name):
            return None, "", "", ""

        # Clean the name
        name = str(patient_name).strip()

        # Extract patient ID if present
        patient_id = None
        id_match = re.search(r'\((\d+)\)', name)
        if id_match:
            patient_id = int(id_match.group(1))
            name = re.sub(r'\s*\(\d+\)', '', name).strip()

        # Split name into components
        if ',' in name:
            # Format: "LastName, FirstName"
            parts = name.split(',', 1)
            last_name = parts[0].strip()
            first_name = parts[1].strip() if len(parts) > 1 else ""
        else:
            # Format: "FirstName LastName"
            parts = name.split()
            if len(parts) >= 2:
                first_name = parts[0].strip()
                last_name = ' '.join(parts[1:]).strip()
            else:
                first_name = ""
                last_name = name.strip()

        # Clean and format full name
        full_name = f"{last_name}, {first_name}".strip(', ')

        return patient_id, first_name, last_name, full_name

    def find_or_create_patient(self, patient_id: Optional[int], patient_name: str,
                              insurance_type: str = None) -> int:
        """Find existing patient or create new one. Returns patient_id."""
        pid, first_name, last_name, full_name = self.extract_patient_id_from_name(patient_name)

        # Use provided patient_id if available, otherwise use extracted
        if patient_id is None:
            patient_id = pid

        try:
            with self.get_database_connection() as conn:
                cursor = conn.cursor()

                # Try to find existing patient
                found_patient_id = None

                # First try exact patient_id match
                if patient_id:
                    cursor.execute(
                        "SELECT patient_id FROM patients WHERE patient_id = ?",
                        (patient_id,)
                    )
                    result = cursor.fetchone()
                    if result:
                        found_patient_id = result[0]
                        self.stats['patients_matched'] += 1
                        self.logger.debug(f"Found patient by ID: {patient_id}")

                # If not found by ID, try fuzzy name matching
                if not found_patient_id and self.config['processing'].get('fuzzy_matching', True):
                    cursor.execute(
                        "SELECT patient_id, patient_name FROM patients WHERE last_name = ? OR first_name = ?",
                        (last_name, first_name)
                    )
                    candidates = cursor.fetchall()

                    if candidates:
                        threshold = self.config['processing'].get('name_match_threshold', 0.85)
                        best_match = None
                        best_score = 0

                        for candidate_id, candidate_name in candidates:
                            score = fuzz.ratio(full_name.lower(), candidate_name.lower()) / 100.0
                            if score > best_score and score >= threshold:
                                best_score = score
                                best_match = candidate_id

                        if best_match:
                            found_patient_id = best_match
                            self.stats['patients_matched'] += 1
                            self.logger.debug(f"Found patient by fuzzy match: {best_match} (score: {best_score:.2f})")

                # If still not found, create new patient
                if not found_patient_id:
                    if not patient_id:
                        # Generate new patient_id
                        cursor.execute("SELECT MAX(patient_id) FROM patients")
                        max_id = cursor.fetchone()[0]
                        patient_id = (max_id or 0) + 1

                    cursor.execute("""
                        INSERT OR REPLACE INTO patients (
                            patient_id, patient_name, first_name, last_name,
                            insurance_type, status, created_by
                        ) VALUES (?, ?, ?, ?, ?, 'Active', ?)
                    """, (
                        patient_id, full_name, first_name, last_name,
                        insurance_type, f"ETL_{self.import_batch}"
                    ))

                    found_patient_id = patient_id
                    self.stats['patients_created'] += 1
                    self.logger.info(f"Created new patient: {patient_id} - {full_name}")

                conn.commit()
                return found_patient_id

        except Exception as e:
            self.logger.error(f"Error finding/creating patient {patient_name}: {e}")
            return None

    def process_patient_visits_pdf(self, file_path: str) -> List[Dict]:
        """Extract patient visit data from PDF file."""
        self.logger.info(f"Processing patient visits PDF: {file_path}")
        visits = []

        try:
            # Try pdfplumber first for better text extraction
            with pdfplumber.open(file_path) as pdf:
                all_text = ""
                for page in pdf.pages:
                    all_text += page.extract_text() or ""

            # Parse the text to extract visit information
            visits = self._parse_visits_from_text(all_text, file_path)

            # If pdfplumber doesn't work well, fall back to tabula
            if not visits:
                self.logger.info("Falling back to tabula for table extraction")
                visits = self._extract_visits_with_tabula(file_path)

        except Exception as e:
            self.logger.error(f"Error processing PDF {file_path}: {e}")
            self.logger.error(traceback.format_exc())

        self.logger.info(f"Extracted {len(visits)} visits from {file_path}")
        return visits

    def _parse_visits_from_text(self, text: str, file_path: str) -> List[Dict]:
        """Parse visit data from extracted PDF text."""
        visits = []
        lines = text.split('\n')

        current_patient = None
        current_insurance = None
        current_hic = None

        visit_pattern = re.compile(
            r'(\d{1,2}\/\d{1,2}\/\d{4})\s+(\d+\s*-\s*\w+)\s+([^0-9]+?)\s+(\d+\.?\d*)\s+\$?([\d,]+\.?\d*)'
        )

        patient_pattern = re.compile(r'Patient Name:\s*(.+?)(?:\s+HIC|$)', re.IGNORECASE)
        insurance_pattern = re.compile(r'Insurance:\s*(.+?)(?:\s+|$)', re.IGNORECASE)
        hic_pattern = re.compile(r'HIC/Policy #:\s*(.+?)(?:\s+|$)', re.IGNORECASE)

        for i, line in enumerate(lines):
            line = line.strip()

            # Look for patient information
            patient_match = patient_pattern.search(line)
            if patient_match:
                current_patient = patient_match.group(1).strip()
                continue

            insurance_match = insurance_pattern.search(line)
            if insurance_match:
                current_insurance = insurance_match.group(1).strip()
                continue

            hic_match = hic_pattern.search(line)
            if hic_match:
                current_hic = hic_match.group(1).strip()
                continue

            # Look for visit data
            visit_match = visit_pattern.search(line)
            if visit_match and current_patient:
                try:
                    visit_date = datetime.strptime(visit_match.group(1), '%m/%d/%Y').date()
                    service_info = visit_match.group(2).strip()
                    caregiver = visit_match.group(3).strip()
                    hours = float(visit_match.group(4))
                    amount = float(visit_match.group(5).replace(',', '').replace('$', ''))

                    # Parse service code and description
                    service_parts = service_info.split('-', 1)
                    service_code = service_parts[0].strip()
                    service_desc = service_parts[1].strip() if len(service_parts) > 1 else ""

                    # Map service code to discipline
                    discipline = self.config.get('service_codes', {}).get(service_code, service_desc)

                    visit = {
                        'patient_name': current_patient,
                        'visit_date': visit_date,
                        'service_code': service_code,
                        'service_description': service_desc,
                        'discipline': discipline,
                        'caregiver_name': caregiver,
                        'duration_hours': hours,
                        'charge_amount': amount,
                        'insurance_type': current_insurance,
                        'hic_policy_number': current_hic,
                        'data_source': os.path.basename(file_path)
                    }

                    visits.append(visit)

                except (ValueError, IndexError) as e:
                    self.logger.warning(f"Could not parse visit line: {line} - {e}")
                    continue

        return visits

    def _extract_visits_with_tabula(self, file_path: str) -> List[Dict]:
        """Extract visits using tabula-py as fallback method."""
        visits = []

        try:
            # Extract tables from PDF
            tables = tabula.read_pdf(
                file_path,
                pages='all',
                multiple_tables=True,
                pandas_options={'dtype': str}
            )

            for table in tables:
                if table.empty:
                    continue

                # Try to identify visit data tables
                if self._looks_like_visit_table(table):
                    table_visits = self._parse_visit_table(table, file_path)
                    visits.extend(table_visits)

        except Exception as e:
            self.logger.error(f"Tabula extraction failed: {e}")

        return visits

    def _looks_like_visit_table(self, df: pd.DataFrame) -> bool:
        """Check if DataFrame looks like a visit table."""
        if df.empty or len(df.columns) < 4:
            return False

        # Look for date-like patterns in first column
        first_col = df.iloc[:, 0].astype(str)
        date_count = sum(1 for val in first_col if re.search(r'\d{1,2}\/\d{1,2}\/\d{4}', str(val)))

        return date_count > len(df) * 0.5  # At least 50% of rows have dates

    def _parse_visit_table(self, df: pd.DataFrame, file_path: str) -> List[Dict]:
        """Parse visit data from tabula-extracted table."""
        visits = []

        # This is a simplified parser - you may need to customize based on your PDF format
        for _, row in df.iterrows():
            try:
                if len(row) >= 5:
                    visit = {
                        'visit_date': pd.to_datetime(row.iloc[0]).date(),
                        'service_code': str(row.iloc[1]),
                        'caregiver_name': str(row.iloc[2]),
                        'duration_hours': float(str(row.iloc[3]).replace('h', '')),
                        'charge_amount': float(str(row.iloc[4]).replace('$', '').replace(',', '')),
                        'data_source': os.path.basename(file_path)
                    }
                    visits.append(visit)
            except (ValueError, IndexError):
                continue

        return visits

    def process_ar_detail_pdf(self, file_path: str) -> List[Dict]:
        """Extract accounts receivable data from PDF file."""
        self.logger.info(f"Processing AR detail PDF: {file_path}")
        claims = []

        try:
            with pdfplumber.open(file_path) as pdf:
                all_text = ""
                for page in pdf.pages:
                    all_text += page.extract_text() or ""

            claims = self._parse_ar_from_text(all_text, file_path)

        except Exception as e:
            self.logger.error(f"Error processing AR PDF {file_path}: {e}")

        self.logger.info(f"Extracted {len(claims)} claims from {file_path}")
        return claims

    def _parse_ar_from_text(self, text: str, file_path: str) -> List[Dict]:
        """Parse AR data from extracted PDF text."""
        claims = []
        lines = text.split('\n')

        # Pattern for AR lines - adjust based on your PDF format
        ar_pattern = re.compile(
            r'(.+?)\s+(\d+)\s+(\d{2}\/\d{2}\/\d{4})-(\d{2}\/\d{2}\/\d{4})\s+\$?([\d,]+\.?\d*)\s+\$?([\d,]+\.?\d*)\s+\$?([\d,]+\.?\d*)'
        )

        for line in lines:
            line = line.strip()

            match = ar_pattern.search(line)
            if match:
                try:
                    patient_name = match.group(1).strip()
                    claim_number = match.group(2).strip()
                    period_start = datetime.strptime(match.group(3), '%m/%d/%Y').date()
                    period_end = datetime.strptime(match.group(4), '%m/%d/%Y').date()
                    total_amount = float(match.group(5).replace(',', ''))
                    payments = float(match.group(6).replace(',', ''))
                    balance = float(match.group(7).replace(',', ''))

                    claim = {
                        'patient_name': patient_name,
                        'claim_number': claim_number,
                        'claim_period_start': period_start,
                        'claim_period_end': period_end,
                        'total_amount': total_amount,
                        'posted_payments': payments,
                        'balance': balance,
                        'data_source': os.path.basename(file_path)
                    }

                    claims.append(claim)

                except (ValueError, IndexError) as e:
                    self.logger.warning(f"Could not parse AR line: {line} - {e}")
                    continue

        return claims

    def process_excel_file(self, file_path: str) -> Dict[str, List[Dict]]:
        """Process Excel file and return data by sheet type."""
        self.logger.info(f"Processing Excel file: {file_path}")

        try:
            # Read all sheets
            excel_data = pd.read_excel(file_path, sheet_name=None, dtype=str)

            processed_data = {}

            for sheet_name, df in excel_data.items():
                if df.empty:
                    continue

                # Determine data type based on column names
                columns = [col.lower() for col in df.columns]

                if any(word in ' '.join(columns) for word in ['visit', 'date', 'service']):
                    # Looks like visit data
                    processed_data['visits'] = self._process_visit_sheet(df, file_path)
                elif any(word in ' '.join(columns) for word in ['claim', 'balance', 'payment']):
                    # Looks like claims data
                    processed_data['claims'] = self._process_claims_sheet(df, file_path)
                else:
                    # Generic data processing
                    processed_data[sheet_name] = df.to_dict('records')

            return processed_data

        except Exception as e:
            self.logger.error(f"Error processing Excel file {file_path}: {e}")
            return {}

    def _process_visit_sheet(self, df: pd.DataFrame, file_path: str) -> List[Dict]:
        """Process visit data from Excel sheet."""
        visits = []

        for _, row in df.iterrows():
            try:
                visit = {
                    'patient_name': str(row.get('Patient_Name', row.get('patient_name', ''))),
                    'visit_date': pd.to_datetime(row.get('Visit_Date', row.get('visit_date'))).date(),
                    'service_code': str(row.get('Service_Code', row.get('service_code', ''))),
                    'discipline': str(row.get('Discipline', row.get('discipline', ''))),
                    'caregiver_name': str(row.get('Caregiver', row.get('caregiver_name', ''))),
                    'duration_hours': float(row.get('Hours', row.get('duration_hours', 0))),
                    'charge_amount': float(row.get('Amount', row.get('charge_amount', 0))),
                    'data_source': os.path.basename(file_path)
                }
                visits.append(visit)
            except (ValueError, KeyError):
                continue

        return visits

    def _process_claims_sheet(self, df: pd.DataFrame, file_path: str) -> List[Dict]:
        """Process claims data from Excel sheet."""
        claims = []

        for _, row in df.iterrows():
            try:
                claim = {
                    'patient_name': str(row.get('Patient_Name', row.get('patient_name', ''))),
                    'claim_number': str(row.get('Claim_Number', row.get('claim_number', ''))),
                    'total_amount': float(row.get('Total_Amount', row.get('total_amount', 0))),
                    'balance': float(row.get('Balance', row.get('balance', 0))),
                    'data_source': os.path.basename(file_path)
                }
                claims.append(claim)
            except (ValueError, KeyError):
                continue

        return claims

    def store_visits(self, visits: List[Dict], import_id: int):
        """Store visit records in database."""
        if not visits:
            return

        self.logger.info(f"Storing {len(visits)} visits in database")

        try:
            with self.get_database_connection() as conn:
                cursor = conn.cursor()

                for visit in visits:
                    try:
                        # Find or create patient
                        patient_id = self.find_or_create_patient(
                            visit.get('patient_id'),
                            visit.get('patient_name', ''),
                            visit.get('insurance_type')
                        )

                        if not patient_id:
                            self.logger.error(f"Could not resolve patient for visit: {visit}")
                            self.stats['records_failed'] += 1
                            continue

                        # Check for duplicate visits
                        cursor.execute("""
                            SELECT visit_id FROM visits
                            WHERE patient_id = ? AND visit_date = ? AND service_code = ?
                        """, (patient_id, visit['visit_date'], visit.get('service_code', '')))

                        if cursor.fetchone():
                            self.logger.debug(f"Duplicate visit found, skipping: {visit}")
                            continue

                        # Insert visit
                        cursor.execute("""
                            INSERT INTO visits (
                                patient_id, visit_date, service_code, service_description,
                                discipline, caregiver_name, duration_hours, charge_amount,
                                data_source, import_batch
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            patient_id,
                            visit['visit_date'],
                            visit.get('service_code'),
                            visit.get('service_description'),
                            visit.get('discipline'),
                            visit.get('caregiver_name'),
                            visit.get('duration_hours'),
                            visit.get('charge_amount'),
                            visit.get('data_source'),
                            self.import_batch
                        ))

                        self.stats['records_imported'] += 1

                    except Exception as e:
                        self.logger.error(f"Error storing visit: {visit} - {e}")
                        self.stats['records_failed'] += 1
                        continue

                conn.commit()

        except Exception as e:
            self.logger.error(f"Database error storing visits: {e}")

    def store_claims(self, claims: List[Dict], import_id: int):
        """Store claims records in database."""
        if not claims:
            return

        self.logger.info(f"Storing {len(claims)} claims in database")

        try:
            with self.get_database_connection() as conn:
                cursor = conn.cursor()

                for claim in claims:
                    try:
                        # Find or create patient
                        patient_id = self.find_or_create_patient(
                            claim.get('patient_id'),
                            claim.get('patient_name', '')
                        )

                        if not patient_id:
                            self.logger.error(f"Could not resolve patient for claim: {claim}")
                            self.stats['records_failed'] += 1
                            continue

                        # Insert or update claim
                        cursor.execute("""
                            INSERT OR REPLACE INTO claims (
                                claim_number, patient_id, claim_period_start, claim_period_end,
                                total_amount, posted_payments, balance, data_source, import_batch
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            claim.get('claim_number'),
                            patient_id,
                            claim.get('claim_period_start'),
                            claim.get('claim_period_end'),
                            claim.get('total_amount'),
                            claim.get('posted_payments'),
                            claim.get('balance'),
                            claim.get('data_source'),
                            self.import_batch
                        ))

                        self.stats['records_imported'] += 1

                    except Exception as e:
                        self.logger.error(f"Error storing claim: {claim} - {e}")
                        self.stats['records_failed'] += 1
                        continue

                conn.commit()

        except Exception as e:
            self.logger.error(f"Database error storing claims: {e}")

    def update_monthly_summaries(self):
        """Update pre-aggregated monthly summary tables."""
        self.logger.info("Updating monthly summaries")

        try:
            with self.get_database_connection() as conn:
                cursor = conn.cursor()

                # Clear and rebuild monthly summaries for affected months
                cursor.execute("""
                    DELETE FROM monthly_summaries
                    WHERE month_year IN (
                        SELECT DISTINCT strftime('%Y-%m', visit_date)
                        FROM visits
                        WHERE import_batch = ?
                    )
                """, (self.import_batch,))

                # Rebuild monthly summaries
                cursor.execute("""
                    INSERT INTO monthly_summaries (
                        patient_id, month_year, total_visits, total_hours, total_charges,
                        sn_visits, sn_hours, hha_visits, hha_hours, pt_visits, pt_hours,
                        ot_visits, ot_hours, st_visits, st_hours, msw_visits, msw_hours
                    )
                    SELECT
                        patient_id,
                        strftime('%Y-%m', visit_date) as month_year,
                        COUNT(*) as total_visits,
                        SUM(duration_hours) as total_hours,
                        SUM(charge_amount) as total_charges,
                        SUM(CASE WHEN discipline = 'SN' THEN 1 ELSE 0 END) as sn_visits,
                        SUM(CASE WHEN discipline = 'SN' THEN duration_hours ELSE 0 END) as sn_hours,
                        SUM(CASE WHEN discipline = 'HHA' THEN 1 ELSE 0 END) as hha_visits,
                        SUM(CASE WHEN discipline = 'HHA' THEN duration_hours ELSE 0 END) as hha_hours,
                        SUM(CASE WHEN discipline = 'PT' THEN 1 ELSE 0 END) as pt_visits,
                        SUM(CASE WHEN discipline = 'PT' THEN duration_hours ELSE 0 END) as pt_hours,
                        SUM(CASE WHEN discipline = 'OT' THEN 1 ELSE 0 END) as ot_visits,
                        SUM(CASE WHEN discipline = 'OT' THEN duration_hours ELSE 0 END) as ot_hours,
                        SUM(CASE WHEN discipline = 'ST' THEN 1 ELSE 0 END) as st_visits,
                        SUM(CASE WHEN discipline = 'ST' THEN duration_hours ELSE 0 END) as st_hours,
                        SUM(CASE WHEN discipline = 'MSW' THEN 1 ELSE 0 END) as msw_visits,
                        SUM(CASE WHEN discipline = 'MSW' THEN duration_hours ELSE 0 END) as msw_hours
                    FROM visits
                    GROUP BY patient_id, strftime('%Y-%m', visit_date)
                """)

                conn.commit()
                self.logger.info("Monthly summaries updated successfully")

        except Exception as e:
            self.logger.error(f"Error updating monthly summaries: {e}")

    def process_directory(self, directory_path: str, file_patterns: List[str] = None):
        """Process all files in a directory matching specified patterns."""
        if not os.path.exists(directory_path):
            self.logger.error(f"Directory does not exist: {directory_path}")
            return

        # Default patterns
        if file_patterns is None:
            file_patterns = ['*.pdf', '*.xlsx', '*.xls']

        processed_files = []

        for pattern in file_patterns:
            for file_path in Path(directory_path).glob(pattern):
                try:
                    self.process_file(str(file_path))
                    processed_files.append(str(file_path))
                except Exception as e:
                    self.logger.error(f"Error processing {file_path}: {e}")

        self.logger.info(f"Processed {len(processed_files)} files from {directory_path}")
        return processed_files

    def process_file(self, file_path: str):
        """Process a single file based on its type and content."""
        file_ext = Path(file_path).suffix.lower()
        file_name = os.path.basename(file_path)

        self.logger.info(f"Processing file: {file_name}")

        # Start import log
        import_id = self.start_import_log(file_name, file_path, file_ext)

        try:
            if file_ext == '.pdf':
                # Determine PDF type based on filename
                filename_lower = file_name.lower().replace(' ', '_').replace('-', '_')
                if any(pattern in filename_lower for pattern in ['patient_visits', 'visits_list', 'patient_visits_list']):
                    visits = self.process_patient_visits_pdf(file_path)
                    self.stats['records_read'] += len(visits)
                    self.store_visits(visits, import_id)
                elif any(pattern in filename_lower for pattern in ['ar_by_claim', 'claim_detail', 'ar_detail']):
                    claims = self.process_ar_detail_pdf(file_path)
                    self.stats['records_read'] += len(claims)
                    self.store_claims(claims, import_id)
                else:
                    self.logger.warning(f"Unknown PDF type: {file_name}")
                    self.logger.info(f"Processed filename for matching: {filename_lower}")

            elif file_ext in ['.xlsx', '.xls']:
                excel_data = self.process_excel_file(file_path)

                if 'visits' in excel_data:
                    visits = excel_data['visits']
                    self.stats['records_read'] += len(visits)
                    self.store_visits(visits, import_id)

                if 'claims' in excel_data:
                    claims = excel_data['claims']
                    self.stats['records_read'] += len(claims)
                    self.store_claims(claims, import_id)

            self.stats['files_processed'] += 1
            self.update_import_log(import_id, 'Completed')

        except Exception as e:
            self.logger.error(f"Error processing {file_path}: {e}")
            self.logger.error(traceback.format_exc())
            self.update_import_log(import_id, 'Failed', str(e))

    def run_pipeline(self, input_dir: str = None, month: str = None):
        """Run the complete ETL pipeline."""
        self.logger.info("Starting ETL Pipeline")
        self.logger.info(f"Batch ID: {self.import_batch}")

        try:
            # Determine input directory
            if input_dir is None:
                pdf_dir = self.config['input_files'].get('pdf_directory', 'data/pdfs/')
                excel_dir = self.config['input_files'].get('excel_directory', 'data/excel/')
            else:
                pdf_dir = input_dir
                excel_dir = input_dir

            # Process PDF files
            if os.path.exists(pdf_dir):
                self.process_directory(pdf_dir, ['*.pdf'])

            # Process Excel files
            if os.path.exists(excel_dir):
                self.process_directory(excel_dir, ['*.xlsx', '*.xls'])

            # Update monthly summaries
            self.update_monthly_summaries()

            # Print summary
            self.print_summary()

        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}")
            self.logger.error(traceback.format_exc())
            raise

    def print_summary(self):
        """Print processing summary."""
        duration = datetime.now() - self.stats['start_time']

        print("\n" + "="*60)
        print("ETL PIPELINE SUMMARY")
        print("="*60)
        print(f"Batch ID: {self.import_batch}")
        print(f"Duration: {duration}")
        print(f"Files Processed: {self.stats['files_processed']}")
        print(f"Records Read: {self.stats['records_read']}")
        print(f"Records Imported: {self.stats['records_imported']}")
        print(f"Records Failed: {self.stats['records_failed']}")
        print(f"Patients Matched: {self.stats['patients_matched']}")
        print(f"Patients Created: {self.stats['patients_created']}")

        if self.stats['records_read'] > 0:
            success_rate = (self.stats['records_imported'] / self.stats['records_read']) * 100
            print(f"Success Rate: {success_rate:.1f}%")

        print("="*60)


def main():
    """Main entry point for ETL pipeline."""
    parser = argparse.ArgumentParser(description='Home Health Agency ETL Pipeline')
    parser.add_argument('--config', default='config.yaml', help='Configuration file path')
    parser.add_argument('--input-dir', help='Input directory path')
    parser.add_argument('--month', help='Month to process (YYYY-MM)')
    parser.add_argument('--process-all', action='store_true', help='Process all available data')
    parser.add_argument('--file', help='Process single file')

    args = parser.parse_args()

    try:
        # Initialize ETL pipeline
        etl = HomeHealthETL(args.config)

        if args.file:
            # Process single file
            etl.process_file(args.file)
        else:
            # Run full pipeline
            etl.run_pipeline(args.input_dir, args.month)

        print("\nETL Pipeline completed successfully!")

    except Exception as e:
        print(f"ETL Pipeline failed: {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())