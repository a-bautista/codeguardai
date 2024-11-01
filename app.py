from flask import Flask, render_template, request
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

class MessageSchema(Schema):
    message = ma_fields.Str(required=True)

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

# Blueprint for CRUD operations
blp = Blueprint(
    'crud', 'crud',
    url_prefix='/crud',
    description='CRUD operations'
)

@blp.route('/')
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
            abort(400, message=str(e))

@blp.route('/<int:user_id>')
class UserResource(MethodView):
    @blp.response(200, UserSchema)
    @blp.response(404, MessageSchema)
    def get(self, user_id):
        """Get a specific user by ID"""
        user = User.query.get_or_404(user_id)
        return user

    @blp.arguments(UserUpdateSchema)
    @blp.response(200, UserSchema)
    @blp.response(404, MessageSchema)
    def put(self, user_data, user_id):
        """Update a user"""
        user = User.query.get_or_404(user_id)
        
        try:
            if 'username' in user_data:
                user.username = user_data['username']
            if 'email' in user_data:
                user.email = user_data['email']
                
            db.session.commit()
            return user
        except Exception as e:
            db.session.rollback()
            abort(400, message=str(e))

    @blp.response(200, MessageSchema)
    @blp.response(404, MessageSchema)
    def delete(self, user_id):
        """Delete a user"""
        user = User.query.get_or_404(user_id)
        
        try:
            db.session.delete(user)
            db.session.commit()
            return {"message": "User deleted successfully"}
        except Exception as e:
            db.session.rollback()
            abort(400, message=str(e))

# Register blueprint
api.register_blueprint(blp)
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)