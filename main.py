from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, LoginManager, login_user, logout_user
import pandas as pd
import json
import plotly
import plotly.express as px
import pandas as pd
import sqlite3
from datetime import datetime, date

app = Flask(__name__)
# flask-sqlalchemy to connect to sqlite
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///db.sqlite"
#Declaring the secret key
app.config["SECRET_KEY"] = "mysecret"

db = SQLAlchemy()

sales_data = None


'''Column Names are
Date,Salesperson,Customer Name,Car Make,Car Model,Car Year,Sale Price,Commission Rate,Commission Earned'''

class Sales(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    salesperson = db.Column(db.String(250), nullable=False)
    customer_name = db.Column(db.String(250), nullable=False)
    car_make = db.Column(db.String(250), nullable=False)
    car_model = db.Column(db.String(250), nullable=False)
    car_year = db.Column(db.Integer(), nullable=False)
    sale_price = db.Column(db.String(250), nullable=False)
    commission_rate = db.Column(db.Float(), nullable=False)
    commission_earned = db.Column(db.Float(), nullable=False)

# Declaring user model
class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(10), nullable = False, unique = True)
    password = db.Column(db.String(250), nullable = False)


# Initializing app with extension
db.init_app(app)

# Create db with app context
with app.app_context():
    db.create_all()

# Load CSV data
csv_file_path = 'data/car-data-small.csv'
car_sales_data = pd.read_csv(csv_file_path)

# Drop sales table if it exists
with app.app_context():
    db.session.execute(db.text('DROP TABLE IF EXISTS sales'))
    db.session.commit()

with app.app_context():
    db.create_all()
    for index, row in car_sales_data.iterrows():
        new_car_sale = Sales(
            date=datetime.strptime(row['Date'], '%Y-%m-%d').date(),
            salesperson=row['Salesperson'],
            customer_name=row['Customer Name'],
            car_make=row['Car Make'],
            car_model=row['Car Model'],
            car_year=row['Car Year'],
            sale_price=row['Sale Price'],
            commission_rate=row['Commission Rate'],
            commission_earned=row['Commission Earned']
        )
        db.session.add(new_car_sale)
    db.session.commit()
    print("Car sales data loaded successfully.")

#Initializing loginManager
loginManager = LoginManager()
loginManager.init_app(app)

@loginManager.user_loader
def load_user(user_id):
    return Users.query.get(user_id)

@app.route('/')
def home():
    return render_template("home.html")

@app.route('/first_page')
def first_page():
    return render_template("first_page.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = Users.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('first_page'))
        else:
            return "Invalid credentials"

    return render_template("login.html")


@app.route('/register', methods=['GET', 'POST'])
def register():
    #If the user made a post request, create a new user
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = Users(username=username, password=password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))

    #If the user made a get request, return the register page    
    return render_template("register.html")


@app.route('/logout', methods=['GET'])
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/filter_by', methods=['POST'])
def filter_by():
    global sales_data
    filters = request.form.to_dict()
    page = 1
    records_per_page = 20

    # Filter the sales data by a value of the column in filters
    valid_columns = ['date', 'salesperson', 'customer_name', 'car_make', 'car_model', 'car_year', 'sale_price', 'commission_rate', 'commission_earned']

    filtered_data = sales_data.copy()
    for column, value in filters.items():
        if column in valid_columns:
            filtered_data = filtered_data[filtered_data[column] == value]

    total_records = len(filtered_data)  # Count the filtered records

    # Paginate the data
    start = (page - 1) * records_per_page
    end = start + records_per_page
    paginated_sales_data = filtered_data.iloc[start:end]

    return render_template('show_sales_data.html', sales=paginated_sales_data.to_dict(orient='records'), total_records=total_records, page=page, records_per_page=records_per_page, filters=filters)

@app.route('/show_sales_data/', defaults={'page': 1, 'records_per_page': 10})
@app.route('/show_sales_data/page/<int:page>/records_per_page/<int:records_per_page>')
def show_sales_data(page, records_per_page):
    global sales_data
    
    # Load all sales data into a pandas DataFrame
    con = sqlite3.connect("instance/db.sqlite")

    sales_data = pd.read_sql_query("SELECT * from sales", con)
    
    # Remove all duplicate records
    sales_data = sales_data.drop_duplicates()


    # Calculate total records
    total_records = len(sales_data)
    
    # Calculate total pages
    total_pages = (total_records + records_per_page - 1) // records_per_page 
    # Paginate the data
    start = (page - 1) * records_per_page
    end = start + records_per_page
    paginated_sales_data = sales_data.iloc[start:end]


    # Create a dictionary that contains all the unique values for each column in the Sales table
    filter_columns = ["salesperson", "car_make", "car_model", "car_year"]
    filters = {column: sales_data[column].unique().tolist() for column in filter_columns}

    return render_template('show_sales_data.html', sales=paginated_sales_data.to_dict(orient='records'), total_records=total_records, total_pages=total_pages, page=page, records_per_page=records_per_page, filters=filters)



