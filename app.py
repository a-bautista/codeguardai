from flask import Flask, request, session, render_template, redirect, url_for, flash
from flask.views import MethodView
import openai
import os
from dotenv import load_dotenv, find_dotenv
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from flask_smorest import Api, Blueprint, abort
from marshmallow import Schema, fields as ma_fields
from functools import wraps
from extensions import db, migrate

# look for credentials OpenAI
openai.api_key = os.environ.get("OPENAI_API_KEY")

# Initialize extensions and configure the flask app
def create_app():
    app = Flask(__name__)
    
    # Configure database
    database_url = os.getenv('DATABASE_URL')
    if database_url and database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = os.environ.get("FLASK_SECRET_KEY")

    # configure OpenAPI
    app.config["API_TITLE"] = "codeguardai"
    app.config["API_VERSION"] = "1.0.0"
    app.config["OPENAPI_VERSION"] = "3.0.0"
    app.config["OPENAPI_URL_PREFIX"] = "/"
    app.config["OPENAPI_SWAGGER_UI_PATH"] = "/swagger"
    app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
    app.config["OPENAPI_SERVERS"] = [
        {"url": "https://virtserver.swaggerhub.com/A00973450_1/codeguardai/1.0.0", "description": "SwaggerHub API Auto Mocking"},
        {"url": "http://localhost:5001", "description": "Local Development Server"}
    ]
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    api = Api(app)
    
    return app, api
    
# Create the application instance and API
app, api = create_app()

# set up the secret key for the login and define the lifetime of the session
app.secret_key = os.environ.get("FLASK_SECRET_KEY")
app.permanent_session_lifetime = timedelta(days=1)


# Blueprint for CRUD operations
blp = Blueprint(
    'crud', 'crud',
    url_prefix='/crud',
    description='CRUD operations'
)

# Define Marshmallow schemas
class UserSchema(Schema):
    id = ma_fields.Int(dump_only=True)
    username = ma_fields.Str(required=True)
    email = ma_fields.Email(required=True)
    created_at = ma_fields.DateTime(dump_only=True)

class UserCreateSchema(UserSchema):
    password = ma_fields.Str(required=True, load_only=True)

class UserUpdateSchema(Schema):
    username = ma_fields.Str()
    email = ma_fields.Email()

class PromptSchema(Schema):
    id = ma_fields.Int(dump_only=True)
    user_id = ma_fields.Int(required=True)
    prompt = ma_fields.Str(required=True)
    response = ma_fields.Str(required=True)
    created_at = ma_fields.DateTime(dump_only=True)

