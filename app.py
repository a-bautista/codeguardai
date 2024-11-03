from flask import Flask, request, session, render_template, redirect, url_for, flash
from flask.views import MethodView
import openai
import os
from dotenv import load_dotenv, find_dotenv
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from flask_smorest import Api, Blueprint, abort
from marshmallow import Schema, fields as ma_fields
from functools import wraps

load_dotenv(find_dotenv())
os.environ['OPENAI_API_KEY'] = os.environ.get("OPEN_AI")

app = Flask(__name__)

# Configure API with OpenAPI 3.0
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

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@db:5432/flask_db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
api = Api(app)

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
    prompt = ma_fields.Str(required=True)
    created_at = ma_fields.DateTime(dump_only=True)

# Database model
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

class Prompts(db.Model):
    __tablename__ = 'prompts'
    id = db.Column(db.Integer, primary_key=True)
    prompt = db.Column(db.String(200), unique=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    

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
    def put(self, user_data, user_id):
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

# Register blueprint
api.register_blueprint(blp)

# /analyze app route
@app.route('/analyze', methods=['GET', 'POST'])
def analyze_code():
    if request.method == 'POST':
        code_snippet = request.form['code']

        messages = [
            {
                "role": "system",
                "content": "You are a code analysis assistant. Analyze the following code for potential improvements or bugs."
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
            return {'code': code_snippet, 'analysis': analysis}
        except Exception as e:
            api.abort(500, f"An error occurred: {str(e)}")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            abort(401, message="Authentication required")
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.verify_password(password):
            session['user_id'] = user.id
            session.permanent = True
            flash('Successfully logged in!', 'success')
            return redirect(url_for('index'))
        
        flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
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

@app.route('/')
def index():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        return render_template('index.html', user=user)
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)