from flask import Flask, render_template, request
import openai
import os
from dotenv import load_dotenv, find_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, request, jsonify
from datetime import datetime
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv(find_dotenv())
os.environ['OPENAI_API_KEY'] =  os.environ.get("OPEN_AI")

app = Flask(__name__)
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

@app.route('/', methods=['GET', 'POST'])
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
        except Exception as e:
            analysis = f"An error occurred: {e}"

        return render_template('result.html', code=code_snippet, analysis=analysis)
    return render_template('index.html')

# CRUD routes
@app.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()
    
    required_fields = ['username', 'email', 'password']
    if not all(field in data for field in required_fields):
        return jsonify({
            'error': 'Missing required fields',
            'required_fields': required_fields
        }), 400

    new_user = User(
        username=data['username'],
        email=data['email']
    )
    
    new_user.password = data['password']
    
    try:
        db.session.add(new_user)
        db.session.commit()
        return jsonify(new_user.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/users', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])

@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify(user.to_dict())

@app.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    try:
        if 'username' in data:
            user.username = data['username']
        if 'email' in data:
            user.email = data['email']
            
        db.session.commit()
        return jsonify(user.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@app.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    try:
        db.session.delete(user)
        db.session.commit()
        return jsonify({'message': 'User deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)