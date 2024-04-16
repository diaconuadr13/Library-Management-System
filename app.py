from flask import Flask, render_template, request, redirect, url_for, flash
from flask_mysqldb import MySQL, cursors
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from datetime import datetime, timedelta
import mysql.connector
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, Regexp, NumberRange, Optional
from wtforms.validators import ValidationError
from flask_talisman import Talisman


def validate_username(self, username):
    cursor = mysql.connection.cursor(cursorclass=cursors.DictCursor)
    cursor.execute("SELECT * FROM Users WHERE Username = %s", [username.data])
    existing_user = cursor.fetchone()
    cursor.close()
    if existing_user:
        raise ValidationError('Username already exists. Please choose a different one.')

class BookForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    year = IntegerField('YearOfPublication', validators=[DataRequired(), NumberRange(min=0, max=9999)])
    publisher = StringField('Publisher', validators=[DataRequired()])
    quantity = IntegerField('Quantity', validators=[Optional(), NumberRange(min=-1)])
    submit = SubmitField('Sign Up')

class ProfileForm(FlaskForm):
    username = StringField('Username', validators=[Length(min=2, max=20), validate_username, Optional()])
    email = StringField('Email', validators=[Email(), Optional()])
    telephone = StringField('Telephone', validators=[Regexp(r'[0-9-()+\s]+', message="Invalid telephone number")])
    address = StringField('Address')
    firstname = StringField('First Name')
    lastname = StringField('Last Name')
    submit = SubmitField('Update')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20), validate_username])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8),
                                                     EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Repeat Password')
    firstName = StringField('First Name', validators=[DataRequired()])
    lastName = StringField('Last Name', validators=[DataRequired()])
    telephone = StringField('Telephone',
                            validators=[DataRequired(), Regexp(r'[0-9-()+\s]+', message="Invalid telephone number")])
    address = StringField('Address', validators=[DataRequired()])
    role = SelectField('Role', choices=[('Admin', 'Admin'), ('Regular', 'Regular')])
    submit = SubmitField('Register')


class User(UserMixin):
    def __init__(self, user_id, username, email, role, firstName, lastName, telephone, address):
        self.id = user_id
        self.username = username
        self.email = email
        self.role = role
        self.firstName = firstName
        self.lastName = lastName
        self.telephone = telephone
        self.address = address


csp = {
    'default-src': [
        '\'self\'',
        'stackpath.bootstrapcdn.com',
    ],
    'script-src': [
        '\'self\'',
        '\'unsafe-inline\'',
        'stackpath.bootstrapcdn.com',
        'https://code.jquery.com/jquery-3.3.1.slim.min.js',
        'https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.7/umd/popper.min.js',
        'https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/js/bootstrap.min.js'
    ]
}

app = Flask(__name__)
Talisman(app, content_security_policy=csp, force_https=False)
login_manager = LoginManager(app)
login_manager.init_app(app)

app.secret_key = 'test'

# Configure MySQL connection
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Dynamita1978'
app.config['MYSQL_DB'] = 'adi'

mysql = MySQL(app)


@app.route('/books')
@login_required
def books():
    form = BookForm()
    cursor = mysql.connection.cursor(cursorclass=cursors.DictCursor)
    cursor.execute("SELECT * FROM Books")
    books = cursor.fetchall()
    cursor.close()
    return render_template('books.html', books=books, form=form)


@app.route('/authors')
@login_required
def authors():
    cursor = mysql.connection.cursor(cursorclass=cursors.DictCursor)
    cursor.execute("SELECT * FROM Authors")
    authors = cursor.fetchall()
    cursor.close()
    return render_template('authors.html', authors=authors)


@app.route('/libraries')
@login_required
def libraries():
    cursor = mysql.connection.cursor(cursorclass=cursors.DictCursor)
    cursor.execute("SELECT * FROM Libraries")
    libraries = cursor.fetchall()
    cursor.close()
    return render_template('libraries.html', libraries=libraries)


@app.route('/books_author')
@login_required
def books_author():
    cursor = mysql.connection.cursor(cursorclass=cursors.DictCursor)

    # Fetch books data
    cursor.execute("SELECT * FROM Books")
    books = cursor.fetchall()

    # Fetch authors data
    cursor.execute("SELECT * FROM Authors")
    authors = cursor.fetchall()

    # Fetch books_author data
    cursor.execute(
        """SELECT Books.BookID, Authors.AuthorID, Books.Title, Authors.FirstName, Authors.LastName, Books.Publisher, Books.YearOfPublication
        FROM Books
        INNER JOIN BookAuthors ON Books.BookID = BookAuthors.BookID
        INNER JOIN Authors ON BookAuthors.AuthorID = Authors.AuthorID;""")
    books_author = cursor.fetchall()

    cursor.close()

    # Pass books, authors, and books_author data to the template
    return render_template('books_author.html', books_author=books_author, books=books, authors=authors)


