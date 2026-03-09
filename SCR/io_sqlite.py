import sqlite3
import logging
import os
import numpy as np
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def create_scores_table(db_path):
    """Create the scores table if it doesn't exist"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_conf TEXT NOT NULL,
            model_init TEXT NOT NULL,
            accumulation_duration INTEGER NOT NULL,
            start_accumulation_period TEXT NOT NULL,
            experiment_name TEXT NOT NULL,
            subdomain TEXT NOT NULL,
            lead INTEGER,
            name TEXT,
            maximum REAL,
            average REAL,
            percentile_99 REAL,
            percentile_95 REAL,
            percentile_90 REAL,
            percentile_75 REAL,
            percentile_50 REAL,
            bias REAL,
            mae REAL,
            rms REAL,
            correlation REAL,
            d90 REAL,
            fss_condensed REAL,
            fss_condensed_weighted REAL,
            rank_mae INTEGER,
            rank_bias INTEGER,
            rank_rms INTEGER,
            rank_corr INTEGER,
            rank_d90 INTEGER,
            rank_fss_condensed INTEGER,
            rank_fss_condensed_weighted INTEGER,
            fss_netcdf_reference TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(model_conf, model_init, accumulation_duration, start_accumulation_period, experiment_name, subdomain)
        )
    ''')
    
    conn.commit()
    conn.close()


def check_duplicate_entry(db_path, model_conf, model_init, accumulation_duration, 
                          start_accumulation_period, experiment_name, subdomain):
    """Check if an entry already exists with the same unique identifier"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id FROM scores
        WHERE model_conf = ? AND model_init = ? AND accumulation_duration = ? 
        AND start_accumulation_period = ? AND experiment_name = ? AND subdomain = ?
    ''', (model_conf, model_init, accumulation_duration, start_accumulation_period, 
          experiment_name, subdomain))
    
    existing = cursor.fetchone()
    conn.close()
    return existing is not None


def insert_scores(db_path, model_conf, model_init, accumulation_duration, start_accumulation_period, 
                  experiment_name, subdomain, sim_data, fss_netcdf_ref=None):
    """Insert scores into the database
    
    Args:
        db_path: Path to the sqlite database
        model_conf: Model configuration tuple/string
        model_init: Model initialization datetime as string
        accumulation_duration: Duration of accumulation in hours
        start_accumulation_period: Start of accumulation period as string
        experiment_name: Name of the experiment
        subdomain: Name of the verification subdomain
        sim_data: Dictionary containing the simulation data with keys from sim dict
        fss_netcdf_ref: Optional path/reference to the FSS netCDF file
    """
    
    # Check for duplicate entry
    if check_duplicate_entry(db_path, model_conf, model_init, accumulation_duration,
                             start_accumulation_period, experiment_name, subdomain):
        logger.critical(f"Entry already exists in database for model_conf={model_conf}, "
                       f"model_init={model_init}, accumulation_duration={accumulation_duration}h, "
                       f"start_accumulation_period={start_accumulation_period}, "
                       f"experiment_name={experiment_name}, subdomain={subdomain}. "
                       f"This would cause data to be overwritten. Aborting!")
        raise ValueError("Duplicate entry detected - would cause data overwrite")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO scores (
                model_conf, model_init, accumulation_duration, start_accumulation_period,
                experiment_name, subdomain, lead, name, maximum, average, 
                percentile_99, percentile_95, percentile_90, percentile_75, percentile_50,
                bias, mae, rms, correlation, d90, fss_condensed, fss_condensed_weighted,
                rank_mae, rank_bias, rank_rms, rank_corr, rank_d90, 
                rank_fss_condensed, rank_fss_condensed_weighted, fss_netcdf_reference
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                      ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            str(model_conf), model_init, accumulation_duration, start_accumulation_period,
            experiment_name, subdomain, sim_data.get('lead'), sim_data.get('name'),
            sim_data.get('maximum'), sim_data.get('average'),
            sim_data.get('percentile_99'), sim_data.get('percentile_95'), 
            sim_data.get('percentile_90'), sim_data.get('percentile_75'), 
            sim_data.get('percentile_50'),
            sim_data.get('bias_real'), sim_data.get('mae'), sim_data.get('rms'), 
            sim_data.get('corr'), sim_data.get('d90'),
            sim_data.get('fss_condensed'), sim_data.get('fss_condensed_weighted'),
            sim_data.get('rank_mae'), sim_data.get('rank_bias'), sim_data.get('rank_rms'),
            sim_data.get('rank_corr'), sim_data.get('rank_d90'),
            sim_data.get('rank_fss_condensed'), sim_data.get('rank_fss_condensed_weighted'),
            fss_netcdf_ref
        ))
        
        conn.commit()
        logger.info(f"Successfully inserted scores for {sim_data.get('name')}")
        
    except sqlite3.IntegrityError as e:
        logger.critical(f"Integrity error when inserting data: {e}. "
                       f"This indicates duplicate data that would be overwritten. Aborting!")
        conn.close()
        raise
    
    conn.close()


def check_database_exists(db_path):
    """Check if database already exists and log a warning if it does"""
    if os.path.exists(db_path):
        logger.warning(f"Database already exists at {db_path}. "
                      f"New data will be appended to the existing database.")
        return True
    return False


def query_scores(db_path, **filters):
    """Query scores from the database with optional filters
    
    Args:
        db_path: Path to the sqlite database
        **filters: Optional filter criteria (e.g., experiment_name='test', subdomain='Austria')
    
    Returns:
        List of dictionaries containing the queried data
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    query = "SELECT * FROM scores WHERE 1=1"
    params = []
    
    if 'experiment_name' in filters:
        query += " AND experiment_name = ?"
        params.append(filters['experiment_name'])
    if 'subdomain' in filters:
        query += " AND subdomain = ?"
        params.append(filters['subdomain'])
    if 'model_conf' in filters:
        query += " AND model_conf = ?"
        params.append(filters['model_conf'])
    
    cursor.execute(query, params)
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return results
