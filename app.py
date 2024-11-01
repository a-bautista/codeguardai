from flask import Flask, render_template, request
import openai
import os
from dotenv import load_dotenv, find_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request, jsonify
from datetime import datetime
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from flask_restx import Api, Resource, fields

load_dotenv(find_dotenv())
os.environ['OPENAI_API_KEY'] =  os.environ.get("OPEN_AI")

app = Flask(__name__)
api = Api(app, 
    version='1.0.0',
    title='codeguardai',
    description='API para servicios de codeguardai',
    doc='/swagger'
)

ns = api.namespace('crud', description='CRUD operations')
openai.api_key = os.getenv("OPENAI_KEY")

# Postgresql
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@db:5432/flask_db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Initialize SQLAlchemy
db = SQLAlchemy(app)
migrate = Migrate(app, db)

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

    def __repr__(self):
        return f'<User {self.username}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat()
        }
    
# swagger models
user_model = api.model('User', {
    'id': fields.Integer(readonly=True, description='User identifier'),
    'username': fields.String(required=True, description='Username'),
    'email': fields.String(required=True, description='User email'),
    'created_at': fields.DateTime(readonly=True, description='Account creation date')
})

code_analysis_model = api.model('CodeAnalysis', {
    'code': fields.String(required=True, description='Code snippet to analyze'),
})

code_analysis_response = api.model('CodeAnalysisResponse', {
    'code': fields.String(description='Original code snippet'),
    'analysis': fields.String(description='Analysis result')
})

user_input_model = api.model('UserInput', {
    'username': fields.String(required=True, description='Username'),
    'password': fields.String(required=True, description='Password'),
    'email': fields.String(required=True, description='User email')
})

@ns.route('/')
class AnalyzeCode(Resource):
    @ns.doc('analyze_code')
    @ns.expect(code_analysis_model)
    @ns.marshal_with(code_analysis_response)


    def post(self):
        """Analyze code snippet"""
        code_snippet = request.json.get('code')

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

# CRUD routes
@ns.route('/users')
class UserList(Resource):
    @ns.doc('list_users')
    @ns.marshal_list_with(user_model)
    def get(self):
        """List all users"""
        users = User.query.all()
        return [user.to_dict() for user in users]

    @ns.doc('create_user')
    @ns.expect(user_input_model)
    @ns.marshal_with(user_model, code=201)
    def post(self):
        """Create a new user"""
        data = request.json
        user = User(
            username=data['username'],
            email=data['email']
        )
        user.password = data['password']
        try:
            db.session.add(user)
            db.session.commit()
            return user.to_dict(), 201
        except Exception as e:
            db.session.rollback()
            api.abort(400, f"Error creating user: {str(e)}")

# @ns.route('/users')
# @app.route('/users', methods=['GET'])
# def get_users():
#     users = User.query.all()
#     return jsonify([user.to_dict() for user in users])


@ns.route('/users/<int:id>')
@ns.param('id', 'The user identifier')
class UserResource(Resource):
    @ns.doc('get_user')
    @ns.marshal_with(user_model)
    def get(self, id):
        """Get a user by ID"""
        user = User.query.get_or_404(id)
        return user.to_dict()

    @ns.doc('delete_user')
    @ns.response(204, 'User deleted')
    def delete(self, id):
        """Delete a user"""
        user = User.query.get_or_404(id)
        try:
            db.session.delete(user)
            db.session.commit()
            return '', 204
        except Exception as e:
            db.session.rollback()
            api.abort(500, f"Error deleting user: {str(e)}")

@app.route('/users')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)