@app.route('/reserve_book/<int:book_id>/<int:library_id>', methods=['POST'])
@login_required
def reserve_book(book_id, library_id):
    cursor = mysql.connection.cursor(cursorclass=cursors.DictCursor)
    reservation_date = datetime.now().date()
    due_date = reservation_date + timedelta(days=14)

    args = [book_id, current_user.id, 3, reservation_date, due_date, 0]

    # Call the stored procedure
    cursor.callproc('ReserveBook', args)
    cursor.execute('SELECT @_ReserveBook_5')
    result_args = cursor.fetchone()
    # print(result_args.values())
    cursor.close()
    string = result_args['@_ReserveBook_5']
    flash(string)
    return redirect(url_for('books_author'))


@app.route('/reservations')
@login_required
def reservations():
    cursor = mysql.connection.cursor(cursorclass=cursors.DictCursor)
    query = """SELECT Books.Title, Books.Publisher, Libraries.Name, BookReservations.ReservationID, BookReservations.ReservationDate, BookReservations.DueDate
               FROM BookReservations
               INNER JOIN Books ON BookReservations.BookID = Books.BookID
               INNER JOIN Libraries ON BookReservations.LibraryID = Libraries.LibraryID
               WHERE BookReservations.UserID = %s"""
    cursor.execute(query, [current_user.id])
    reservations = cursor.fetchall()
    cursor.close()
    return render_template('reservations.html', reservations=reservations)


@app.route('/delete_reservation/<int:reservation_id>', methods=['POST'])
@login_required
def delete_reservation(reservation_id):
    cursor = mysql.connection.cursor(cursorclass=cursors.DictCursor)
    query = "DELETE FROM BookReservations WHERE ReservationID = %s AND UserID = %s"
    cursor.execute(query, (reservation_id, current_user.id))
    mysql.connection.commit()
    cursor.close()
    flash('Reservation cancelled successfully!')
    return redirect(url_for('reservations'))


@app.route('/add_author', methods=['POST'])
@login_required
def add_author():
    # Retrieve form data
    first_name = request.form['firstName']
    last_name = request.form['lastName']
    country = request.form['country']
    # Create a new author record
    cursor = mysql.connection.cursor(cursorclass=cursors.DictCursor)
    query = "INSERT INTO Authors (FirstName, LastName, CountryOfOrigin) VALUES (%s, %s, %s)"
    cursor.execute(query, (first_name, last_name, country))

    mysql.connection.commit()
    cursor.close()

    flash('New author added successfully!')

    return redirect(url_for('authors'))


@app.route('/delete_author/<int:id>', methods=['POST'])
@login_required
def delete_author(id):
    if not current_user.role == 'Admin':
        flash('Only admin users can delete data.', 'danger')
        return redirect(url_for('authors'))

    cursor = mysql.connection.cursor(cursorclass=cursors.DictCursor)
    query = "DELETE FROM Authors WHERE AuthorID = %s"
    cursor.execute(query, [id])

    mysql.connection.commit()
    cursor.close()

    flash('Author deleted successfully!')

    return redirect(url_for('authors'))


@app.route('/update_author/<int:id>', methods=['POST'])
@login_required
def update_author(id):
    first_name = request.form['firstName']
    last_name = request.form['lastName']
    country = request.form['country']

    cursor = mysql.connection.cursor(cursorclass=cursors.DictCursor)
    query = "UPDATE Authors SET FirstName = %s, LastName = %s, CountryOfOrigin = %s WHERE AuthorID = %s"
    cursor.execute(query, (first_name, last_name, country, id))

    mysql.connection.commit()
    cursor.close()

    flash('Author updated successfully!')

    return redirect(url_for('authors'))


@app.route('/add_library', methods=['POST'])
@login_required
def add_library():
    name = request.form['name']
    address = request.form['address']
    cursor = mysql.connection.cursor(cursorclass=cursors.DictCursor)
    query = "INSERT INTO Libraries (Name, Address) VALUES (%s, %s)"
    cursor.execute(query, (name, address))
    mysql.connection.commit()
    cursor.close()
    flash('New library added successfully!')
    return redirect(url_for('libraries'))


