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
    # Extract the video ID from the URL
    video_id_match = re.search(r"v=([a-zA-Z0-9_-]+)", video_url)
    if not video_id_match:
        return {"error": "Invalid YouTube video URL"}
    video_id = video_id_match.group(1)

    # API endpoint and parameters
    api_url = f"https://www.googleapis.com/youtube/v3/videos"
    params = {
        "part": "statistics,snippet",
        "id": video_id,
        "key": api_key,
    }

    # Send the API request
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
                "dislikes": "Unavailable (YouTube doesn't provide this anymore)",  # Dislikes are no longer public
                "shares": "Unavailable (YouTube API doesn't provide this)",
                "published_at": snippet["publishedAt"],
            }
        else:
            return {"error": "No video data found for the given URL"}
    else:
        return {"error": f"Failed to fetch data: {response.status_code}"}


# Admin login credentials
ADMIN_USERNAME = "Kavishka"
ADMIN_PASSWORD = "grat1234"

# Initialize feedback storage
if "feedback_data" not in st.session_state:
    st.session_state["feedback_data"] = []

# Function to store feedback in Firestore
def store_feedback(user_feedback, reaction):
    feedback_ref = db.collection("feedbacks")
    feedback_ref.add({"feedback": user_feedback, "reaction": reaction})
    st.success("Feedback submitted successfully!")

