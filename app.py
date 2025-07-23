from datetime import datetime
from flask import Flask, get_flashed_messages, jsonify, render_template, request, redirect, url_for, session, flash # type: ignore
from flask_sqlalchemy import SQLAlchemy # type: ignore
from flask_bcrypt import Bcrypt # type: ignore
from geopy.distance import geodesic # type: ignore
from flask_migrate import Migrate # type: ignore
import pytz # type: ignore
import csv
from flask import request # type: ignore



app = Flask(__name__)

# Get the Flask app name
app_name = "StarParkinglot"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////Users/jeevanprakash/Documents/TARP/users.db'
app.config['SECRET_KEY'] = 'your_secret_key'

# Define parking lot location (latitude, longitude)
PARKING_LOT_COORDS = (12.84122730814175, 80.15613704173273)
ALLOWED_RADIUS = 0.5  # radius in kilometers

#13.086090599558995, 80.1815387067288

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
migrate = Migrate(app, db)


# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    vehicle_number = db.Column(db.String(20), unique=True, nullable=True)


# Slot model
class Slot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slot_number = db.Column(db.String(20), unique=True, nullable=False)
    booked = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    booking_time = db.Column(db.DateTime)
    booking_method = db.Column(db.String(20), default="software")  # New column with default value
    end_time = db.Column(db.DateTime, nullable=True)

class SlotHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slot_number = db.Column(db.String(20), nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
    booking_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)




# Create the database tables
with app.app_context():
    db.create_all()

# Function to convert UTC to IST
def utc_to_ist(utc_dt):
    ist_tz = pytz.timezone('Asia/Kolkata')
    return utc_dt.replace(tzinfo=pytz.utc).astimezone(ist_tz)

# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed_password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')
        new_user = User(
            name=request.form['Name'],
            username=request.form['username'],
            phone_number=request.form['number'],
            password=hashed_password
        )
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash("Registered successfully! Please log in.")
            return redirect(url_for('login'))
        except Exception as e:
            flash("Registration failed: " + str(e))
            return redirect(url_for('register'))

    return render_template('register.html')



@app.route('/', methods=['GET', 'POST'])
def login():
    error_message = None

    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and bcrypt.check_password_hash(user.password, request.form['password']):
            session['username'] = user.username
            flash('Login successful', 'success')
            return redirect(url_for('index'))
        else:
            error_message = 'Invalid username or password'
            flash(error_message, 'error')
            return redirect(url_for('login'))  # Redirect to login again

    # Retrieve and clear flashed messages
    flashed_messages = get_flashed_messages(with_categories=True, category_filter=['error'])

    return render_template('login.html', error_message=error_message, flashed_messages=flashed_messages)

@app.route('/index')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('indexpark.html')


# Logout route
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# Flask route for a floor
@app.route('/floor1')
def floor1():
    return render_template('floors1.html')

# Route for Floor 2
@app.route('/floor2')
def floor2():
    return render_template('floors2.html')

# Route for Floor 3
@app.route('/floor3')
def floor3():
    return render_template('floors3.html')

@app.route('/slot')
def slot():
    return render_template('slot.html')

def get_user_data(username):
    return User.query.filter_by(username=username).first()


@app.route('/account')
def account():
    if 'username' in session:
        user_data = get_user_data(session['username'])
        if user_data:
            return render_template('account.html', 
                                   name=user_data.name, 
                                   username=user_data.username, 
                                   number=user_data.phone_number,
                                   vehicle_number=user_data.vehicle_number)  # Add vehicle number here
        else:
            flash("User not found")
            return redirect(url_for('index'))
    else:
        return redirect(url_for('login'))

    

@app.route('/book_slot', methods=['POST'])
def book_slot():
    if 'username' not in session:
        return jsonify(success=False, message="User not logged in"), 401

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return jsonify(success=False, message="User not found"), 404

    # Check if the user already has a booked slot
    existing_slot = Slot.query.filter_by(user_id=user.id, booked=True).first()
    if existing_slot:
        return jsonify(success=False, message="You already have a booked slot. Please cancel your current booking before making a new one."), 403

    data = request.json
    user_location = (data['latitude'], data['longitude'])
    parking_lot_coords = (13.086537898232212, 80.18155397817559) #13.062719485237842, 80.16143267092903
    distance = geodesic(user_location, parking_lot_coords).kilometers

    if distance > 2:
        return jsonify(success=False, message="You must be within 2 km of the parking lot to book a slot."), 403

    slot_number = data['slotNumber']
    slot = Slot.query.filter_by(slot_number=slot_number).first()

    if not slot:
        slot = Slot(slot_number=slot_number, booked=True, user_id=user.id)
        db.session.add(slot)
    else:
        if slot.booked:
            return jsonify(success=False, message="This slot is already booked!")

    # Set booking time in IST
    slot.booking_time = utc_to_ist(datetime.utcnow())
    slot.booked = True
    slot.user_id = user.id

    db.session.commit()
    return jsonify(success=True, message="Slot booked successfully")



