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

# Storing Filters in the storage dictionary
filter_storage = dict()

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
    sale_price = db.Column(db.Integer(), nullable=False)
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


# Load all sales data into a pandas DataFrame
con = sqlite3.connect("instance/db.sqlite")
sales_data = pd.read_sql_query("SELECT * from sales", con)

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

    return render_template("home.html")


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



@app.route('/filter_sales', methods=['GET','POST'])
def filter_sales():
    '''
    Function to filter sales view
    '''
    global sales_data, filter_storage
    filters = request.form.to_dict()
    column_name = request.form.get('column_name')
    column_value = request.form.get('column_value')
    filter_storage[column_name] = column_value
    page = 1
    records_per_page = 20
    filtered_data = sales_data.copy()
    filtered_data = filtered_data[filtered_data[column_name] == column_value]
    sales_data = filtered_data
    
    return redirect(url_for('show_sales_data'))

@app.route('/clear_all_filters', methods=['GET'])
def clear_all_filters():
    global sales_data

    # Reload all sales data from the database
    con = sqlite3.connect("instance/db.sqlite")
    sales_data = pd.read_sql_query("SELECT * from sales", con)
    con.close()

    return redirect(url_for('show_sales_data'))

SALES_DATA = None

@app.route('/unique_values', methods=['POST'])
def unique_values():
    global sales_data
    column_name = request.form.get('column_name')
    # Get the list of columns
    columns = sales_data.columns.tolist()
    if column_name in columns:
        unique_values = sales_data[column_name].unique().tolist()
        return jsonify({"items":unique_values})
    else:
        return {"error": "Invalid column name"}, 400

@app.route('/show_sales_data/', defaults={'page': 1, 'records_per_page': 10})
@app.route('/show_sales_data/page/<int:page>/records_per_page/<int:records_per_page>')
def show_sales_data(page, records_per_page):
    global sales_data

    
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
    global sales_data

    # Select only the Salesperson and Sale Price columns
    sales_df = sales_data[['salesperson', 'sale_price']].copy()

    # Rename the columns to Salesperson and Sale Price
    sales_df.columns = ['Salesperson', 'Sale Price']

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
    global sales_data

    # Select only the Car Make and Sale Price columns
    sales_df = sales_data[['car_make', 'sale_price']].copy()

    # Rename the columns to Car Make and Sale Price
    sales_df.columns = ['Car Make', 'Sale Price']


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

    return render_template("first_page.html", graphJSON=graphJSON)


@app.route('/compare_sales_2022_2023', methods=['GET'])
def compare_sales_2022_2023():
    global sales_data

    # Filter data for the years 2022 and 2023
    sales_data['date'] = pd.to_datetime(sales_data['date'])
    sales_data['year'] = sales_data['date'].dt.year
    sales_2022 = sales_data[sales_data['year'] == 2022]
    sales_2023 = sales_data[sales_data['year'] == 2023]

    # Group by car make and sum the sale prices for each year
    sales_2022_grouped = sales_2022.groupby('car_make')['sale_price'].sum().reset_index()
    sales_2023_grouped = sales_2023.groupby('car_make')['sale_price'].sum().reset_index()

    # Merge the two dataframes on car make
    comparison_df = pd.merge(sales_2022_grouped, sales_2023_grouped, on='car_make', how='outer', suffixes=('_2022', '_2023')).fillna(0)

    
    # Create a bar chart comparing sales in 2022 and 2023
    fig = px.bar(comparison_df, y='car_make', x=['sale_price_2022', 'sale_price_2023'], barmode='group', labels={'value': 'Total Sale Price', 'car_make': 'Car Make'})

    # Create graphJSON
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template("first_page.html", graphJSON=graphJSON)


@app.route('/delete_sales_record/<int:id>', methods=['POST'])
def delete_sales_record(id):
    print("Deleting record with id: ", id)
    sale = Sales.query.get_or_404(id)
    db.session.delete(sale)
    db.session.commit()
    reload_from_db()
    return redirect(url_for('show_sales_data'))

def reload_from_db():
    global sales_data, filter_storage
    # Reload all sales data from the database
    con = sqlite3.connect("instance/db.sqlite")
    sales_data = pd.read_sql_query("SELECT * from sales", con)
    # Checking if there are any current filteres to keep up filter storage
    if filter_storage:
        for column_name, column_value in filter_storage.items():
            sales_data = sales_data[sales_data[column_name] == column_value]
    con.close()


@app.route('/edit_sales_record/<int:id>', methods=['GET', 'POST'])
def edit_sales_record(id):
    sale = Sales.query.get_or_404(id)
    if request.method == 'POST':
        sale.date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        sale.salesperson = request.form['salesperson']
        sale.customer_name = request.form['customer_name']
        sale.car_make = request.form['car_make']
        sale.car_model = request.form['car_model']
        sale.car_year = request.form['car_year']
        sale.sale_price = request.form['sale_price']
        sale.commission_rate = request.form['commission_rate']
        sale.commission_earned = request.form['commission_earned']
        db.session.commit()
        reload_from_db()
        return redirect(url_for('show_sales_data'))
        
    return render_template('edit_sales_record.html', sale=sale)

@app.route('/add_sales_record', methods=['GET', 'POST'])
def add_sales_record():
    # Adding the sales data to the database
    if request.method == 'POST':
        new_sale = Sales(
            date = datetime.strptime(request.form['date'], '%Y-%m-%d').date(),
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
        reload_from_db()
        return redirect(url_for('show_sales_data'))
    
    return render_template('add_sales_record.html')

if __name__ == "__main__":
    app.run(debug=True)