@app.route('/delete_library/<int:id>', methods=['POST'])
@login_required
def delete_library(id):
    if not current_user.role == 'Admin':
        flash('Only admin users can delete data.')
        return redirect(url_for('libraries'))

    cursor = mysql.connection.cursor(cursorclass=cursors.DictCursor)
    query = "DELETE FROM Libraries WHERE LibraryID = %s"
    cursor.execute(query, [id])
    mysql.connection.commit()
    cursor.close()
    flash('Library deleted successfully!')
    return redirect(url_for('libraries'))


@app.route('/update_library/<int:id>', methods=['POST'])
@login_required
def update_library(id):
    name = request.form['name']
    address = request.form['address']
    cursor = mysql.connection.cursor(cursorclass=cursors.DictCursor)
    query = "UPDATE Libraries SET Name = %s, Address = %s WHERE LibraryID = %s"
    cursor.execute(query, (name, address, id))
    mysql.connection.commit()
    cursor.close()
    flash('Library updated successfully!')
    return redirect(url_for('libraries'))

#TODO: CHECK FOR INVALID DATA
@app.route('/add_book', methods=['GET', 'POST'])
@login_required
def add_book():
    form = BookForm()
    cursor = mysql.connection.cursor(cursorclass=cursors.DictCursor)
    cursor.execute("SELECT * FROM Books")
    books = cursor.fetchall()
    cursor.close()
    if form.validate_on_submit():
        title = form.title.data
        year = form.year.data
        publisher = form.publisher.data
        quantity = form.quantity.data
        cursor = mysql.connection.cursor(cursorclass=cursors.DictCursor)
        query = "INSERT INTO Books (Title, YearOfPublication, Publisher, Quantity) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (title, year, publisher, quantity))
        mysql.connection.commit()
        cursor.close()
        flash('New book added successfully!')
        return redirect(url_for('books'))
    return render_template('books.html', form=form, books=books)


@app.route('/delete_book/<int:id>', methods=['POST'])
@login_required
def delete_book(id):
    if not current_user.role == 'Admin':
        flash('Only admin users can delete data.')
        return redirect(url_for('books'))

    cursor = mysql.connection.cursor(cursorclass=cursors.DictCursor)
    query = "DELETE FROM Books WHERE BookID = %s"
    cursor.execute(query, [id])
    mysql.connection.commit()
    cursor.close()
    flash('Book deleted successfully!')
    return redirect(url_for('books'))

#TODO: CHECK FOR INVALID DATA
@app.route('/update_book/<int:id>', methods=['GET', 'POST'])
@login_required
def update_book(id):
    form = BookForm()
    cursor = mysql.connection.cursor(cursorclass=cursors.DictCursor)
    cursor.execute("SELECT * FROM Books")
    books = cursor.fetchall()
    cursor.close()
    if request.method == 'GET':
        cursor = mysql.connection.cursor(cursorclass=cursors.DictCursor)
        cursor.execute("SELECT * FROM Books WHERE BookID = %s", [id])
        book = cursor.fetchone()
        form.title.data = book['Title']
        form.year.data = book['YearOfPublication']
        form.publisher.data = book['Publisher']
        form.quantity.data = book['Quantity']
        cursor.close()
    elif form.validate_on_submit():
        title = form.title.data
        year = form.year.data
        publisher = form.publisher.data
        quantity = form.quantity.data
        cursor = mysql.connection.cursor(cursorclass=cursors.DictCursor)
        query = "UPDATE Books SET Title = %s, YearOfPublication = %s, Publisher = %s, Quantity=%s WHERE BookID = %s"
        cursor.execute(query, (title, year, publisher, quantity, id))
        mysql.connection.commit()
        cursor.close()
        flash('Book updated successfully!')
        return redirect(url_for('books'))
    return render_template('books.html', form=form, books=books)


@app.route('/add_book_author', methods=['POST'])
@login_required
def add_book_author():
    book_id = request.form['book']
    author_id = request.form['author']
    cursor = mysql.connection.cursor(cursorclass=cursors.DictCursor)
    query = "INSERT INTO BookAuthors (BookID, AuthorID) VALUES (%s, %s)"
    cursor.execute(query, (book_id, author_id))
    mysql.connection.commit()
    cursor.close()
    flash('New book-author relationship added successfully!')
    return redirect(url_for('books_author'))


