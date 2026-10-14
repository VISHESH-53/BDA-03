
import re
from datetime import datetime, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from textblob import TextBlob

st.set_page_config(
    page_title="Social Media Trend Tracker",
    page_icon="📈",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background: #f5f8fc;
    color: #10213a;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #172536, #1d2b3c);
}
[data-testid="stSidebar"] * {
    color: #f5f8ff;
}
.main .block-container {
    padding-top: 1.5rem;
    max-width: 1600px;
}
h1, h2, h3 {
    color: #10213a;
}
[data-testid="stMetric"] {
    background: white;
    padding: 18px;
    border-radius: 14px;
    border: 1px solid #e5eaf2;
    box-shadow: 0 2px 8px rgba(20,40,70,.04);
}
[data-testid="stMetricLabel"] {
    color: #52647c;
}
[data-testid="stMetricValue"] {
    color: #10213a;
}
div[data-testid="stPlotlyChart"],
div[data-testid="stDataFrame"] {
    background: white;
    border: 1px solid #e5eaf2;
    border-radius: 14px;
    padding: 10px;
}
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown("# 📈 Social Media")
st.sidebar.markdown("## Trend Tracker")
page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Add Post", "View Posts", "Analysis"],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
st.sidebar.caption("Sentiment & Trend Analytics")

SAMPLE_POSTS = [
    ("AI technology is amazing", "Twitter", 4),
    ("The service is terrible", "Reddit", 4),
    ("I love the new application", "Twitter", 3),
    ("Technology is changing the world", "LinkedIn", 3),
    ("The product is disappointing", "Reddit", 2),
    ("Artificial intelligence is useful", "Twitter", 2),
    ("The latest update is excellent", "LinkedIn", 1),
    ("This application is frustrating", "Reddit", 1),
    ("AI creates exciting opportunities", "Twitter", 0),
    ("The business results are poor", "LinkedIn", 0)
]

def classify(text):
    polarity = TextBlob(text).sentiment.polarity
    if polarity > 0.05:
        label = "Positive"
    elif polarity < -0.05:
        label = "Negative"
    else:
        label = "Neutral"
    return label, polarity

def prepare_data(rows):
    records = []
    today = datetime.now().date()

    for i, row in enumerate(rows):
        post = str(row.get("Post", ""))
        sentiment, polarity = classify(post)

        date_value = row.get("Timestamp", today)
        try:
            date_value = pd.to_datetime(date_value).date()
        except Exception:
            date_value = today

        records.append({
            "Post ID": row.get("Post ID", i + 1),
            "Post": post,
            "Platform": row.get("Platform", "Twitter"),
            "Timestamp": date_value,
            "Sentiment": sentiment,
            "Polarity": polarity
        })

    return pd.DataFrame(records)

def load_mongodb_posts():
    try:
        from pymongo import MongoClient

        client = MongoClient(
            st.secrets["MONGO_URI"],
            serverSelectionTimeoutMS=4000
        )
        client.admin.command("ping")
        collection = client["SocialMediaDB"]["Posts"]
        rows = list(collection.find({}, {"_id": 0}).limit(1000))
        client.close()

        if rows:
            return prepare_data(rows), True

    except Exception:
        pass

    rows = []
    today = datetime.now().date()

    for i, (post, platform, days_ago) in enumerate(SAMPLE_POSTS, 1):
        rows.append({
            "Post ID": i,
            "Post": post,
            "Platform": platform,
            "Timestamp": today - timedelta(days=days_ago)
        })

    return prepare_data(rows), False

if "posts" not in st.session_state:
    st.session_state.posts = None

if st.session_state.posts is None:
    st.session_state.posts, st.session_state.db_connected = load_mongodb_posts()

df = st.session_state.posts.copy()

