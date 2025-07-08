from flask import Blueprint, jsonify
from database import db  # your shared db connection

charts_bp = Blueprint('charts', __name__)

@charts_bp.route('/api/chart-data')
def chart_data():
    cursor = db.connection.cursor()

    # 1. Charger status counts
    cursor.execute("SELECT status, COUNT(*) AS count FROM chargers GROUP BY status")
    status_rows = cursor.fetchall()
    status_counts = [{'status': row[0], 'count': row[1]} for row in status_rows]

    # 2. Energy usage (past 7 days)
    cursor.execute("""
        SELECT DATE(timestamp) AS date, SUM(energy) AS total_energy
        FROM meter_readings
        WHERE timestamp >= NOW() - INTERVAL 7 DAY
        GROUP BY DATE(timestamp)
        ORDER BY DATE(timestamp)
    """)
    energy_rows = cursor.fetchall()
    energy_data = [{'date': str(row[0]), 'total_energy': float(row[1]) if row[1] is not None else 0.0} for row in energy_rows]

    # 3. Revenue (past 7 days)
    cursor.execute("""
        SELECT DATE(start_time) AS date, SUM(amount_paid) AS total_revenue
        FROM charging_sessions
        WHERE start_time >= NOW() - INTERVAL 7 DAY AND payment_status = 'paid'
        GROUP BY DATE(start_time)
        ORDER BY DATE(start_time)
    """)
    revenue_rows = cursor.fetchall()
    revenue_data = [{'date': str(row[0]), 'total_revenue': float(row[1]) if row[1] is not None else 0.0} for row in revenue_rows]

    cursor.close()

    return jsonify({
        "status_counts": status_counts,
        "energy_data": energy_data,
        "revenue_data": revenue_data
    })