@app.route('/update_book_author/<int:old_book_id>/<int:old_author_id>', methods=['POST'])
@login_required
def update_book_author(old_book_id, old_author_id):
    new_book_id = request.form['book']
    new_author_id = request.form['author']
    cursor = mysql.connection.cursor(cursorclass=cursors.DictCursor)
    query = "UPDATE BookAuthors SET BookID = %s, AuthorID = %s WHERE BookID = %s AND AuthorID = %s"
    cursor.execute(query, (new_book_id, new_author_id, old_book_id, old_author_id))
    mysql.connection.commit()
    cursor.close()
    flash('Book-Author relationship updated successfully!')
    return redirect(url_for('books_author'))


@app.route('/delete_book_author/<int:book_id>/<int:author_id>', methods=['POST'])
@login_required
def delete_book_author(book_id, author_id):
    if not current_user.role == 'Admin':
        flash('Only admin users can delete data.')
        return redirect(url_for('books_author'))

    cursor = mysql.connection.cursor(cursorclass=cursors.DictCursor)
    query = "DELETE FROM BookAuthors WHERE BookID = %s AND AuthorID = %s"
    cursor.execute(query, (book_id, author_id))
    mysql.connection.commit()
    cursor.close()
    flash('Book-Author relationship deleted successfully!')
    return redirect(url_for('books_author'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = generate_password_hash(form.password.data)
        firstName = form.firstName.data
        lastName = form.lastName.data
        telephone = form.telephone.data
        address = form.address.data
        role = form.role.data

        cursor = mysql.connection.cursor(cursorclass=cursors.DictCursor)

        query = "INSERT INTO Users (Username, Password, FirstName, LastName, Telephone, Address, Email, Role) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        cursor.execute(query, (username, password, firstName, lastName, telephone, address, email, role))
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@login_manager.user_loader
def load_user(user_id):
    cursor = mysql.connection.cursor(cursorclass=cursors.DictCursor)
    cursor.execute("SELECT * FROM Users WHERE UserID = %s", [user_id])
    user_data = cursor.fetchone()
    cursor.close()
    if user_data:
        return User(user_data['UserID'], user_data['Username'], user_data['Email'], user_data['Role'], user_data['FirstName'],
                    user_data['LastName'], user_data['Telephone'], user_data['Address'])
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(cursorclass=cursors.DictCursor)
        cursor.execute("SELECT * FROM Users WHERE Username = %s", [username])
        user = cursor.fetchone()
        cursor.close()
        if user and check_password_hash(user['Password'], password):
            login_user(
                User(user['UserID'], user['Username'], user['Email'], user['Role'], user['FirstName'], user['LastName'],
                     user['Telephone'], user['Address']))
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')


@app.route('/profile')
@login_required
def profile():
    # Fetch user information from the database
    cursor = mysql.connection.cursor(cursorclass=cursors.DictCursor)
    cursor.execute("SELECT * FROM Users WHERE UserID = %s", [current_user.id])
    user = cursor.fetchone()
    cursor.close()
    # Create an instance of ProfileForm
    form = ProfileForm()
    # Pass the user information and form to the template
    return render_template('profile.html', user=user, form=form)

@app.route('/update_profile', methods=['POST'])
@login_required
def update_profile():
    form = ProfileForm(request.form)
    if form.validate_on_submit():
        cursor = mysql.connection.cursor(cursorclass=cursors.DictCursor)
        firstname = form.firstname.data
        lastname = form.lastname.data
        telephone = form.telephone.data
        address = form.address.data
        query = "UPDATE Users SET FirstName = %s, LastName = %s, Telephone = %s, Address = %s WHERE UserID = %s"
        cursor.execute(query, (firstname, lastname, telephone, address, current_user.id))
        mysql.connection.commit()
        cursor.close()
        flash('Profile updated successfully!')
        return redirect(url_for('profile'))
    else:
        # Fetch user information from the database
        cursor = mysql.connection.cursor(cursorclass=cursors.DictCursor)
        cursor.execute("SELECT * FROM Users WHERE UserID = %s", [current_user.id])
        user = cursor.fetchone()
        cursor.close()
        # Render the profile.html template with the form errors
        return render_template('profile.html', user=user, form=form)

@app.route('/delete_account', methods=['POST'])
@login_required
def delete_account():
    cursor = mysql.connection.cursor(cursorclass=cursors.DictCursor)
    query = "DELETE FROM Users WHERE UserID = %s"
    cursor.execute(query, [current_user.id])
    mysql.connection.commit()
    cursor.close()
    logout_user()
    flash('Your account has been deleted.')
    return redirect(url_for('login'))


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.')
    return redirect(url_for('login'))


@app.route('/home')
@login_required
def home():
    return render_template('home.html')


@app.route('/')
def landing():
    return render_template('landing.html')


if __name__ == '__main__':
    app.run(debug=True)
