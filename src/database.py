#!/usr/bin/env python3
"""
Voiseege Database Module - SQLite implementation with WAL mode
"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./logs/database.log'),
        logging.StreamHandler()
    ]
)

class DatabaseManager:
    def __init__(self, db_path="./db/voiseege.db"):
        self.db_path = db_path
        self.connection = None
        self.init_database()
        
    def init_database(self):
        """Initialize the database connection and create tables if they don't exist"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            
            # Enable WAL mode for better concurrency
            self.connection.execute("PRAGMA journal_mode=WAL")
            
            # Create tables
            self.create_tables()
            
            logging.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logging.error(f"Failed to initialize database: {e}")
            raise

    def create_tables(self):
        """Create all required database tables"""
        cursor = self.connection.cursor()
        
        # Raw audio recordings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS raw_audio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                filepath TEXT NOT NULL,
                recording_start TEXT NOT NULL,
                duration REAL NOT NULL,
                shabbat_mode BOOLEAN NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Transcripts table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transcripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audio_id INTEGER,
                transcript TEXT,
                language TEXT,
                confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (audio_id) REFERENCES raw_audio (id)
            )
        ''')
        
        # Congregants table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS congregants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                photo_path TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Aliyah sales table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS aliyah_sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                congregant_id INTEGER,
                aliyah_type TEXT NOT NULL,
                amount REAL,
                timestamp TEXT NOT NULL,
                audio_id INTEGER,
                transcript_id INTEGER,
                audio_clip_path TEXT,
                confidence REAL,
                verified BOOLEAN DEFAULT FALSE,
                verifier_id INTEGER,
                verification_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (congregant_id) REFERENCES congregants (id),
                FOREIGN KEY (audio_id) REFERENCES raw_audio (id),
                FOREIGN KEY (transcript_id) REFERENCES transcripts (id)
            )
        ''')
        
        # Verification log table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS verification_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                aliyah_sale_id INTEGER,
                verifier_id INTEGER,
                action TEXT NOT NULL, -- 'verified', 'rejected', 'modified'
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (aliyah_sale_id) REFERENCES aliyah_sales (id)
            )
        ''')
        
        self.connection.commit()
        logging.info("Database tables created successfully")

    def insert_raw_audio(self, filename, filepath, recording_start, duration, shabbat_mode):
        """Insert a new raw audio recording record"""
        cursor = self.connection.cursor()
        cursor.execute('''
            INSERT INTO raw_audio (filename, filepath, recording_start, duration, shabbat_mode)
            VALUES (?, ?, ?, ?, ?)
        ''', (filename, filepath, recording_start, duration, shabbat_mode))
        
        self.connection.commit()
        return cursor.lastrowid

    def insert_transcript(self, audio_id, transcript, language, confidence):
        """Insert a new transcript record"""
        cursor = self.connection.cursor()
        cursor.execute('''
            INSERT INTO transcripts (audio_id, transcript, language, confidence)
            VALUES (?, ?, ?, ?)
        ''', (audio_id, transcript, language, confidence))
        
        self.connection.commit()
        return cursor.lastrowid

    def insert_congregant(self, name, email=None, phone=None, photo_path=None, notes=None):
        """Insert a new congregant record"""
        cursor = self.connection.cursor()
        cursor.execute('''
            INSERT INTO congregants (name, email, phone, photo_path, notes, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (name, email, phone, photo_path, notes))

        self.connection.commit()
        return cursor.lastrowid

    def update_congregant_photo(self, congregant_id, photo_path):
        """Update congregant photo"""
        cursor = self.connection.cursor()
        cursor.execute('''
            UPDATE congregants
            SET photo_path = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (photo_path, congregant_id))

        self.connection.commit()
        return cursor.rowcount > 0

    def insert_aliyah_sale(self, congregant_id, aliyah_type, amount, timestamp,
                          audio_id, transcript_id, confidence, verified=False,
                          verifier_id=None, verification_notes=None, audio_clip_path=None):
        """Insert a new aliyah sale record"""
        cursor = self.connection.cursor()
        cursor.execute('''
            INSERT INTO aliyah_sales (
                congregant_id, aliyah_type, amount, timestamp,
                audio_id, transcript_id, audio_clip_path, confidence, verified,
                verifier_id, verification_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (congregant_id, aliyah_type, amount, timestamp,
              audio_id, transcript_id, audio_clip_path, confidence, verified,
              verifier_id, verification_notes))

        self.connection.commit()
        return cursor.lastrowid

    def insert_verification_log(self, aliyah_sale_id, verifier_id, action, notes=None):
        """Insert a new verification log record"""
        cursor = self.connection.cursor()
        cursor.execute('''
            INSERT INTO verification_log (aliyah_sale_id, verifier_id, action, notes)
            VALUES (?, ?, ?, ?)
        ''', (aliyah_sale_id, verifier_id, action, notes))
        
        self.connection.commit()
        return cursor.lastrowid

    def get_unverified_aliyah_sales(self):
        """Get all unverified aliyah sales for review"""
        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT * FROM aliyah_sales 
            WHERE verified = FALSE
            ORDER BY created_at DESC
        ''')
        return cursor.fetchall()

    def get_aliyah_sales_with_audio(self):
        """Get all aliyah sales with associated audio and transcript info"""
        cursor = self.connection.cursor()
        cursor.execute('''
            SELECT 
                a.id,
                a.aliyah_type,
                a.amount,
                a.timestamp,
                a.confidence,
                a.verified,
                c.name as congregant_name,
                r.filename as audio_filename,
                t.transcript
            FROM aliyah_sales a
            LEFT JOIN congregants c ON a.congregant_id = c.id
            LEFT JOIN raw_audio r ON a.audio_id = r.id
            LEFT JOIN transcripts t ON a.transcript_id = t.id
            ORDER BY a.created_at DESC
        ''')
        return cursor.fetchall()

    def close(self):
        """Close the database connection"""
        if self.connection:
            self.connection.close()
            logging.info("Database connection closed")


# Example usage
if __name__ == "__main__":
    db = DatabaseManager()
    logging.info("Database module test completed")
    db.close()