@app.route('/sales_by_salesperson', methods=['GET'])
def sales_by_salesperson():
    print("Function triggered")
    # Query the sales data from the database
    sales_data = Sales.query.all()

    # Convert the sales data to a pandas DataFrame
    sales_df = pd.DataFrame([(s.salesperson, s.sale_price) for s in sales_data], columns=['Salesperson', 'Sale Price'])

    # Convert the sale price to numeric
    sales_df['Sale Price'] = pd.to_numeric(sales_df['Sale Price'], errors='coerce')

    # Group the data by Salesperson and sum the total price of cars sold
    sales_by_person = sales_df.groupby('Salesperson')['Sale Price'].sum()
    # Convert the grouped data to a DataFrame
    sales_by_person_df = sales_by_person.reset_index()
    sales_by_person_df.columns = ['Salesperson', 'Total Sale Price']

    # Create Bar chart
    fig = px.bar(sales_by_person_df, x='Salesperson', y='Total Sale Price')

    # Create graphJSON
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)     
    
    # Use render_template to pass graphJSON to html
    return render_template('first_page.html', graphJSON=graphJSON)


@app.route('/sales_by_car_make', methods=['GET'])
def sales_by_car_make():
    # Query the sales data from the database
    sales_data = Sales.query.all()

    # Convert the sales data to a pandas DataFrame
    sales_df = pd.DataFrame([(s.car_make, s.sale_price) for s in sales_data], columns=['Car Make', 'Sale Price'])

    # Convert the sale price to numeric
    sales_df['Sale Price'] = pd.to_numeric(sales_df['Sale Price'], errors='coerce')

    # Group the data by Car Make and sum the total price of cars sold
    sales_by_car_make = sales_df.groupby('Car Make')['Sale Price'].sum()
    # Convert the grouped data to a DataFrame
    sales_by_car_make_df = sales_by_car_make.reset_index()
    sales_by_car_make_df.columns = ['Car Make', 'Total Sale Price']

    # Create Bar chart
    fig = px.bar(sales_by_car_make_df, x='Car Make', y='Total Sale Price')
    
    # Create graphJSON
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    #
    #return jsonify(json.loads(graphJSON))

    #return graphJSON
    return render_template("first_page.html", graphJSON = graphJSON)

@app.route('/delete_sales_record/<int:id>', methods=['POST'])
def delete_sales_record(id):
    print("Deleting record with id: ", id)
    sale = Sales.query.get_or_404(id)
    db.session.delete(sale)
    db.session.commit()
    return redirect(url_for('show_sales_data'))


@app.route('/edit_sales_record/<int:id>', methods=['GET', 'POST'])
def edit_sales_record(id):
    sale = Sales.query.get_or_404(id)
    if request.method == 'POST':
        sale.date = request.form['date']
        sale.salesperson = request.form['salesperson']
        sale.customer_name = request.form['customer_name']
        sale.car_make = request.form['car_make']
        sale.car_model = request.form['car_model']
        sale.car_year = request.form['car_year']
        sale.sale_price = request.form['sale_price']
        sale.commission_rate = request.form['commission_rate']
        sale.commission_earned = request.form['commission_earned']
        db.session.commit()
        return redirect(url_for('show_sales_data'))
        
    return render_template('edit_sales_record.html', sale=sale)

@app.route('/add_sales_record', methods=['GET', 'POST'])
def add_sales_record():
    # Adding the sales data to the database
    if request.method == 'POST':
        new_sale = Sales(
            date=request.form['date'],
            salesperson=request.form['salesperson'],
            customer_name=request.form['customer_name'],
            car_make=request.form['car_make'],
            car_model=request.form['car_model'],
            car_year=request.form['car_year'],
            sale_price=request.form['sale_price'],
            commission_rate=request.form['commission_rate'],
            commission_earned=request.form['commission_earned']
        )
        db.session.add(new_sale)
        db.session.commit()
        return redirect(url_for('show_sales_data'))
    
    return render_template('add_sales_record.html')

if __name__ == "__main__":
    app.run(debug=True)