if page == "Add Post":
    st.title("Add Social Media Post")
    with st.form("add_post_form"):
        post_text = st.text_area("Post text")
        platform = st.selectbox(
            "Platform", ["Twitter", "Reddit", "LinkedIn", "Other"]
        )
        submitted = st.form_submit_button("Add Post")

        if submitted:
            if not post_text.strip():
                st.error("Please enter some post text.")
            else:
                sentiment, polarity = classify(post_text)
                new_row = pd.DataFrame([{
                    "Post ID": int(df["Post ID"].max()) + 1 if not df.empty else 1,
                    "Post": post_text.strip(),
                    "Platform": platform,
                    "Timestamp": datetime.now().date(),
                    "Sentiment": sentiment,
                    "Polarity": polarity
                }])

                st.session_state.posts = pd.concat(
                    [df, new_row], ignore_index=True
                )

                if st.session_state.db_connected:
                    try:
                        from pymongo import MongoClient

                        client = MongoClient(
                            st.secrets["MONGO_URI"],
                            serverSelectionTimeoutMS=4000
                        )
                        client["SocialMediaDB"]["Posts"].insert_one({
                            "Post ID": int(new_row.iloc[0]["Post ID"]),
                            "Post": post_text.strip(),
                            "Platform": platform,
                            "Timestamp": datetime.now().isoformat()
                        })
                        client.close()
                    except Exception:
                        st.warning(
                            "Post added to this session, but MongoDB save failed."
                        )

                st.success(f"Post added. Sentiment: {sentiment}")
                st.rerun()

elif page == "View Posts":
    st.title("All Social Media Posts")
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.download_button(
        "Download CSV",
        df.to_csv(index=False).encode("utf-8"),
        "social_media_posts.csv",
        "text/csv"
    )

elif page == "Analysis":
    st.title("Sentiment Analysis")

    counts = df["Sentiment"].value_counts().reindex(
        ["Positive", "Negative", "Neutral"], fill_value=0
    )
    st.bar_chart(counts)

    st.subheader("Average Sentiment Polarity")
    st.metric("Average Polarity", f"{df['Polarity'].mean():.3f}")

    st.subheader("Platform-wise Analysis")
    st.dataframe(
        df.groupby(["Platform", "Sentiment"]).size()
        .rename("Post Count").reset_index(),
        use_container_width=True,
        hide_index=True
    )

