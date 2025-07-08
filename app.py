from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash,Blueprint
from werkzeug.security import generate_password_hash, check_password_hash
from database import db
import config
from functools import wraps
from charts import charts_bp 
import datetime

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.register_blueprint(charts_bp)

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def dashboard():
    # Get user's devices
    cursor = db.connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM devices WHERE user_id = %s", (session['user_id'],))
    devices = cursor.fetchall()
    
    # Get recent charging sessions
    charging_sessions = []
    for device in devices:
        cursor.execute("""
            SELECT cs.*, c.charger_name 
            FROM charging_sessions cs
            JOIN chargers c ON cs.charger_id = c.id
            WHERE c.device_id = %s
            ORDER BY cs.start_time DESC
            LIMIT 5
        """, (device['id'],))
        sessions = cursor.fetchall()
        charging_sessions.extend(sessions)
    
    # Get charger status counts
    cursor.execute("""
        SELECT c.status, COUNT(*) as count
        FROM chargers c
        JOIN devices d ON c.device_id = d.id
        WHERE d.user_id = %s
        GROUP BY c.status
    """, (session['user_id'],))
    status_counts = cursor.fetchall()
    
    cursor.close()
    
    return render_template('dashboard.html', 
                         devices=devices,
                         charging_sessions=charging_sessions,
                         status_counts=status_counts)

@app.route('/add_device', methods=['GET', 'POST'])
@login_required
def add_device():
    if request.method == 'POST':
        device_name = request.form['device_name']
        device_id = request.form['device_id']
        location = request.form.get('location', '')
        
        try:
            cursor = db.connection.cursor()
            cursor.execute(
                "INSERT INTO devices (user_id, device_name, device_id, location) VALUES (%s, %s, %s, %s)",
                (session['user_id'], device_name, device_id, location)
            )
            db.connection.commit()
            cursor.close()
            flash('Device added successfully', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f'Error adding device: {str(e)}', 'danger')
    
    return render_template('add_device.html')

@app.route('/device/<device_id>/add_charger', methods=['GET', 'POST'])
@login_required
def add_charger(device_id):
    cursor = db.connection.cursor(dictionary=True)
    
    # Verify device belongs to user
    cursor.execute("""
        SELECT id FROM devices 
        WHERE device_id = %s AND user_id = %s
    """, (device_id, session['user_id']))
    device = cursor.fetchone()
    
    if not device:
        flash('Device not found', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        charger_name = request.form['charger_name']
        charger_type = request.form['charger_type']
        max_power = request.form.get('max_power')
        
        try:
            cursor.execute(
                "INSERT INTO chargers (device_id, charger_name, charger_type, max_power) VALUES (%s, %s, %s, %s)",
                (device['id'], charger_name, charger_type, max_power)
            )
            db.connection.commit()
            flash('Charger added successfully', 'success')
            return redirect(url_for('device_detail', device_id=device_id))
        except Exception as e:
            flash(f'Error adding charger: {str(e)}', 'danger')
    
    cursor.close()
    return render_template('add_charger.html', device_id=device_id)


@app.route('/device/<device_id>')
@login_required
def device_detail(device_id):
    cursor = db.connection.cursor(dictionary=True)
    
    # Verify device belongs to user
    cursor.execute("""
        SELECT d.* 
        FROM devices d
        WHERE d.device_id = %s AND d.user_id = %s
    """, (device_id, session['user_id']))
    device = cursor.fetchone()
    
    if not device:
        flash('Device not found', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get chargers for this device
    cursor.execute("""
        SELECT * FROM chargers
        WHERE device_id = %s
        ORDER BY charger_name
    """, (device['id'],))
    chargers = cursor.fetchall()
    
    # Get recent charging sessions for this device
    cursor.execute("""
        SELECT cs.*, c.charger_name 
        FROM charging_sessions cs
        JOIN chargers c ON cs.charger_id = c.id
        WHERE c.device_id = %s
        ORDER BY cs.start_time DESC
        LIMIT 10
    """, (device['id'],))
    charging_sessions = cursor.fetchall()
    
    cursor.close()
    
    return render_template('device_detail.html', 
                         device=device,
                         chargers=chargers,
                         charging_sessions=charging_sessions)

@app.route('/charger/<charger_id>')
@login_required
def charger_detail(charger_id):
    cursor = db.connection.cursor(dictionary=True)
    
    # Verify charger belongs to user
    cursor.execute("""
        SELECT c.*, d.device_id, d.device_name
        FROM chargers c
        JOIN devices d ON c.device_id = d.id
        WHERE c.id = %s AND d.user_id = %s
    """, (charger_id, session['user_id']))
    charger = cursor.fetchone()
    
    if not charger:
        flash('Charger not found', 'danger')
        return redirect(url_for('dashboard'))
    
    # Get recent charging sessions
    cursor.execute("""
        SELECT * FROM charging_sessions
        WHERE charger_id = %s
        ORDER BY start_time DESC
        LIMIT 10
    """, (charger['id'],))
    charging_sessions = cursor.fetchall()
    
    # Get recent meter readings
    cursor.execute("""
        SELECT * FROM meter_readings
        WHERE charger_id = %s
        ORDER BY timestamp DESC
        LIMIT 100
    """, (charger['id'],))
    meter_readings = cursor.fetchall()
    
    cursor.close()
    
    return render_template('charger_detail.html', 
                         charger=charger,
                         charging_sessions=charging_sessions,
                         meter_readings=meter_readings)

@app.route('/api/charging_start', methods=['POST'])
def api_charging_start():
    data = request.json
    device_id = data.get('device_id')
    charger_name = data.get('charger_name')
    amount = data.get('amount')
    
    # Get charger ID
    charger_id = db.get_charger_id(device_id, charger_name)
    if not charger_id:
        return jsonify({'success': False, 'message': 'Charger not found'}), 404

    # Create charging session
    session_id = db.add_charging_session(
        charger_id=charger_id,
        amount_paid=amount,
        payment_status='pending'
    )

    if session_id:
        try:
            # Update charger status to 'working'
            cursor = db.connection.cursor()
            cursor.execute("UPDATE chargers SET status = 'Active' WHERE id = %s", (charger_id,))
            db.connection.commit()
        except Exception as e:
            return jsonify({'success': False, 'message': 'Session started, but failed to update charger status', 'error': str(e)}), 500

        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': 'Charging session started and charger set to working'
        })
    else:
        return jsonify({'success': False, 'message': 'Failed to start session'}), 500

