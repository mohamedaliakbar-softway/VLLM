# Video Shorts Generator - Replit Setup

## Overview
An AI-powered SaaS application that automatically creates engaging 15-30 second marketing shorts from long-form YouTube videos (15-30 minutes). It leverages Google's Gemini AI to identify compelling segments, aiming to transform videos into multi-platform social media content rapidly. The business vision is to provide a fast, AI-driven solution for content creators and marketers to repurpose long-form video into high-engagement short-form content, significantly reducing manual editing time and boosting content reach across platforms like YouTube Shorts, Instagram Reels, Facebook, LinkedIn, and WhatsApp.

## User Preferences
- All authentication has been removed as per user request.
- The user prefers a rapid, iterative development approach.
- The user prefers detailed explanations of changes and functionality.
- The user wants the AI to act as a conversational video editing agent, understanding natural language commands for video manipulation.
- The user prefers a clear, concise communication style.
- The user wants the agent to make changes to the codebase and then explain what those changes were, including a summary of why the change was made, and any alternative approaches considered.

## System Architecture
The application features a React + Vite frontend and a FastAPI (Python 3.11) backend, communicating via REST APIs and Server-Sent Events (SSE) for real-time updates.

**UI/UX Decisions:**
- **Design:** The frontend is designed with a professional, dark-themed interface, matching the "HighlightAI" reference images.
- **Landing Page:** Includes a navigation bar, a hero section with a gradient title, a single YouTube URL input field, and feature badges emphasizing "AI-Powered Detection," "2-Minute Processing," and "Multi-Platform Export."
- **Video Editor:** A three-panel layout comprises:
    - **Left Panel:** AI chat interface for conversational editing with quick action buttons.
    - **Center Panel:** Video player with playback controls, clip labels, and a timeline for clip management, selection, and reordering.
    - **Right Panel:** Properties panel for editing clip titles, time ranges, duration, and order.
- **Workflow:** Users provide a YouTube URL, are instantly redirected to an editor with a blurred thumbnail, and receive live progress updates as the backend processes the video. The blurred thumbnail is replaced with a playable video when ready.

**Technical Implementations:**
- **Core Processing:** Optimized to reduce video processing from 10 minutes to 15-20 seconds by using a transcript-first analysis pipeline:
    1.  **Transcript Extraction:** Subtitles are extracted without full video download.
    2.  **AI Analysis:** Gemini analyzes the transcript to identify up to three engaging segments.
    3.  **Selective Download:** Only identified 30-second segments are downloaded using FFmpeg.
    4.  **Fast Encoding:** Shorts are created in parallel using FFmpeg's `veryfast` preset.
- **Conversational AI Editing:** An AI-powered `VideoEditingAgent` (using Gemini) processes natural language commands for video operations (trim, shorten, speed adjust, split clips).
- **Captioning:** Live captions are generated using Vosk (offline) with Gemini as an online fallback, supporting multiple caption styles (bold_modern, elegant_serif, fun_playful).
- **Database:** PostgreSQL is used for persistence, storing projects and generated shorts via SQLAlchemy ORM.
- **Error Handling:** Robust error handling includes retry logic with exponential backoff for YouTube API requests to mitigate rate limiting and handling of browser cookie issues with `yt-dlp`.
- **Dual Storage:** Memory-based tracking for real-time job status and database for long-term project persistence.

**Feature Specifications:**
- Direct YouTube URL processing.
- AI-powered highlight detection.
- Real-time video editing via AI chat.
- Automatic clipping for various social platforms.
- Generation of up to 3 optimized shorts per video.
- Support for live captions and multiple caption styles.

## External Dependencies
- **AI Service:** Google Gemini AI (2.5 Flash) for video analysis and conversational editing.
- **Video Processing:**
    - FFmpeg for efficient video downloading, clipping, and encoding.
    - `yt-dlp` for YouTube video downloading and metadata extraction.
    - `moviepy` for supplementary video editing operations.
    - Vosk for offline speech recognition and caption generation.
- **Database:** PostgreSQL for persistent storage of project data and generated shorts.
- **Frontend Framework:** React 19 with Vite.
- **Routing:** React Router.
- **API Communication:** Axios.
- **Icons:** Lucide React.