else:
    header, selector = st.columns([3, 1])

    with header:
        st.title("Social Media Trend Tracker")
        st.caption(
            "Analyze social media posts, track sentiment and discover trending keywords."
        )

    with selector:
        platforms = ["All Platforms"] + sorted(df["Platform"].unique().tolist())
        selected_platform = st.selectbox("Select Platform", platforms)

    if not st.session_state.db_connected:
        st.info(
            "Displaying sample data because MongoDB is unavailable or empty. "
            "Your dashboard remains functional."
        )

    sentiment_filter = st.sidebar.selectbox(
        "Filter Sentiment",
        ["All", "Positive", "Negative", "Neutral"]
    )

    filtered = df.copy()

    if selected_platform != "All Platforms":
        filtered = filtered[filtered["Platform"] == selected_platform]

    if sentiment_filter != "All":
        filtered = filtered[filtered["Sentiment"] == sentiment_filter]

    total = len(filtered)
    positive = int((filtered["Sentiment"] == "Positive").sum())
    negative = int((filtered["Sentiment"] == "Negative").sum())
    neutral = int((filtered["Sentiment"] == "Neutral").sum())

    st.markdown("### Overview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📝 Total Posts", total)
    c2.metric("😊 Positive Posts", positive,
              f"{positive / total * 100:.1f}%" if total else "0%")
    c3.metric("☹️ Negative Posts", negative,
              f"{negative / total * 100:.1f}%" if total else "0%")
    c4.metric("😐 Neutral Posts", neutral,
              f"{neutral / total * 100:.1f}%" if total else "0%")

    left, right = st.columns(2)

    with left:
        st.subheader("Sentiment Distribution")
        sentiment_counts = pd.DataFrame({
            "Sentiment": ["Positive", "Negative", "Neutral"],
            "Count": [positive, negative, neutral]
        })

        fig = px.pie(
            sentiment_counts,
            names="Sentiment",
            values="Count",
            color="Sentiment",
            color_discrete_map={
                "Positive": "#43b77a",
                "Negative": "#ef5350",
                "Neutral": "#4389f5"
            },
            hole=0.12
        )
        fig.update_traces(textinfo="percent", textfont_size=15)
        fig.update_layout(
            margin=dict(t=20, b=10, l=10, r=10),
            paper_bgcolor="white",
            plot_bgcolor="white",
            legend_title_text=""
        )
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Sentiment Trend Over Time")

        if not filtered.empty:
            trend = (
                filtered.groupby(["Timestamp", "Sentiment"])
                .size()
                .reset_index(name="Posts")
            )

            dates = pd.date_range(
                end=datetime.now().date(), periods=5, freq="D"
            ).date

            full_index = pd.MultiIndex.from_product(
                [dates, ["Positive", "Negative", "Neutral"]],
                names=["Timestamp", "Sentiment"]
            )

            trend = (
                trend.set_index(["Timestamp", "Sentiment"])
                .reindex(full_index, fill_value=0)
                .reset_index()
            )

            fig2 = px.line(
                trend,
                x="Timestamp",
                y="Posts",
                color="Sentiment",
                markers=True,
                color_discrete_map={
                    "Positive": "#43b77a",
                    "Negative": "#ef5350",
                    "Neutral": "#4389f5"
                }
            )
            fig2.update_layout(
                margin=dict(t=20, b=10, l=10, r=10),
                paper_bgcolor="white",
                plot_bgcolor="white",
                legend_title_text="",
                xaxis_title="Date",
                yaxis_title="Number of Posts"
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No posts match the selected filters.")

    left2, right2 = st.columns([1.15, 1])

    with left2:
        st.subheader("Recent Posts")

        if not filtered.empty:
            display_df = filtered.sort_values(
                "Timestamp", ascending=False
            ).copy()

            display_df["Timestamp"] = display_df["Timestamp"].astype(str)
            display_df = display_df.rename(columns={
                "Post": "Post Text",
                "Timestamp": "Date"
            })

            st.dataframe(
                display_df[
                    ["Post ID", "Post Text", "Platform", "Sentiment", "Date"]
                ].head(10),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No posts available.")

    with right2:
        st.subheader("Top Trending Keywords")

        stopwords = {
            "the", "and", "are", "for", "with", "is", "was",
            "this", "that", "new", "from", "you", "your",
            "have", "has", "its", "into", "about"
        }

        words = []
        for post in filtered["Post"]:
            tokens = re.findall(r"\b[a-zA-Z]{3,}\b", post.lower())
            words.extend(w for w in tokens if w not in stopwords)

        if words:
            keyword_df = (
                pd.Series(words).value_counts().head(8)
                .rename_axis("Keyword")
                .reset_index(name="Frequency")
            )

            fig3 = px.bar(
                keyword_df.sort_values("Frequency"),
                x="Frequency",
                y="Keyword",
                orientation="h",
                text="Frequency",
                color_discrete_sequence=["#4389f5"]
            )
            fig3.update_layout(
                margin=dict(t=10, b=10, l=10, r=10),
                paper_bgcolor="white",
                plot_bgcolor="white",
                xaxis_title="Frequency",
                yaxis_title="",
                showlegend=False
            )
            fig3.update_traces(textposition="outside")
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("No keywords to display.")

    st.markdown("---")
    csv = filtered.to_csv(index=False).encode("utf-8")

    st.download_button(
        "⬇️ Download Filtered Results (CSV)",
        data=csv,
        file_name="social_media_trends.csv",
        mime="text/csv"
    )

    if st.button("🔄 Refresh Dashboard"):
        st.session_state.posts, st.session_state.db_connected = load_mongodb_posts()
        st.rerun()
