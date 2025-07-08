import mysql.connector
from mysql.connector import Error
import config  # Make sure you have DB_HOST, DB_USER, etc., defined in this config file

class Database:
    def __init__(self):
        self.connection = None
        self.connect()
        
    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=config.DB_HOST,
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                database=config.DB_NAME
            )
            print("Database connection established")
        except Error as e:
            print(f"Error connecting to MySQL: {e}")

    def ensure_connection(self):
        """Reconnect if connection is lost"""
        if self.connection is None or not self.connection.is_connected():
            print("🔄 Reconnecting to MySQL...")
            self.connect()

    def get_cursor(self, dictionary=False):
        self.ensure_connection()
        return self.connection.cursor(dictionary=dictionary)        
    
    def create_tables(self):
       if not self.connection:
          print("❌ Cannot create tables: No database connection.")
          return

       cursor = None
       try:
         cursor = self.connection.cursor()

            # Users table
         cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                email VARCHAR(100) NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            # Devices table
         cursor.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                device_name VARCHAR(100) NOT NULL,
                device_id VARCHAR(50) NOT NULL UNIQUE,
                location VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """)

            # Chargers table
         cursor.execute("""
            CREATE TABLE IF NOT EXISTS chargers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                device_id INT NOT NULL,
                charger_name VARCHAR(50) NOT NULL,
                charger_type VARCHAR(50),
                max_power FLOAT,
                status VARCHAR(20) DEFAULT 'inactive',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (device_id) REFERENCES devices(id),
                UNIQUE KEY unique_charger (device_id, charger_name)
            )
            """)

            # Charging sessions table
         cursor.execute("""
            CREATE TABLE IF NOT EXISTS charging_sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                charger_id INT NOT NULL,
                user_id INT,
                start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                end_time TIMESTAMP NULL,
                amount_paid FLOAT,
                energy_consumed FLOAT,
                payment_status VARCHAR(20),
                payment_method VARCHAR(50),
                transaction_id VARCHAR(100),
                FOREIGN KEY (charger_id) REFERENCES chargers(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
            """)

            # Meter readings table
         cursor.execute("""
            CREATE TABLE IF NOT EXISTS meter_readings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                charger_id INT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                voltage FLOAT,
                current FLOAT,
                power_factor FLOAT,
                frequency FLOAT,
                energy FLOAT,
                FOREIGN KEY (charger_id) REFERENCES chargers(id)
            )
            """)

         self.connection.commit()
       except Error as e:
            print(f"Error creating tables: {e}")
       finally:
            if cursor:
                cursor.close()
    
    def add_charging_session(self, charger_id, user_id=None, amount_paid=0, energy_consumed=0, 
                             payment_status='pending', payment_method='razorpay', transaction_id=None):
        try:
            cursor = self.connection.cursor()
            query = """
            INSERT INTO charging_sessions 
            (charger_id, user_id, amount_paid, energy_consumed, payment_status, payment_method, transaction_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (charger_id, user_id, amount_paid, energy_consumed, 
                                   payment_status, payment_method, transaction_id))
            self.connection.commit()
            return cursor.lastrowid
        except Error as e:
            print(f"Error adding charging session: {e}")
            return None
    
    def update_charging_session(self, session_id, end_time=None, energy_consumed=None, 
                                 payment_status=None):
        try:
            cursor = self.connection.cursor()
            query = "UPDATE charging_sessions SET "
            params = []
            
            if end_time:
                query += "end_time = %s, "
                params.append(end_time)
            if energy_consumed:
                query += "energy_consumed = %s, "
                params.append(energy_consumed)
            if payment_status:
                query += "payment_status = %s, "
                params.append(payment_status)
                
            query = query.rstrip(", ") + " WHERE id = %s"
            params.append(session_id)
            
            cursor.execute(query, params)
            self.connection.commit()
            return True
        except Error as e:
            print(f"Error updating charging session: {e}")
            return False
    
    def add_meter_reading(self, charger_id, voltage=None, current=None, 
                           power_factor=None, frequency=None, energy=None):
        try:
            cursor = self.connection.cursor()
            query = """
            INSERT INTO meter_readings 
            (charger_id, voltage, current, power_factor, frequency, energy)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (charger_id, voltage, current, 
                                   power_factor, frequency, energy))
            self.connection.commit()
            return True
        except Error as e:
            print(f"Error adding meter reading: {e}")
            return False
    
    def get_charger_id(self, device_id, charger_name):
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = """
            SELECT c.id 
            FROM chargers c
            JOIN devices d ON c.device_id = d.id
            WHERE d.device_id = %s AND c.charger_name = %s
            """
            cursor.execute(query, (device_id, charger_name))
            result = cursor.fetchone()
            return result['id'] if result else None
        except Error as e:
            print(f"Error getting charger ID: {e}")
            return None
    
    def get_charging_sessions(self, device_id, limit=50):
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = """
            SELECT cs.*, c.charger_name, d.device_name
            FROM charging_sessions cs
            JOIN chargers c ON cs.charger_id = c.id
            JOIN devices d ON c.device_id = d.id
            WHERE d.device_id = %s
            ORDER BY cs.start_time DESC
            LIMIT %s
            """
            cursor.execute(query, (device_id, limit))
            return cursor.fetchall()
        except Error as e:
            print(f"Error getting charging sessions: {e}")
            return []
    
    def get_meter_readings(self, charger_id, limit=100):
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = """
            SELECT * FROM meter_readings
            WHERE charger_id = %s
            ORDER BY timestamp DESC
            LIMIT %s
            """
            cursor.execute(query, (charger_id, limit))
            return cursor.fetchall()
        except Error as e:
            print(f"Error getting meter readings: {e}")
            return []
    
    def close(self):
        if self.connection:
            self.connection.close()
            print("Database connection closed")

# ✅ Initialize and create tables
db = Database()
db.create_tables()