@app.route('/api/charging_update', methods=['POST'])
def api_charging_update():
    data = request.json
    session_id = data.get('session_id')
    energy_consumed = data.get('energy_consumed')
    payment_status = data.get('payment_status', None)
    
    success = db.update_charging_session(
        session_id=session_id,
        energy_consumed=energy_consumed,
        payment_status=payment_status
    )
    
    if success:
        return jsonify({'success': True, 'message': 'Session updated'})
    else:
        return jsonify({'success': False, 'message': 'Failed to update session'}), 500

@app.route('/api/meter_reading', methods=['POST'])
def api_meter_reading():
    data = request.json
    device_id = data.get('device_id')
    charger_name = data.get('charger_name')
    voltage = data.get('voltage')
    current = data.get('current')
    power_factor = data.get('power_factor')
    frequency = data.get('frequency')
    energy = data.get('energy')
    
    # Get charger ID
    charger_id = db.get_charger_id(device_id, charger_name)
    if not charger_id:
        return jsonify({'success': False, 'message': 'Charger not found'}), 404
    
    # Add meter reading
    success = db.add_meter_reading(
        charger_id=charger_id,
        voltage=voltage,
        current=current,
        power_factor=power_factor,
        frequency=frequency,
        energy=energy
    )
    
    if success:
        return jsonify({'success': True, 'message': 'Meter reading added'})
    else:
        return jsonify({'success': False, 'message': 'Failed to add reading'}), 500

@app.route('/api/meter_readings', methods=['GET'])
def get_meter_readings():
    charger_id = request.args.get('charger_id')
    limit = request.args.get('limit', 20)

    if not charger_id:
        return jsonify({'error': 'Missing charger_id'}), 400

    try:
        limit = int(limit)
    except ValueError:
        limit = 20

    cursor = db.connection.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM meter_readings
        WHERE charger_id = %s
        ORDER BY timestamp DESC
        LIMIT %s
    """, (charger_id, limit))
    readings = cursor.fetchall()
    cursor.close()

    return jsonify(readings)


# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cursor = db.connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Logged in successfully', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        
        try:
            cursor = db.connection.cursor()
            cursor.execute(
                "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                (username, email, password)
            )
            db.connection.commit()
            cursor.close()
            
            flash('Registration successful. Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash('Registration failed. Username or email may already exist.', 'danger')
    
    return render_template('register.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)