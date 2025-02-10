import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import requests
import re
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase Firestore
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_credentials.json")  # Update with your Firebase JSON file
    firebase_admin.initialize_app(cred)

db = firestore.client()  # Firestore database instance

# Function to calculate the gratification score
def calculate_gratification_score(likes, shares, comments, thumbnail_quality, keyword_score, watch_time, delta_s,
                                  delta_t, iterations, ws, wt, a, b, c, d, e, f):
    s = a * likes + b * shares + c * comments  # Social gratification score (S)
    t = d * thumbnail_quality + e * keyword_score + f * watch_time  # Technological gratification score (T)
    fs = delta_s / iterations  # Change in engagement
    ft = delta_t / iterations  # Change in visibility
    g = (ws * s + wt * t) * (1 + (fs + ft) / 2)
    return g

# Function to normalize the gratification score
def normalize_gratification_score(G, G_max):
    k = 100 / np.log(1 + G_max)
    G_normalized = max(1, min(100, k * np.log(1 + G)))
    return G_normalized

# Function to fetch YouTube video statistics
def fetch_youtube_stats(api_key, video_url):
    video_id_match = re.search(r"v=([a-zA-Z0-9_-]+)", video_url)
    if not video_id_match:
        return {"error": "Invalid YouTube video URL"}
    video_id = video_id_match.group(1)

    api_url = f"https://www.googleapis.com/youtube/v3/videos"
    params = {"part": "statistics,snippet", "id": video_id, "key": api_key}

    response = requests.get(api_url, params=params)
    if response.status_code == 200:
        data = response.json()
        if "items" in data and len(data["items"]) > 0:
            stats = data["items"][0]["statistics"]
            snippet = data["items"][0]["snippet"]
            return {
                "title": snippet["title"],
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "views": int(stats.get("viewCount", 0)),
                "published_at": snippet["publishedAt"],
            }
        else:
            return {"error": "No video data found for the given URL"}
    else:
        return {"error": f"Failed to fetch data: {response.status_code}"}

# Function to store feedback in Firestore
def store_feedback(user_feedback, reaction):
    feedback_ref = db.collection("feedbacks")
    feedback_ref.add({"feedback": user_feedback, "reaction": reaction})
    st.success("Feedback submitted successfully!")

# Function to fetch all feedback from Firestore
def fetch_feedback():
    feedback_ref = db.collection("feedbacks").stream()
    return [{"Reaction": f.get("reaction"), "Feedback": f.get("feedback")} for f in feedback_ref]

# Admin login credentials
ADMIN_USERNAME = "Kavishka"
ADMIN_PASSWORD = "grat1234"

# Main application function
def main():
    st.title("YouTube Content Creation Simulation")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Equation Explanation", "Simulation", "YouTube Stats", "Admin Login", "Feedback Section"])

    # Equation Explanation Tab
    with tab1:
        st.subheader("Equation Explanation")
        st.latex(r"G = (w_s \cdot S + w_t \cdot T) \cdot \left(1 + \frac{F_s + F_t}{2}\right)")

    # Simulation Tab
    with tab2:
        st.subheader("Simulation Parameters")
        likes = st.number_input("Likes", value=1000)
        shares = st.number_input("Shares", value=500)
        comments = st.number_input("Comments", value=200)
        thumbnail_quality = st.slider("Thumbnail Quality (1-10)", 1, 10, 5)
        keyword_score = st.slider("Keyword Optimization Score (1-100)", 1, 100, 50)
        watch_time = st.number_input("Watch Time (seconds)", value=300)
        delta_s = st.number_input("ΔS (Change in engagement)", value=10.0)
        delta_t = st.number_input("ΔT (Change in visibility)", value=20.0)
        iterations = st.number_input("Iterations", value=100.0)
        ws = st.slider("Weight for Social Gratification (ws)", 0.0, 1.0, 0.6)
        wt = st.slider("Weight for Technological Gratification (wt)", 0.0, 1.0, 0.4)
        a = st.slider("Weight for Likes (a)", 0.0, 1.0, 0.3)
        b = st.slider("Weight for Shares (b)", 0.0, 1.0, 0.4)
        c = st.slider("Weight for Comments (c)", 0.0, 1.0, 0.3)
        d = st.slider("Weight for Thumbnail Quality (d)", 0.0, 1.0, 0.3)
        e = st.slider("Weight for Keyword Optimization (e)", 0.0, 1.0, 0.4)
        f = st.slider("Weight for Watch Time (f)", 0.0, 1.0, 0.3)

        if st.button("Compute Gratification Score"):
            g = calculate_gratification_score(likes, shares, comments, thumbnail_quality, keyword_score,
                                               watch_time, delta_s, delta_t, iterations, ws, wt, a, b, c, d, e, f)
            g_normalized = normalize_gratification_score(g, 10000000)
            st.success(f"Normalized Gratification Score: {g_normalized:.2f}")

    # YouTube Stats Tab
    with tab3:
        st.subheader("YouTube Video Statistics")
        api_key = st.text_input("YouTube Data API Key", type="password")
        video_url = st.text_input("YouTube Video URL")
        if st.button("Fetch Video Stats") and api_key and video_url:
            stats = fetch_youtube_stats(api_key, video_url)
            if "error" in stats:
                st.error(stats["error"])
            else:
                st.success(f"Title: {stats['title']}")
                st.metric("Likes", stats["likes"])
                st.metric("Comments", stats["comments"])
                st.metric("Views", stats["views"])

    # Admin Login Tab
    with tab4:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login") and username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            show_admin_dashboard()

    # Feedback Section Tab
    with tab5:
        feedback = st.text_area("Leave your feedback here:")
        thumbs_up = st.button("👍 Thumbs Up")
        thumbs_down = st.button("👎 Thumbs Down")

        if thumbs_up or thumbs_down:
            store_feedback(feedback, "Thumbs Up" if thumbs_up else "Thumbs Down")

# Admin Dashboard
def show_admin_dashboard():
    st.title("Admin Dashboard")
    feedback_data = fetch_feedback()
    if feedback_data:
        df = pd.DataFrame(feedback_data)
        st.dataframe(df)
        fig = px.pie(df, names="Reaction", title="Feedback Distribution")
        st.plotly_chart(fig)

if __name__ == "__main__":
    main()













































