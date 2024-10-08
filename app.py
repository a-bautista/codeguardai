from flask import Flask, render_template, request
import openai
import os

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
            # Adjust the API call according to the latest version (>= 1.0.0)
            response = openai.chat.completions.create(
                model="gpt-4o",  # Use "gpt-4" if you have access
                messages=messages,
                max_tokens=500,
                temperature=0.5,
            )
            # Extracting the first response from the completion
            analysis = response.choices[0].message.content.strip()
        except Exception as e:
            analysis = f"An error occurred: {e}"

        return render_template('result.html', code=code_snippet, analysis=analysis)
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
