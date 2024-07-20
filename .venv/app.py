from flask import Flask,render_template,redirect, session, flash, url_for, request,jsonify, send_file, g
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, ValidationError
import bcrypt
from flask_mysqldb import MySQL
import pymysql
import pandas as pd
import xlsxwriter 
from werkzeug.utils import secure_filename
import os
from datetime import datetime







UPLOAD_FOLDER = os.path.join('static', 'uploads')  # Create a relative path

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'jfif'}

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# MySQL Configuration
conn = pymysql.connect( 
        host='localhost', 
        user='root',  
        password = "", 
        db='flasker_db', 
        )

conn.autocommit(True)

cursor = conn.cursor()

app.secret_key = 'my super secret key'

class RegisterForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Register")

    def validate_email(self, field):
        
        cursor.execute("SELECT * FROM users WHERE email = %s", (field.data,))
        user = cursor.fetchone()
        if user:
            raise ValidationError('Email Already Taken')
    
    
class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Register")    

# Ensure the upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



@app.route('/')
def index():
    return render_template('index.html')       

@app.route('/blog/')
def blog():
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM posts")
    allPosts  = cursor.fetchall()
    blogposts = []
    if allPosts:
        for post in allPosts:
            blogposts.append({
                'id': post[0],
                'title': post[1],
                'author': post[2],
                'content': post[3],
                'feature_img': post[4],
                'categories': post[5],
                'date_created': post[6],
                })
        print(blogposts)
        return render_template('blog.html', blogPosts = blogposts)
    else:
        return render_template('blog.html')
        
        
@app.route('/blog/<int:id>', methods= ['GET'])
def singleblog(id):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM posts WHERE id = %s", (id,))
    post = cursor.fetchone()
    if post:
        return render_template('singleblog.html', post = post)
    else:
        return render_template('404.html')
    


@app.route('/register', methods=['GET','POST'])
def register():
    form = RegisterForm()
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        hashed_password = bcrypt.hashpw(password.encode('utf-8'),bcrypt.gensalt())

        # Store data into flasker_DB DB  
               
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (name, email, username, password) VALUES (%s, %s, %s, %s)",(name, email, username, hashed_password))
        conn.commit()
        flash("Congratulations, your account has been successfully created.", 'success')                
        return redirect('/login')

    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    user_id = session.get('user_id')
    if user_id:
        return redirect('/dashboard')

    else:
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            print(username, password)
       
            # Store data into flasker_DB DB         
            
            cursor.execute("SELECT * FROM users WHERE email = %s", (username,))
            user = cursor.fetchone()        
        
            if user and bcrypt.checkpw(password.encode('utf-8'),user[4].encode('utf-8')):
                session['user_id'] = user[0]
                session['user_name'] = user[1]
                flash("Login Successfully", 'success')
                redirect(url_for('login'))
                # return redirect('/dashboard')
            else:
                flash("Login failed. Please check your email and password",'danger')
                redirect(url_for('login'))

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    form = LoginForm()   
    if 'user_id' in session:
        user_id = session['user_id']
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        if user:      
             return render_template('dashboard.html', user=user)
        
    return render_template('login.html',form=form)

@app.route('/create')
def create():
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM category")
    categories  = cursor.fetchall()      
    return render_template('create.html', categories = categories)


@app.route('/add_post', methods=['GET','POST'])
def add_post():
    if request.method == 'POST':

        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(url_for('create'))
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file','danger')
            return redirect(url_for('create'))
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            print(f"Attempting to save file at: {file_path}")
            file.save(file_path)
            print(f"File {filename} saved successfully.")

            title = request.form['post_title']
            author = request.form['post_author']
            content = request.form.get('post_description') 
            feature_img = filename        
            categories = ','.join(request.form.getlist('multiselect'))  # Join list into a comma-separated string
            date_created = datetime.utcnow()  # Call the function to get the current datetime

            # Store data into flasker_DB DB                 
            cursor = conn.cursor()
            cursor.execute("INSERT INTO posts (post_title, post_author, post_description, feature_image, post_categories, created_at) VALUES (%s, %s, %s, %s, %s, %s)",(title, author, content, feature_img, categories, date_created))
            conn.commit()

            flash('Post created successfully!', 'success')
            return redirect(url_for('create'))
        
        else:
            flash('File type not allowed', 'danger')
            return redirect(url_for('create'))    
    

