from flask import Flask, render_template, request
import openai
import os
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
os.environ['OPENAI_API_KEY'] =  os.environ.get("OPEN_AI")

app = Flask(__name__)

openai.api_key = os.getenv("OPENAI_KEY")

@app.route('/', methods=['GET', 'POST'])
def analyze_code():
    if request.method == 'POST':
        code_snippet = request.form['code']

        # Define the messages for OpenAI Chat API
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

if __name__ == '__main__':
    app.run(debug=True)
