import tempfile
import streamlit as st
from embedchain import App
from youtube_transcript_api import YouTubeTranscriptApi
from typing import Tuple, List, Dict
import urllib.parse
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def embedchain_bot(db_path: str, api_key: str) -> App:
    return App.from_config(
        config={
            "llm": {"provider": "openai", "config": {"model": "gpt-4", "temperature": 0.5, "api_key": api_key}},
            "vectordb": {"provider": "chroma", "config": {}},
            "embedder": {"provider": "openai", "config": {"api_key": api_key}},
        }
    )

def extract_video_id(video_url: str) -> str:
    if "youtube.com/watch?v=" in video_url:
        return video_url.split("v=")[-1].split("&")[0]
    elif "youtube.com/shorts/" in video_url:
        return video_url.split("/shorts/")[-1].split("?")[0]
    else:
        raise ValueError("Invalid YouTube URL")

def fetch_video_data(video_url: str) -> Tuple[str, str]:
    try:
        video_id = extract_video_id(video_url)
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([entry["text"] for entry in transcript])
        return "Unknown", transcript_text  # Title is set to "Unknown" since we're not fetching it
    except Exception as e:
        st.error(f"Error fetching transcript: {e}")
        return "Unknown", "No transcript available for this video."

def fetch_video_data_with_segments(video_url: str) -> Tuple[str, str, List[Dict]]:
    try:
        video_id = extract_video_id(video_url)
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = " ".join([entry["text"] for entry in transcript])
        return "Unknown", transcript_text, transcript  # Return transcript segments as well
    except Exception as e:
        st.error(f"Error fetching transcript: {e}")
        return "Unknown", "No transcript available for this video.", []

# Create Streamlit app
st.set_page_config(page_title="Chat with YouTube Video - planAI", page_icon="📺")

# Display planAI logo and branding
logo_path = os.path.join(os.path.dirname(__file__), "planAI.png")
st.image(logo_path, width=180)
st.title("Chat with YouTube Video, Powered by planAI 📺")
st.caption("This app allows you to chat with a YouTube video using planAI's technology. Just enter the video URL, and ask any question about it! It will event give you a timestamp of the relevant part of the video.")

# Get OpenAI API key from environment variable
openai_access_token = os.getenv("OPENAI_API_KEY")

if not openai_access_token:
    st.error("OPENAI_API_KEY not found in .env file. Please add it and restart the app.")
else:
    # Create a temporary directory to store the database
    db_path = tempfile.mkdtemp()
    # Create an instance of Embedchain App
    app = embedchain_bot(db_path, openai_access_token)
    # Get the YouTube video URL from the user
    video_url = st.text_input("Enter YouTube Video URL", type="default")
    transcript_segments = []
    video_id = None
    # Add the video to the knowledge base
    if video_url:
        try:
            video_id = extract_video_id(video_url)
            title, transcript, transcript_segments = fetch_video_data_with_segments(video_url)
            if transcript != "No transcript available for this video.":
                app.add(transcript, data_type="text", metadata={"title": title, "url": video_url})
                st.success(f"Added video '{title}' to knowledge base!")
            else:
                st.warning(f"No transcript available for video '{title}'. Cannot add to knowledge base.")
        except Exception as e:
            st.error(f"Error adding video: {e}")
        # Ask a question about the video
        prompt = st.text_input("Ask any question about the YouTube Video")
        # Chat with the video
        if prompt:
            try:
                answer = app.chat(prompt)
                st.write(answer)
                # --- Timestamp search logic ---
                if transcript_segments:
                    # Simple keyword search for the most relevant segment
                    best_segment = None
                    best_score = 0
                    for seg in transcript_segments:
                        score = sum(1 for word in prompt.lower().split() if word in seg["text"].lower())
                        if score > best_score:
                            best_score = score
                            best_segment = seg
                    if best_segment and best_score > 0:
                        start_time = int(best_segment["start"])
                        timestamp_url = f"https://www.youtube.com/watch?v={video_id}&t={start_time}s"
                        st.markdown(f"**Relevant timestamp:** [{start_time}s]({timestamp_url})")
            except Exception as e:
                st.error(f"Error chatting with the video: {e}")