@app.route('/view_posts')
def view_posts(): 
    cursor = conn.cursor()
    cursor.execute("SELECT id, post_title, post_author, post_description, feature_image, post_categories, created_at FROM posts")
    posts = cursor.fetchall()
    print(posts)
    posts_data = []
    if posts:        
        for post in posts:
            post_id, title, author, content, feature_img, categories, created_at = post            
            # Fetch category names based on category IDs
            category_ids = categories.split(',')
            category_names = []
            for category_id in category_ids:
                cursor.execute("SELECT name FROM category WHERE id = %s", (category_id,))
                category_name = cursor.fetchone()
                if category_name:
                    category_names.append(category_name[0])
            
            category_names_str = ', '.join(category_names)
            # Append post data along with category names to the list
            posts_data.append({
                'id': post_id,
                'title': title,
                'author': author,
                'content': content,
                'feature_img': feature_img,
                'categories': category_names_str,
                'date_created': created_at,
                'category_list':category_ids
            })

        cursor.execute("SELECT * FROM category")
        categories  = cursor.fetchall() 
        print(posts_data)
        return render_template('view_posts.html', posts=posts_data, categories=categories)
    
    else:
        flash('No posts found', 'info')
        return render_template('view_posts.html')


@app.route('/update_post', methods=['GET','POST'])
def update_post():

    if request.method == 'POST':

        id = request.form['postId']
        title = request.form['post_title']
        author = request.form['post_author']
        content = request.form.get('post_description')                  
        categories = ','.join(request.form.getlist('multiselect'))  # Join list into a comma-separated string
        date_created = datetime.utcnow()  # Call the function to get the current datetime

        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(url_for('view_posts'))
        file = request.files['file']
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':          

            # Store data into flasker_DB DB                 
            cursor = conn.cursor()
            cursor.execute("UPDATE posts SET post_title=%s, post_author=%s, post_description=%s, post_categories=%s, created_at=%s WHERE id=%s", (title, author, content, categories, date_created, id))
            conn.commit()
            flash('Post Updated!', 'success')
            return redirect(url_for('view_posts'))        


        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            print(f"Attempting to save file at: {file_path}")
            file.save(file_path)
            print(f"File {filename} saved successfully.")            
            feature_img = filename        
            categories = ','.join(request.form.getlist('multiselect'))  # Join list into a comma-separated string
            date_created = datetime.utcnow()  # Call the function to get the current datetime
            # Store data into flasker_DB DB                 
            cursor = conn.cursor()
            cursor.execute("UPDATE posts SET post_title=%s, post_author=%s, post_description=%s, feature_image=%s, post_categories=%s, created_at=%s WHERE id=%s", (title, author, content, feature_img, categories, date_created, id))
            conn.commit()

            flash('Post Updated!', 'success')
            return redirect(url_for('view_posts'))
        
        else:
            flash('File type not allowed', 'danger')
            return redirect(url_for('view_posts'))        


@app.route('/delete_post', methods=['POST'])

def delete_post():
    id = request.form['id']
    cursor = conn.cursor()   
    cursor.execute("DELETE FROM posts WHERE id={}".format(id))   
    flash('Post Deleted!', 'success')

    return jsonify({
    'status': 'success',
    'message': "Post Deleted!"
    })
   