# define database models
class User(db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    prompts = db.relationship('Prompts', backref='user', lazy=True)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

class Prompts(db.Model):
    __tablename__ = 'prompt'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) 
    prompt = db.Column(db.String(10000), unique=False, nullable=False)
    response = db.Column(db.String(12000), unique=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
  
# Route: Users
@blp.route('/users')
class UserList(MethodView):
    @blp.response(200, UserSchema(many=True))
    def get(self):
        """List all users"""
        users = User.query.all()
        return users

    @blp.arguments(UserCreateSchema)
    @blp.response(201, UserSchema)
    def post(self, user_data):
        """Create a new user"""
        new_user = User(
            username=user_data['username'],
            email=user_data['email']
        )
        new_user.password = user_data['password']
        
        try:
            db.session.add(new_user)
            db.session.commit()
            return new_user
        except Exception as e:
            db.session.rollback()
            abort(400, message={"error": str(e)})

@blp.route('/users/<int:user_id>')
class UserResource(MethodView):
    @blp.response(200, UserSchema)
    def get(self, user_id):
        """Get a specific user by ID"""
        user = User.query.get(user_id)
        if not user:
            abort(404, message={"error": "User not found"})
        return user

    @blp.arguments(UserUpdateSchema)
    @blp.response(200, UserSchema)
    def patch(self, user_data, user_id):
        """Update a user"""
        user = User.query.get(user_id)
        if not user:
            abort(404, message={"error": "User not found"})
        
        try:
            if 'username' in user_data:
                user.username = user_data['username']
            if 'email' in user_data:
                user.email = user_data['email']
                
            db.session.commit()
            return user
        except Exception as e:
            db.session.rollback()
            abort(400, message={"error": str(e)})

    @blp.response(204)
    def delete(self, user_id):
        """Delete a user"""
        user = User.query.get(user_id)
        if not user:
            abort(404, message={"error": "User not found"})
        
        try:
            db.session.delete(user)
            db.session.commit()
            return ""
        except Exception as e:
            db.session.rollback()
            abort(400, message={"error": str(e)})

# Route: Prompts
@blp.route('/prompts')
class PromptList(MethodView):
    @blp.response(200, PromptSchema(many=True))
    def get(self):
        """List all prompts"""
        prompts = Prompts.query.all()
        return prompts

    @blp.arguments(PromptSchema)
    @blp.response(201, PromptSchema)
    def post(self, prompt_data):
        """Create a new prompt"""
        new_prompt = Prompts(
            prompt=prompt_data['prompt']
        )
        
        try:
            db.session.add(new_prompt)
            db.session.commit()
            return new_prompt
        except Exception as e:
            db.session.rollback()
            abort(400, message={"error": str(e)})

@blp.route('/prompts/<int:prompt_id>')
class PromptResource(MethodView):
    @blp.response(200, PromptSchema)
    def get(self, prompt_id):
        """Get a specific prompt by ID"""
        prompt = Prompts.query.get(prompt_id)
        if not prompt:
            abort(404, message={"error": "Prompt not found"})
        return prompt

    @blp.response(204)
    def delete(self, prompt_id):
        """Delete a prompt"""
        prompt = Prompts.query.get(prompt_id)
        if not prompt:
            abort(404, message={"error": "Prompt not found"})
        
        try:
            db.session.delete(prompt)
            db.session.commit()
            return ""
        except Exception as e:
            db.session.rollback()
            abort(400, message={"error": str(e)})   

# Registration and login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            abort(401, message="Authentication required")
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('analyze_code'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.verify_password(password):
            session['user_id'] = user.id
            session.permanent = True
            flash('Successfully logged in!', 'success')
            return redirect(url_for('analyze_code')) # redirect to the function
        
        flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    if 'user_id' in session:
        session.clear()
        flash('Successfully logged out!', 'success')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('analyze_code'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('templates/register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('templates/register.html')
            
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return render_template('templates/register.html')
        
        new_user = User(username=username, email=email)
        new_user.password = password
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration', 'error')
            
    return render_template('register.html')

# main page
@app.route('/')
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        return render_template('index.html', user=user)
    return render_template('index.html')


# Route: analyze_code
@app.route('/analyze_code', methods=['GET', 'POST'])
@login_required
def analyze_code():
    if request.method == 'GET':
        return render_template('analyze.html')
    
    if request.method == 'POST':
        if 'user_id' in session:
            user = User.query.get(session['user_id'])

        code_snippet = request.form['code']
        corporate_rules = request.form.get('rules', '')  # Obtener las reglas corporativas del formulario

        # Construir el mensaje del sistema con o sin las reglas corporativas
        system_message = "You are a code analysis assistant. Analyze the following code for potential improvements or bugs. You must categorize the bugs or errors from a scale of 1 to 3, where 1 indicates a sever error that MUST be fixed to allow the program to run smoothly while 3 indicates a non optimal code that could be improved upon. For level 1 errors, suggest a solution that keeps the code original functionality."
        if corporate_rules.strip():
            system_message += f" Follow these corporate rules or standards: {corporate_rules.strip()}"

        messages = [
            {
                "role": "system",
                "content": system_message
            },
            {
                "role": "user",
                "content": code_snippet
            }
        ]

        try:
            response = openai.chat.completions.create(
                model="gpt-4o", 
                messages=messages,
                max_tokens=500,
                temperature=0.5,
            )
            
            analysis = response.choices[0].message.content.strip()
            new_prompt = Prompts(user_id=user.id, prompt=code_snippet, response=analysis)
            db.session.add(new_prompt)
            db.session.commit()
            return render_template('result.html', code=code_snippet, analysis=analysis)
        
        except Exception as e:
            db.session.rollback()
            abort(400, message={"error": str(e)})

# Optionally, add a health check endpoint
@app.route('/healthcheck')
def healthcheck():
    return {'status': 'healthy'}, 200

# Register blueprint
api.register_blueprint(blp)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)