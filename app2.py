import serial # type: ignore
import time
from datetime import datetime
from sqlalchemy import create_engine, exc # type: ignore
from sqlalchemy.orm import sessionmaker # type: ignore
from app import Slot, User  # Import Slot and User models from your Flask app module

# Database configuration (use the same database URI as your Flask app)
DATABASE_URI = 'sqlite:////Users/jeevanprakash/Documents/TARP/users.db'

# Initialize serial connection
ser = serial.Serial('/dev/cu.usbmodem1101', 9600, timeout=1)
ser.flush()

# Set up database connection
engine = create_engine(DATABASE_URI)
Session = sessionmaker(bind=engine)

def update_slot(slot_number, user_id, booking_method):
    session = Session()
    try:
        slot = session.query(Slot).filter_by(slot_number=slot_number).first()
        if not slot:
            slot = Slot(slot_number=slot_number)
            session.add(slot)
        
        slot.booked = True
        slot.user_id = user_id
        slot.booking_method = booking_method
        slot.booking_time = datetime.utcnow()
        session.commit()
    except exc.SQLAlchemyError as e:
        print(f"Database error: {e}")
    finally:
        session.close()

while True:
    if ser.in_waiting > 0:
        line = ser.readline().decode('utf-8').rstrip()
        print("Received:", line)
        slot_data = line.split(',')
        if len(slot_data) == 2:
            slot_number, status = slot_data
            if status == '1':  # Assuming status '3' means the slot is booked
                # Here you might want to determine the user_id dynamically or based on other conditions
                update_slot(slot_number, user_id=3, booking_method='hardware')
        time.sleep(1)