@app.route('/getblog_post', methods=['GET', 'POST'])
def getblog_post():

    id = request.form['id']
    print("=====================")
    print(id)
    print("=====================")
    cursor = conn.cursor()    
    cursor.execute("SELECT * FROM posts WHERE id = %s", (id,))
    post_data  = cursor.fetchone()  

    # Fetch category names based on category IDs
    category_ids = post_data[5].split(',')
 
    # Append post data along with category names to the list

    blog_post = {
        'id': post_data[0],
        'title': post_data[1],
        'author': post_data[2],
        'content': post_data[3],
        'feature_img': post_data[4],
        'categories': category_ids,
        'date_created': post_data[6]
        }
  
    print(blog_post)
    return jsonify({
        'status': 'success',
        'data': blog_post
    })


    

@app.route('/create_category')
def create_category():
    cursor.execute("SELECT * FROM category")
    categories  = cursor.fetchall()  
    return render_template('create_category.html',categories = categories)

@app.route('/add_category', methods = ['GET', 'POST'])
def add_category():
    if request.method == 'POST':
        category = request.form['category']
        # Store data into flasker_DB DB                 
        cursor = conn.cursor()
        cursor.execute("INSERT INTO category (name) VALUES (%s)",(category))
        conn.commit()    
        cursor.execute("SELECT * FROM category")
        categories  = cursor.fetchall()  
        print(categories)     
        flash("Category has been successfully created.", 'success')                
        return redirect('/create_category')

    # return render_template('create_category.html')
    pass
   
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("You have been logged out successfully.", 'success')       
    return redirect(url_for('login'))


@app.route('/get_users', methods=['GET','POST'])
def get_users():
    if request.method == 'POST':
        draw = request.form['draw']
        row = int(request.form['start'])
        rowperpage = int(request.form['length'])
        searchValue = request.form["search[value]"]
        
        print(searchValue)

        conn.ping()
        cursor.execute("SELECT COUNT(*) FROM users")
        result = cursor.fetchone()
        totalrecord = result[0]

        
        print(totalrecord)

        # Total number of record with filtering
        likeString = "%" + searchValue + "%"
        cursor.execute("SELECT count(*) as allcount FROM users WHERE name LIKE %s OR email LIKE %s", (likeString, likeString))        
        se_result = cursor.fetchone()
        recordsFiltered = se_result[0]

        # Fetch record
        if searchValue =='':
            cursor.execute("SELECT id, name, email FROM users limit %s, %s",(row, rowperpage))
            users = cursor.fetchall()  
        else:
            cursor.execute("SELECT * FROM users WHERE name LIKE %s OR email LIKE %s", (likeString, likeString))    
            users = cursor.fetchall() 

        data = []
        for user in users:
            data.append({
                'id': user[0],
                'name': user[1],
                'email': user[2]
            })

        response = {
            'draw': draw,
            'recordsTotal': rowperpage,
            'recordsFiltered': recordsFiltered,
            'data': data
            }               
        return jsonify(response)     
    
    return jsonify("Request failed")



@app.route('/users')
def users():
    return render_template('usersajax.html')   


@app.route('/search_results', methods=['GET', 'POST'])
def search_results():
    if request.method == "POST":
        value = request.form['val']
        print(value)
        conn.ping()
        if value!= None:
            cursor.execute("SELECT id, name, email FROM users WHERE name LIKE %s", ("%" + value + "%",))
        else:
            cursor.execute("SELECT id, name, email FROM users")

        results  = cursor.fetchall()    
        print(results)
        return jsonify(results)
    

@app.route('/export_users')
def export_users():
    print("yes coming")
    file_path = "D:/export-users.xlsx"
    cursor.execute("SELECT id, name, email FROM users")
    results  = cursor.fetchall()    
    workbook = xlsxwriter.Workbook(file_path) 
    worksheet = workbook.add_worksheet("users")     

    worksheet.write(0, 0, '#')
    worksheet.write(0, 1, 'Name')
    worksheet.write(0, 2, 'Email')

    row = 1
    column = 0
    for entry in results:     
        worksheet.write(row, column, entry[0]) 
        worksheet.write(row, column+1, entry[1]) 
        worksheet.write(row, column+2, entry[2]) 
        row+=1

    workbook.close() 
    return send_file(file_path)

    # return jsonify('exported')  

