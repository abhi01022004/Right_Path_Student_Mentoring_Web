from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from pymongo import MongoClient
from google.cloud import language_v1

app = Flask(__name__)
app.secret_key = 'supersecretkey'

client = MongoClient("mongodb://localhost:27017/")
db = client['right_path']
users_collection = db['users']
responses_collection = db['responses']

def analyze_text(text):
    client = language_v1.LanguageServiceClient()
    document = language_v1.Document(content=text, type_=language_v1.Document.Type.PLAIN_TEXT)

    sentiment = client.analyze_sentiment(document=document).document_sentiment
    categories = client.classify_text(document=document).categories
    entities = client.analyze_entities(document=document).entities

    return {
        "sentiment": {
            "score": sentiment.score,
            "magnitude": sentiment.magnitude
        },
        "categories": [{"name": cat.name, "confidence": cat.confidence} for cat in categories],
        "entities": [{"name": entity.name, "type": language_v1.Entity.Type(entity.type_).name} for entity in entities]
    }

@app.route('/')
def index():
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register():
    name = request.form['name']
    phone = request.form['phone']
    password = request.form['password']

    existing_user = users_collection.find_one({"phone": phone})
    if existing_user:
        flash('User already exists. Please sign in.', 'error')
        return redirect(url_for('signin'))

    users_collection.insert_one({
        "name": name,
        "phone": phone,
        "password": password
    })

    flash('Registration successful! Please sign in.', 'success')
    return redirect(url_for('signin'))

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        phone = request.form['phone']
        password = request.form['password']

        user = users_collection.find_one({"phone": phone, "password": password})
        if user:
            session['phone'] = phone
            flash(f'Sign In successful for {user["name"]}.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials. Please try again.', 'error')
            return redirect(url_for('signin'))

    return render_template('signin.html')

@app.route('/student_form', methods=['GET', 'POST'])
def student_form():
    if 'phone' not in session:
        flash("Please sign in first.", "error")
        return redirect(url_for('signin'))

    if request.method == 'POST':
        response_data = {
            "phone": session['phone'],
            "class": request.form['class'],
            "favorite_subjects": request.form['favorite_subjects'],
            "extracurricular_activities": request.form['extracurricular_activities'],
            "ideal_day": request.form['ideal_day'],
            "hobbies": request.form['hobbies'],
            "hobby_origin": request.form['hobby_origin'],
            "hobby_interest": request.form['hobby_interest'],
            "skills": request.form['skills'],
            "awards": request.form['awards'],
            "easy_activities": request.form['easy_activities'],
            "career_interests": request.form['career_interests'],
            "career_inspiration": request.form['career_inspiration'],
            "career_day": request.form['career_day'],
            "values": request.form['values'],
            "long_term_goals": request.form['long_term_goals'],
            "challenges": request.form['challenges'],
            "motivation": request.form['motivation']
        }

        combined_text = ' '.join(response_data.values())
        analysis_result = analyze_text(combined_text)

        response_data["analysis_result"] = analysis_result
        responses_collection.update_one(
            {"phone": session['phone']},
            {"$set": response_data},
            upsert=True
        )

        return redirect(url_for('dashboard'))

    return render_template('student_form.html')

@app.route('/dashboard')
def dashboard():
    if 'phone' not in session:
        flash("Please sign in.", "error")
        return redirect(url_for('signin'))

    phone = session['phone']
    user = users_collection.find_one({"phone": phone})
    response = responses_collection.find_one({"phone": phone})

    return render_template('dashboard.html', user=user, response=response)

@app.route('/api/suggest_career', methods=['POST'])
def suggest_career():
    data = request.json
    response_text = ' '.join([data.get(key, '') for key in data])
    analysis_result = analyze_text(response_text)
    return jsonify({'analysis_result': analysis_result})

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for('signin'))

if __name__ == '__main__':
    app.run(debug=True)