# Main application function
def main():
    st.title("YouTube Content Creation Simulation")
    st.markdown("""
    Explore how adjustments in social and technological factors impact the Gratification Score.
    """)

    # Tabs for different functionalities
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Equation Explanation", "Simulation", "YouTube Stats", "Admin Login", "Feedback Section"])

    # Equation Explanation Tab
    with tab1:
        st.subheader("Equation Explanation")
        st.markdown("""
        The Gratification Score (**G**) is calculated using a combination of Social Gratification (**S**) and Technological Gratification (**T**) along with engagement and visibility factors.
        """)
        st.latex(r"G = (w_s \cdot S + w_t \cdot T) \cdot \left(1 + \frac{F_s + F_t}{2}\right)")
        st.write("Where:")
        st.markdown("""
        - **S (Social Gratification)** = a * Likes + b * Shares + c * Comments
        - **T (Technological Gratification)** = d * Thumbnail Quality + e * Keyword Optimization + f * Watch Time
        - **F_s (Change in Engagement)** = ΔS / Iterations
        - **F_t (Change in Visibility)** = ΔT / Iterations
        - **w_s (Social Weight)** = Weight assigned to Social Gratification
        - **w_t (Technological Weight)** = Weight assigned to Technological Gratification
        """)

    # Simulation Tab
    with tab2:
        st.subheader("Simulation Parameters")

        likes = st.number_input("Likes", value=1000, help="Number of likes for the content")
        shares = st.number_input("Shares", value=500, help="Number of shares for the content")
        comments = st.number_input("Comments", value=200, help="Number of comments for the content")
        thumbnail_quality = st.slider("Thumbnail Quality (1-10)", 1, 10, 5,
                                      help="Quality of the thumbnail (1: Poor, 10: Excellent)")
        keyword_score = st.slider("Keyword Optimization Score (1-100)", 1, 100, 50,
                                  help="Effectiveness of the keywords used")
        watch_time = st.number_input("Watch Time (seconds)", value=300, help="Average watch time for the content")

        delta_s = st.number_input("ΔS (Change in engagement)", value=10.0, help="Change in engagement metrics over iterations")
        delta_t = st.number_input("ΔT (Change in visibility)", value=20.0, help="Change in visibility metrics over iterations")
        iterations = st.number_input("Iterations", value=100.0, help="Number of iterations for optimization")

        ws = st.slider("Weight for Social Gratification (ws)", 0.0, 1.0, 0.6)
        wt = st.slider("Weight for Technological Gratification (wt)", 0.0, 1.0, 0.4)
        if not np.isclose(ws + wt, 1.0):
            st.error("The sum of weights for Social and Technological Gratification must be 1!")

        a = st.slider("Weight for Likes (a)", 0.0, 1.0, 0.3)
        b = st.slider("Weight for Shares (b)", 0.0, 1.0, 0.4)
        c = st.slider("Weight for Comments (c)", 0.0, 1.0, 0.3)
        if not np.isclose(a + b + c, 1.0):
            st.error("The sum of weights for Likes, Shares, and Comments must be 1!")

        d = st.slider("Weight for Thumbnail Quality (d)", 0.0, 1.0, 0.3)
        e = st.slider("Weight for Keyword Optimization (e)", 0.0, 1.0, 0.4)
        f = st.slider("Weight for Watch Time (f)", 0.0, 1.0, 0.3)
        if not np.isclose(d + e + f, 1.0):
            st.error("The sum of weights for Thumbnail Quality, Keyword Optimization, and Watch Time must be 1!")

        g_max_dynamic = st.number_input("Expected Maximum Gratification Score (G_max)", value=10000000.0)

        if st.button("Compute Gratification Score"):
            g = calculate_gratification_score(likes, shares, comments, thumbnail_quality, keyword_score,
                                               watch_time, delta_s, delta_t, iterations, ws, wt, a, b, c, d, e, f)
            g_normalized = normalize_gratification_score(g, g_max_dynamic)

            st.success(f"Raw Gratification Score: {g:.2f}")
            st.success(f"Normalized Gratification Score: {g_normalized:.2f}")

            if g_normalized > 50:
                st.success("The content is good!")
            else:
                st.warning("The content needs some improvements.")

    # YouTube Stats Tab
    with tab3:
        st.subheader("YouTube Video Statistics")
        st.markdown("Enter a YouTube video URL to fetch its statistics.")
        api_key = st.text_input("YouTube Data API Key", type="password", help="Enter your YouTube Data API key here")
        video_url = st.text_input("YouTube Video URL", help="Paste a valid YouTube video URL here")

        if st.button("Fetch Video Stats"):
            if not api_key:
                st.error("Please provide a valid API key!")
            elif not video_url:
                st.error("Please provide a valid YouTube video URL!")
            else:
                stats = fetch_youtube_stats(api_key, video_url)
                if "error" in stats:
                    st.error(stats["error"])
                else:
                    st.success(f"Title: {stats['title']}")
                    st.metric("Likes", stats["likes"])
                    st.metric("Comments", stats["comments"])
                    st.metric("Views", stats["views"])
                    st.metric("Published Date", stats["published_at"])
                    st.info("Note: Dislikes and shares are currently unavailable via YouTube API.")

    # Admin Login Tab
    with tab4:
        st.subheader("Admin Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                st.success("Login successful!")
                show_admin_dashboard()
            else:
                st.error("Invalid credentials. Please try again.")

    # Feedback Section Tab
    with tab5:
        st.subheader("Feedback Section")
        feedback = st.text_area("Leave your feedback here:")
        thumbs_up = st.button("👍 Thumbs Up")
        thumbs_down = st.button("👎 Thumbs Down")

        if thumbs_up or thumbs_down:
            reaction = "Thumbs Up" if thumbs_up else "Thumbs Down"
            store_feedback(feedback, reaction)  # Save feedback in Firestore instead of session state

# Function to fetch all feedback from Firestore
def fetch_feedback():
    feedback_ref = db.collection("feedbacks").stream()
    return [{"Reaction": f.get("reaction"), "Feedback": f.get("feedback")} for f in feedback_ref]


# Admin Dashboard Function
def show_admin_dashboard():
    st.title("Admin Dashboard")
    st.markdown("### Feedback Analytics")

    feedback_data = pd.DataFrame(fetch_feedback())  # Fetch feedback from Firestore instead of session state


    if not feedback_data.empty:
        summary = feedback_data["Reaction"].value_counts().reset_index()
        summary.columns = ["Reaction", "Count"]
        st.write("Feedback Summary:")
        st.dataframe(summary)

        fig = px.pie(summary, names="Reaction", values="Count", title="Feedback Distribution")
        st.plotly_chart(fig)

        st.write("Detailed Feedback:")
        st.dataframe(feedback_data)
    else:
        st.info("No feedback available yet.")


if __name__ == "__main__":
    main()












































