#!/usr/bin/env python3
"""
Voiseege Dashboard Backend API
Provides REST API for viewing and verifying aliyah sales
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# Import our modules
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from database import DatabaseManager
from shabbat_manager import ShabbatManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./logs/dashboard.log'),
        logging.StreamHandler()
    ]
)

def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    CORS(app)  # Enable CORS for all routes

    # Initialize database and Shabbat manager
    db = DatabaseManager()
    shabbat_manager = ShabbatManager()
    
    @app.route('/api/status', methods=['GET'])
    def get_system_status():
        """Get overall system status including Shabbat status"""
        shabbat_status = shabbat_manager.get_current_shabbat_status()
        
        # Get some basic stats
        cursor = db.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM raw_audio")
        total_recordings = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM aliyah_sales")
        total_sales = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM aliyah_sales WHERE verified = FALSE")
        unverified_sales = cursor.fetchone()[0]
        
        status = {
            "shabbat_status": shabbat_status,
            "system_stats": {
                "total_recordings": total_recordings,
                "total_sales": total_sales,
                "unverified_sales": unverified_sales
            },
            "timestamp": datetime.now().isoformat()
        }
        
        return jsonify(status)
    
    @app.route('/api/aliyah-sales', methods=['GET'])
    def get_aliyah_sales():
        """Get all aliyah sales with optional filtering"""
        # Check query parameters
        verified_filter = request.args.get('verified')
        limit = request.args.get('limit', default=50, type=int)
        offset = request.args.get('offset', default=0, type=int)
        
        cursor = db.connection.cursor()
        
        # Base query
        query = '''
            SELECT 
                a.id,
                a.aliyah_type,
                a.amount,
                a.timestamp,
                a.confidence,
                a.verified,
                a.created_at,
                c.name as congregant_name,
                r.filename as audio_filename,
                t.transcript
            FROM aliyah_sales a
            LEFT JOIN congregants c ON a.congregant_id = c.id
            LEFT JOIN raw_audio r ON a.audio_id = r.id
            LEFT JOIN transcripts t ON a.transcript_id = t.id
        '''
        
        # Add filters
        conditions = []
        params = []
        
        if verified_filter is not None:
            if verified_filter.lower() in ['true', '1']:
                conditions.append("a.verified = 1")
            else:
                conditions.append("a.verified = 0")
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY a.created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        # Convert to list of dicts
        sales = []
        for row in results:
            sale = {
                "id": row[0],
                "aliyah_type": row[1],
                "amount": row[2],
                "timestamp": row[3],
                "confidence": row[4],
                "verified": bool(row[5]),
                "created_at": row[6],
                "congregant_name": row[7],
                "audio_filename": row[8],
                "transcript": row[9]
            }
            sales.append(sale)
        
        return jsonify(sales)
    
    @app.route('/api/aliyah-sales/<int:sale_id>', methods=['GET'])
    def get_aliyah_sale(sale_id):
        """Get a specific aliyah sale by ID"""
        cursor = db.connection.cursor()
        
        query = '''
            SELECT 
                a.id,
                a.aliyah_type,
                a.amount,
                a.timestamp,
                a.confidence,
                a.verified,
                a.created_at,
                c.name as congregant_name,
                r.filename as audio_filename,
                t.transcript
            FROM aliyah_sales a
            LEFT JOIN congregants c ON a.congregant_id = c.id
            LEFT JOIN raw_audio r ON a.audio_id = r.id
            LEFT JOIN transcripts t ON a.transcript_id = t.id
            WHERE a.id = ?
        '''
        
        cursor.execute(query, (sale_id,))
        result = cursor.fetchone()
        
        if result is None:
            return jsonify({"error": "Sale not found"}), 404
        
        sale = {
            "id": result[0],
            "aliyah_type": result[1],
            "amount": result[2],
            "timestamp": result[3],
            "confidence": result[4],
            "verified": bool(result[5]),
            "created_at": result[6],
            "congregant_name": result[7],
            "audio_filename": result[8],
            "transcript": result[9]
        }
        
        return jsonify(sale)
    
    @app.route('/api/aliyah-sales/<int:sale_id>/verify', methods=['POST'])
    def verify_aliyah_sale(sale_id):
        """Verify or reject an aliyah sale"""
        # Check if it's currently Shabbat - verification not allowed during Shabbat
        if shabbat_manager.is_currently_shabbat():
            return jsonify({"error": "Verification not allowed during Shabbat"}), 400
        
        data = request.get_json()
        if not data or 'verified' not in data:
            return jsonify({"error": "Missing 'verified' field in request"}), 400
        
        verified = data['verified']
        notes = data.get('notes', '')
        
        cursor = db.connection.cursor()
        
        # Update the sale verification status
        cursor.execute('''
            UPDATE aliyah_sales 
            SET verified = ?, verification_notes = ?
            WHERE id = ?
        ''', (verified, notes, sale_id))
        
        if cursor.rowcount == 0:
            return jsonify({"error": "Sale not found"}), 404
        
        # Log the verification action
        verifier_id = data.get('verifier_id', 0)  # In a real system, you'd have auth
        action = 'verified' if verified else 'rejected'
        
        db.insert_verification_log(sale_id, verifier_id, action, notes)
        
        db.connection.commit()
        
        return jsonify({"message": f"Sale {'verified' if verified else 'rejected'} successfully"})
    
    @app.route('/api/congregants', methods=['GET'])
    def get_congregants():
        """Get all congregants"""
        cursor = db.connection.cursor()
        cursor.execute("SELECT id, name, email, phone, created_at FROM congregants ORDER BY name")
        results = cursor.fetchall()
        
        congregants = []
        for row in results:
            congregant = {
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "phone": row[3],
                "created_at": row[4]
            }
            congregants.append(congregant)
        
        return jsonify(congregants)
    
    @app.route('/api/congregants', methods=['POST'])
    def create_congregant():
        """Create a new congregant"""
        data = request.get_json()
        
        if not data or 'name' not in data:
            return jsonify({"error": "Missing 'name' field in request"}), 400
        
        name = data['name']
        email = data.get('email')
        phone = data.get('phone')
        
        congregant_id = db.insert_congregant(name, email, phone)
        
        return jsonify({"id": congregant_id, "message": "Congregant created successfully"}), 201
    
    @app.route('/api/audio/<filename>', methods=['GET'])
    def get_audio_file(filename):
        """Serve audio files"""
        try:
            # Security check: ensure filename doesn't contain path traversal
            if '..' in filename or filename.startswith('/'):
                return jsonify({"error": "Invalid filename"}), 400

            # Use the default audio directory
            audio_dir = Path('./audio/')
            file_path = audio_dir / filename

            if not file_path.exists():
                return jsonify({"error": "File not found"}), 404

            return send_from_directory(str(audio_dir), filename)
        except Exception as e:
            logging.error(f"Error serving audio file {filename}: {e}")
            return jsonify({"error": "Internal server error"}), 500
    
    @app.route('/api/shabbat-status', methods=['GET'])
    def get_shabbat_status():
        """Get current Shabbat status"""
        status = shabbat_manager.get_current_shabbat_status()
        return jsonify(status)
    
    @app.route('/', methods=['GET'])
    def index():
        """Serve the main dashboard page"""
        return send_from_directory(app.template_folder, 'index.html')

    @app.route('/api/unverified-sales-count', methods=['GET'])
    def get_unverified_sales_count():
        """Get count of unverified sales"""
        cursor = db.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM aliyah_sales WHERE verified = FALSE")
        count = cursor.fetchone()[0]
        return jsonify({"unverified_count": count})
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found"}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"error": "Internal server error"}), 500
    
    return app

# For direct execution
if __name__ == "__main__":
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False)