@app.route('/get_booked_slots')
def get_booked_slots():
    if 'username' not in session:
        return jsonify([]), 401

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return jsonify([]), 404

    booked_slots = Slot.query.filter_by(user_id=user.id, booked=True).all()
    slots_data = [{'slotNumber': slot.slot_number, 'bookedOn': slot.booking_time.strftime("%Y-%m-%d %H:%M:%S")}
                  for slot in booked_slots]
    return jsonify(slots_data)

@app.route('/get_slots')
def get_slots():
    slots = Slot.query.all()
    slots_data = [{'slot_number': slot.slot_number, 'booked': slot.booked} for slot in slots]
    return jsonify(slots_data)

# Route to display bookings for cancellation
@app.route('/cancel_bookings')
def cancel_bookings():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()
    if user:
        booked_slots = Slot.query.filter_by(user_id=user.id, booked=True).all()
        for slot in booked_slots:
            slot.booking_time = slot.booking_time  # Convert to IST

        return render_template('cancel_bookings.html', user=user, booked_slots=booked_slots)
    else:
        flash("User not found")
        return redirect(url_for('index'))


# Route to process a booking cancellation
@app.route('/cancel_booking', methods=['POST'])
def cancel_booking():
    if 'username' not in session:
        return jsonify(success=False, message="User not logged in"), 401

    user = User.query.filter_by(username=session['username']).first()
    if not user:
        return jsonify(success=False, message="User not found"), 404

    data = request.json
    slot_number = data.get('slotNumber')
    user_location = (data['latitude'], data['longitude'])
    parking_lot_coords = (13.086543715686373, 80.18155397817559)  #VIT 12.840577602701114, 80.15337294377673

    distance = geodesic(user_location, parking_lot_coords).kilometers
    if distance <= 2:
        return jsonify(success=False, message="Cannot cancel booking while within 2 km of the parking lot."), 403

    slot = Slot.query.filter_by(slot_number=slot_number).first()
    if not slot or slot.user_id != user.id:
        return jsonify(success=False, message="Slot not found or not booked by you."), 404

    slot_booking_time = slot.booking_time

    slot_history = SlotHistory(
        slot_number=slot.slot_number,
        user_id=slot.user_id,
        booking_time=slot_booking_time,
        end_time=utc_to_ist(datetime.utcnow())
    )
    db.session.add(slot_history)

    db.session.delete(slot)
    db.session.commit()

    # Calculating the amount due
    duration = slot_history.end_time - slot_history.booking_time
    total_hours = duration.total_seconds() / 3600
    amount_due = 20 if total_hours <= 0.5 else 30 * round(total_hours)

    return jsonify(success=True, message="Booking canceled successfully", amount_due=amount_due, slot_number=slot.slot_number)


@app.route('/booking_history')
def booking_history():
    if 'username' not in session:
        return redirect(url_for('login'))

    user = User.query.filter_by(username=session['username']).first()
    if user:
        history_slots = SlotHistory.query.filter_by(user_id=user.id).all()
        for slot in history_slots:
            slot.booking_time = slot.booking_time  # Convert booking time to IST
            slot.end_time = slot.end_time  # Convert end time to IST

        return render_template('booking_history.html', user=user, history_slots=history_slots)
    else:
        flash("User not found")
        return redirect(url_for('index'))

    
@app.route('/calculate_amount')
def calculate_amount():
    user = User.query.filter_by(username=session.get('username')).first()
    if not user:
        return redirect(url_for('login'))

    # Fetch the latest slot history record for the user
    slot_history = SlotHistory.query.filter_by(user_id=user.id).order_by(SlotHistory.end_time.desc()).first()

    if slot_history:
        # Calculate the duration and the amount due
        duration = slot_history.end_time - slot_history.booking_time
        total_hours = duration.total_seconds() / 3600
        if total_hours <= 0.5:  # Grace period
            amount_due = 20
        else:
            amount_due = 30 * round(total_hours)

        # Fetch the slot number
        slot_number = slot_history.slot_number
    else:
        amount_due = 0
        slot_number = None  # or a default value or message

    return render_template('amount.html', slot_number=slot_number, amount_due=amount_due)



@app.route('/amount')
def amount():
    slot_number = request.args.get('slot_number')
    amount_due = request.args.get('amount_due')
    return render_template('amount.html', slot_number=slot_number, amount_due=amount_due)

@app.route('/check-vehicle', methods=['POST'])
def check_vehicle():
    data = request.get_json()
    vehicle_number = data['vehicleNumber']

    with open('vehicle.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row['VehicleNumber'] == vehicle_number:
                return jsonify({'message': 'Vehicle found: ' + row['Status']})

    return jsonify({'message': 'Vehicle not found'})

if __name__ == '__main__':
    app.run(debug=True)