@app.route('/import_csv')
def import_csv():
    file_path = "C:/Users/Admin/Desktop/exportpost.csv"
    data  = pd.read_csv(file_path)
    df = pd.DataFrame(data)
    # Insert DataFrame to Table
    for row in df.itertuples():
            
            # Fetch category names based on category IDs
            category_names = row.categories.split(',')
            date_created = row.date_created
            timestamp = datetime.strptime(date_created, '%d-%m-%Y %H:%M').timestamp()      
            print(timestamp)      
            
          
            category_ids = []
            for category_name in category_names:
                category_name = category_name.strip()
                cursor = conn.cursor()
                query = "SELECT id FROM category WHERE name = %s"
                cursor.execute(query, (category_name,))  # Note the comma after category_name
                category_id = cursor.fetchone()
                if category_id:
                    category_ids.append(category_id[0])
                    
            cat_idx = ', '.join(map(str, category_ids))  # Convert IDs to strings before joining
            
            cursor = conn.cursor()
            cursor.execute("INSERT INTO posts (post_title, post_author, post_description, feature_image, post_categories, created_at) VALUES (%s, %s, %s, %s, %s, %s)",(row.title, row.author, row.content, row.feature_img, cat_idx, timestamp))
            conn.commit()
    
    return jsonify('imported')



@app.route('/export_post')
def export_post():
    
    file_path = "C:/Users/Admin/Desktop/exportpost.csv"
    cursor.execute("SELECT * FROM posts")
    results  = cursor.fetchall()  
    exportData = []
    # title = []
    # author = []
    # content = []
    # image = []
    # category = []
    # publish_date = []
    if results:
        for row in results:                    
            # Fetch category names based on category IDs
            category_ids = row[5].split(',')
            category_names = []
            for category_id in category_ids:
                cursor.execute("SELECT name FROM category WHERE id = %s", (category_id,)) 
                category_name = cursor.fetchone()
                if category_name:
                    category_names.append(category_name[0])

            category_names_str = ', '.join(category_names)

            # title.append(row[1])
            # author.append(row[2])
            # content.append(row[3])
            # image.append("http://127.0.0.1:5000/static/uploads/"+row[4])
            # category.append(category_names_str)
            # publish_date.append(row[6])     

            exportData.append({
                'title': row[1],
                'author': row[2],
                'content': row[3],
                'feature_img': "http://127.0.0.1:5000/static/uploads/"+row[4],
                'categories': category_names_str,
                'date_created': row[6]

            })  
    else:
        return jsonify('No post found')
    



        

    # workbook = xlsxwriter.Workbook(file_path) 
    # worksheet = workbook.add_worksheet("users")     

    # worksheet.write(0, 0, '#')
    # worksheet.write(0, 1, 'Name')
    # worksheet.write(0, 2, 'Email')

    # row = 1
    # column = 0
    # for entry in results:     
    #     worksheet.write(row, column, entry[0]) 
    #     worksheet.write(row, column+1, entry[1]) 
    #     worksheet.write(row, column+2, entry[2]) 
    #     row+=1

    # workbook.close() 
    # return send_file(file_path)
    # df = pd.DataFrame(dicts)

    # saving the dataframe
    
    # df.to_csv(file_path, index=False)
    # return send_file(file_path)
  
    df = pd.DataFrame.from_dict(exportData) 
  

    # df = pd.DataFrame(exportData, columns = ['Title', 'Author','Content', 'Image', 'Categories', 'Publish Date']) 
    df.to_csv(file_path, index=False)
    return send_file(file_path)

    # return jsonify(exportData) 




if __name__ ==  '__main__':
    app.run(debug=True)