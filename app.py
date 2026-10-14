
import streamlit as st
import pandas as pd
import plotly.express as px
from textblob import TextBlob
from pymongo import MongoClient
from datetime import datetime
from collections import Counter
import re

st.set_page_config(page_title="Social Media Trend Tracker", layout="wide")
st.title("Social Media Trend Tracker")
st.write("Sentiment Analysis and Trending Topic Dashboard")

posts = [
    "Artificial intelligence is amazing",
    "Technology is changing the world",
    "The new product is excellent",
    "The service is terrible",
    "I love artificial intelligence",
    "The latest update is disappointing",
    "Technology creates exciting opportunities",
    "The business results are poor",
    "AI is useful and innovative",
    "The new application is frustrating"
]

def analyze_sentiment(text):
    polarity = TextBlob(text).sentiment.polarity
    if polarity > 0.05:
        sentiment = "Positive"
    elif polarity < -0.05:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"
    return sentiment, polarity

data = []

for i, post in enumerate(posts, start=1):
    sentiment, polarity = analyze_sentiment(post)
    hashtags = re.findall(r"#\w+", post.lower())
    data.append({
        "Post ID": i,
        "Post": post,
        "Timestamp": datetime.now(),
        "Sentiment": sentiment,
        "Polarity": polarity,
        "Hashtags": hashtags
    })

df = pd.DataFrame(data)

st.sidebar.header("Dashboard Filters")
selected_sentiment = st.sidebar.selectbox(
    "Select Sentiment",
    ["All", "Positive", "Negative", "Neutral"]
)

filtered = df.copy()

if selected_sentiment != "All":
    filtered = filtered[filtered["Sentiment"] == selected_sentiment]

st.subheader("Key Performance Indicators")
c1, c2, c3, c4 = st.columns(4)

c1.metric("Total Posts", len(filtered))
c2.metric("Positive", int((filtered["Sentiment"] == "Positive").sum()))
c3.metric("Negative", int((filtered["Sentiment"] == "Negative").sum()))
c4.metric("Neutral", int((filtered["Sentiment"] == "Neutral").sum()))

if not filtered.empty:
    sentiment_counts = filtered["Sentiment"].value_counts().reset_index()
    sentiment_counts.columns = ["Sentiment", "Count"]

    st.subheader("Sentiment Distribution")
    fig1 = px.pie(
        sentiment_counts,
        names="Sentiment",
        values="Count",
        title="Social Media Sentiment"
    )
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("Trending Keywords")
    words = []
    for post in filtered["Post"]:
        words.extend(re.findall(r"\b[a-zA-Z]{3,}\b", post.lower()))

    stopwords = {
        "the", "and", "are", "for", "with", "is", "was",
        "this", "that", "new", "creates"
    }
    counts = Counter(w for w in words if w not in stopwords)
    trend_df = pd.DataFrame(
        counts.most_common(10),
        columns=["Keyword", "Frequency"]
    )

    if not trend_df.empty:
        fig2 = px.bar(
            trend_df,
            x="Keyword",
            y="Frequency",
            title="Most Frequent Keywords"
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Social Media Posts")
    st.dataframe(
        filtered[["Timestamp", "Post", "Sentiment", "Polarity"]],
        use_container_width=True,
        hide_index=True
    )

    st.download_button(
        "Download Results as CSV",
        filtered.to_csv(index=False),
        file_name="social_media_trends.csv",
        mime="text/csv"
    )

if st.button("Save Posts to MongoDB"):
    try:
        client = MongoClient(
            st.secrets["MONGO_URI"],
            serverSelectionTimeoutMS=5000
        )
        collection = client["SocialMediaDB"]["Posts"]
        records = df.copy()
        records["Timestamp"] = records["Timestamp"].astype(str)
        collection.insert_many(records.to_dict("records"))
        st.success("Posts saved successfully to MongoDB.")
        client.close()
    except Exception as e:
        st.error(f"MongoDB connection failed: {e}")
