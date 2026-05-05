from flask import Flask, request, jsonify, send_from_directory, redirect, session
from pymongo import MongoClient
import bcrypt
import numpy as np
from PIL import Image
from keras.models import load_model
from flask_cors import CORS
from datetime import datetime
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Image as RLImage
import base64
import os
import gdown   # ✅ ADDED

app = Flask(
    __name__,
    static_folder="../frontend",
    static_url_path=""
)

#SESSION CONFIGRATION
app.secret_key = "supersecretkey"
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_HTTPONLY"] = True

#CORS
CORS(app, supports_credentials=True)

#DATABASE 
# ✅ UPDATED TO MONGODB ATLAS
client = MongoClient("mongodb+srv://sushant6:sushant6@cluster0.kdxgvoq.mongodb.net/skin_app?retryWrites=true&w=majority")
db = client["skin_app"]

users = db["users"]
history = db["history"]

#MODEL
# ✅ GOOGLE DRIVE DOWNLOAD ADDED
MODEL_PATH = "skin_cancer_cnn.h5"

if not os.path.exists(MODEL_PATH):
    print("Downloading model from Google Drive...")

    url = "https://drive.google.com/uc?id=1MPRUAK8PSxUH4L7DydaJiTUhyg2UxFHO"

    gdown.download(url, MODEL_PATH, quiet=False)

model = load_model(MODEL_PATH)

#FRONTEND ROUTES
@app.route("/")
def home():
    return send_from_directory(app.static_folder, "login.html")

@app.route("/signup-page")
def signup_page():
    return send_from_directory(app.static_folder, "signup.html")

@app.route("/index")
def index_page():
    if "user" not in session:
        return redirect("/")
    return send_from_directory(app.static_folder, "index.html")

# AUTH
@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    username = data["username"]
    password = data["password"]

    if users.find_one({"username": username}):
        return jsonify({"message": "User already exists"}), 400

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    users.insert_one({"username": username, "password": hashed})

    return jsonify({"message": "Signup successful"})


@app.route("/login", methods=["POST"])
def login():
    data = request.json
    user = users.find_one({"username": data["username"]})

    if user and bcrypt.checkpw(data["password"].encode(), user["password"]):
        session["user"] = data["username"]
        return jsonify({"message": "Login successful"})
    
    return jsonify({"message": "Invalid credentials"}), 401


@app.route("/logout", methods=["GET"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})

# SMART AI
def get_risk(confidence):
    if confidence > 0.85:
        return "High"
    elif confidence > 0.60:
        return "Medium"
    else:
        return "Low"

def get_explanation(result):
    explanations = {
        "Malignant": "Irregular shape, uneven color, and asymmetry detected.",
        "Benign": "Regular shape and uniform color detected."
    }
    return explanations.get(result, "No explanation available.")


# PREDICT
@app.route("/predict", methods=["POST"])
def predict():
    if "user" not in session:
        return jsonify({"message": "Unauthorized"}), 401

    file = request.files["file"]

    #Image processing:-
    img = Image.open(file).convert("RGB")
    img = img.resize((224, 224))

    arr = np.array(img) / 255.0
    arr = np.expand_dims(arr, axis=0)

    #Prediction:-
    prediction = model.predict(arr)[0][0]

    #Label:-
    result = "Malignant" if prediction > 0.5 else "Benign"

    # Confidence:-
    confidence = float(prediction if prediction > 0.5 else 1 - prediction)

    # Risk:-
    risk = get_risk(confidence)

    # Explanation:-
    explanation = get_explanation(result)

    # SAVE TO DATABASE:-
    record = {
        "username": session["user"],
        "prediction": result,
        "confidence": confidence,
        "risk": risk,
        "explanation": explanation,
        "date": datetime.now()
    }

    history.insert_one(record)

    return jsonify({
        "prediction": result,
        "confidence": f"{confidence * 100:.2f}%",
        "risk": risk,
        "explanation": explanation
    })

# HISTORY 
@app.route("/history-page")
def history_page():
    if "user" not in session:
        return redirect("/")
    return send_from_directory(app.static_folder, "history.html")

@app.route("/history", methods=["GET"])
def get_history():
    if "user" not in session:
        return jsonify({"message": "Unauthorized"}), 401

    user_history = list(
        history.find(
            {"username": session["user"]},
            {"_id": 0}
        ).sort("date", -1)
    )

    # ✅ FORMAT DATE PROPERLY
    for record in user_history:
        if "date" in record:
            record["date"] = record["date"].strftime("%d-%m-%Y %I:%M %p")

    return jsonify(user_history)

# DOWNLOAD REPORT

  
# DOWNLOAD REPORT
@app.route("/download-report", methods=["POST", "GET"])
def download_report():
    print("DOWNLOAD REPORT CALLED")  # debug

    if "user" not in session:
        return jsonify({"message": "Unauthorized"}), 401
    
    data = request.get_json() or {}   # ✅ FIXED (safe)

    try:
        os.makedirs("reports", exist_ok=True)
        filepath = os.path.join("reports", "report.pdf")

        doc = SimpleDocTemplate(filepath)
        styles = getSampleStyleSheet()

        content = []
        content.append(Paragraph("<b>SkinAI Diagnostic Report</b>", styles["Title"]))
        content.append(Spacer(1, 12))

        content.append(Paragraph(f"<b>Patient:</b> {session['user']}", styles["Normal"]))
        content.append(Paragraph(f"<b>Date:</b> {datetime.now().strftime('%d-%m-%Y %H:%M')}", styles["Normal"]))
        content.append(Spacer(1, 10))

        # ✅ SAFE IMAGE HANDLING
        image_path = None

        if "image" in data and data["image"]:
            try:
                image_data = data["image"].split(",")[1]
                image_path = os.path.join("reports", "temp.png")

                with open(image_path, "wb") as f:
                    f.write(base64.b64decode(image_data))
            except Exception as e:
                print("Image error:", e)
                image_path = None

        if image_path and os.path.exists(image_path):
            content.append(Paragraph("<b>Uploaded Image:</b>", styles["Normal"]))
            content.append(Spacer(1, 6))
            content.append(RLImage(image_path, width=200, height=200))
            content.append(Spacer(1, 12))

        content.append(Paragraph("<b>Analysis Result</b>", styles["Heading2"]))
        content.append(Spacer(1, 8))

        content.append(Paragraph(f"<b>Prediction:</b> {data.get('prediction', 'N/A')}", styles["Normal"]))
        content.append(Paragraph(f"<b>Confidence:</b> {data.get('confidence', 'N/A')}", styles["Normal"]))

        risk = data.get("risk", "Low")
        risk_color = "red" if risk == "High" else "orange" if risk == "Medium" else "green"

        content.append(Paragraph(
            f"<b>Risk Level:</b> <font color='{risk_color}'>{risk}</font>",
            styles["Normal"]
        ))

        content.append(Spacer(1, 10))
        content.append(Paragraph("<b>AI Explanation</b>", styles["Heading3"]))
        content.append(Paragraph(data.get("explanation", "No explanation available"), styles["Normal"]))
        content.append(Spacer(1, 12))

        content.append(Paragraph(
            "<i>This AI-based analysis is not a medical diagnosis. Please consult a professional.</i>",
            styles["Italic"]
        ))

        doc.build(content)

        return send_from_directory("reports", "report.pdf", as_attachment=True)
    
    except Exception as e:
        print("PDF ERROR:", e)
        return jsonify({"error": str(e)}), 500
    

# RUN 
if __name__ == "__main__":
    app.run(debug=True)