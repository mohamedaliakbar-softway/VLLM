import { useState, useRef, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import {
  Play,
  Pause,
  Download,
  Share2,
  ArrowLeft,
  Send,
  Plus,
  ChevronUp,
  ChevronDown,
  Loader2,
  Type,
  Volume2,
  Wand2,
  Sparkles,
  Video,
  GripVertical,
  Maximize,
  Minimize,
} from "lucide-react";
import axios from "axios";
import { extractVideoId, getThumbnailUrl } from "../utils/youtube";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

function VideoEditor() {
  const navigate = useNavigate();
  const location = useLocation();
  const videoRef = useRef(null);
  const hasProcessedRef = useRef(false); // Track if video has been processed to prevent double submission
  const chatScrollRef = useRef(null); // Ref for auto-scrolling chat
  const progressIntervalRef = useRef(null); // Interval for progress animation

  const youtubeUrl = location.state?.youtubeUrl;
  const videoId = extractVideoId(youtubeUrl);
  const thumbnailUrl = getThumbnailUrl(videoId);

  // Processing states
  const [isProcessing, setIsProcessing] = useState(true);
  const [processingStatus, setProcessingStatus] =
    useState("Analyzing video...");
  const [processingProgress, setProcessingProgress] = useState(0);
  const [targetProgress, setTargetProgress] = useState(0); // Target progress for smooth animation
  const [error, setError] = useState("");
  const [retryCount, setRetryCount] = useState(0);
  const MAX_API_RETRIES = 3; // Maximum retries at API level

  // Loading steps matching backend processing - distributed across ~5 minutes total
  const [loadingSteps] = useState([
    { id: 1, text: "Connecting to YouTube", duration: 30000 },       // 30s
    { id: 2, text: "Extracting video transcript", duration: 40000 }, // 40s
    { id: 3, text: "Analyzing content with AI", duration: 50000 },   // 50s
    { id: 4, text: "Identifying key highlights", duration: 45000 },  // 45s
    { id: 5, text: "Downloading video segments", duration: 35000 },  // 35s
    { id: 6, text: "Applying smart cropping", duration: 40000 },     // 40s
    { id: 7, text: "Generating short clips", duration: 40000 },      // 40s
    { id: 8, text: "Finalizing your videos", duration: 20000 },      // 20s
  ]);
  const [currentLoadingStep, setCurrentLoadingStep] = useState(0);

  // Video playback states
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [selectedClipIndex, setSelectedClipIndex] = useState(0);

  // Publish modal states
  const [showPublishModal, setShowPublishModal] = useState(false);
  const [selectedPlatforms, setSelectedPlatforms] = useState([]);
  const [publishSettings, setPublishSettings] = useState({
    title: "",
    description: "",
    tags: "",
    aspectRatio: "9:16", // Default for shorts
  });

  // Chat states
  const [chatMessage, setChatMessage] = useState("");
  const [isAiThinking, setIsAiThinking] = useState(false);
  const [chatHistory, setChatHistory] = useState([
    {
      role: "assistant",
      content:
        "Hello! I'm your AI video editor assistant. I can help you trim clips, adjust duration, add effects, and more. Just tell me what you want to do!",
      timestamp: new Date().toISOString(),
    },
  ]);

  // Resizable chat panel states
  const [chatPanelWidth, setChatPanelWidth] = useState(320);
  const [isResizing, setIsResizing] = useState(false);
  const [isChatExpanded, setIsChatExpanded] = useState(false);

  // Caption states
  const [captions, setCaptions] = useState(null);
  const [selectedCaptionStyle, setSelectedCaptionStyle] =
    useState("bold_modern");
  const [showCaptionPreview, setShowCaptionPreview] = useState(false);
  const [currentCaption, setCurrentCaption] = useState('');
  
  // Caption generation timer states
  const [isCaptionGenerating, setIsCaptionGenerating] = useState(false);
  const [captionTimerSeconds, setCaptionTimerSeconds] = useState(90); // 1:30 in seconds
  const captionTimerRef = useRef(null);

  // Available caption styles
  const CAPTION_STYLES = {
    bold_modern: {
      name: "Bold & Modern",
      preview: "💪 HELLO WORLD",
      description: "Bold text with strong contrast",
    },
    elegant_serif: {
      name: "Elegant Serif",
      preview: "✨ Hello World",
      description: "Sophisticated serif font",
    },
    fun_playful: {
      name: "Fun & Playful",
      preview: "🎉 HELLO WORLD!",
      description: "Colorful and energetic",
    },
  };

  // Panel visibility states (collapsible panels)
  const [isLeftPanelVisible, setIsLeftPanelVisible] = useState(true);
  const [isRightPanelVisible, setIsRightPanelVisible] = useState(true);

  // Load panel preferences from localStorage
  useEffect(() => {
    const savedLeftPanel = localStorage.getItem("editor-left-panel-visible");
    const savedRightPanel = localStorage.getItem("editor-right-panel-visible");
    if (savedLeftPanel !== null)
      setIsLeftPanelVisible(savedLeftPanel === "true");
    if (savedRightPanel !== null)
      setIsRightPanelVisible(savedRightPanel === "true");
  }, []);

  // Save panel preferences to localStorage
  useEffect(() => {
    localStorage.setItem(
      "editor-left-panel-visible",
      String(isLeftPanelVisible),
    );
  }, [isLeftPanelVisible]);

  useEffect(() => {
    localStorage.setItem(
      "editor-right-panel-visible",
      String(isRightPanelVisible),
    );
  }, [isRightPanelVisible]);

  // Clips data
  const [clips, setClips] = useState([]);
  const selectedClip = clips[selectedClipIndex];
  const [clipTitle, setClipTitle] = useState(selectedClip?.title || "");
  const [clipDuration, setClipDuration] = useState(
    selectedClip?.duration || 30,
  );

  // Redirect if no YouTube URL
  useEffect(() => {
    if (!youtubeUrl) {
      navigate("/");
    }
  }, [youtubeUrl, navigate]);

  // Auto-advance loading steps every 60+ seconds
  useEffect(() => {
    if (!isProcessing) return;

    const timer = setTimeout(() => {
      setCurrentLoadingStep((current) => {
        // Cycle through steps 0-4, then back to 0
        return (current + 1) % loadingSteps.length;
      });
    }, loadingSteps[currentLoadingStep]?.duration || 70000);

    return () => clearTimeout(timer);
  }, [currentLoadingStep, isProcessing, loadingSteps]);

  // Smooth progress animation - fills proportionally between backend updates
  useEffect(() => {
    // Clear any existing interval
    if (progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
    }

    // If current progress is less than target, animate it
    if (processingProgress < targetProgress) {
      const updateInterval = 100; // Update every 100ms
      
      progressIntervalRef.current = setInterval(() => {
        setProcessingProgress((current) => {
          const next = current + 1;
          if (next >= targetProgress) {
            clearInterval(progressIntervalRef.current);
            return targetProgress;
          }
          return next;
        });
      }, updateInterval);
    } else if (processingProgress > targetProgress) {
      // If target is lower, jump immediately (shouldn't happen but just in case)
      setProcessingProgress(targetProgress);
    }

    return () => {
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }
    };
  }, [targetProgress, processingProgress]);

  // Process video function
  const processVideo = async () => {
    try {
      setProcessingStatus("Extracting transcript...");
      setError(null); // Clear previous errors

      const response = await axios.post("/api/v1/generate-shorts", {
        youtube_url: youtubeUrl,
        max_shorts: 1,
        platform: "youtube_shorts",
      });

      setProcessingStatus("AI analyzing highlights...");

      // Poll for results
      const jobId = response.data.job_id;
      const pollInterval = pollJobStatus(jobId);

      return pollInterval;
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to process video");
      setIsProcessing(false);
      setRetryCount(0); // Reset retry count on API error
      setChatHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Error: ${err.response?.data?.detail || "Failed to process video"}`,
        },
      ]);
      return null;
    }
  };

  // Trigger video processing on mount
  useEffect(() => {
    let pollInterval = null;

    if (youtubeUrl && !hasProcessedRef.current) {
      hasProcessedRef.current = true;
      processVideo().then((interval) => {
        pollInterval = interval;
      });
    }

    // Cleanup on unmount
    return () => {
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [youtubeUrl]);

  const pollJobStatus = (jobId) => {
    const maxAttempts = 60; // 1 minute timeout
    let attempts = 0;

    const poll = setInterval(async () => {
      try {
        attempts++;

        const response = await axios.get(`/api/v1/job/${jobId}`);
        const {
          status,
          shorts: generatedShorts,
          progress,
          percent,
          error, // Add error to destructuring
        } = response.data;

        console.log('Job polling response:', { status, progress, percent, attempts });

        if (progress) {
          setProcessingStatus(progress);
        }

        // Update target progress percentage (0-100) - will animate smoothly digit by digit
        if (typeof percent === "number") {
          setTargetProgress(Math.min(Math.max(percent, 0), 100));
        } else {
          // Estimate based on attempts if backend doesn't provide
          setTargetProgress(Math.min((attempts / maxAttempts) * 100, 95));
        }

        if (
          status === "completed" &&
          generatedShorts &&
          generatedShorts.length > 0
        ) {
          clearInterval(poll);
          setTargetProgress(100);
          setRetryCount(0); // Reset retry count on success

          // Convert shorts to clips format
          const newClips = generatedShorts.map((short, idx) => ({
            id: idx + 1,
            short_id: short.short_id, // Store backend short ID for publishing
            title: short.title || `Highlight ${idx + 1}`,
            startTime: formatTime(short.start_time),
            endTime: formatTime(short.end_time),
            duration: short.duration || short.duration_seconds || 30,
            filename: short.filename,
            url: short.download_url || `/api/v1/download/${short.filename}`,
          }));

          setClips(newClips);
          setIsProcessing(false);
          
          // Only add success message if it doesn't already exist
          setChatHistory((prev) => {
            const successMessage = `✅ Generated ${generatedShorts.length} video highlights! Click any clip to preview.`;
            const alreadyExists = prev.some(msg => msg.content === successMessage);
            
            if (alreadyExists) {
              return prev;
            }
            
            return [
              ...prev,
              {
                role: "assistant",
                content: successMessage,
                timestamp: new Date().toISOString(),
              },
            ];
          });
        } else if (status === "failed") {
          clearInterval(poll);
          
          // Check if error is "No highlights found" and retry if under limit
          // Use functional update to get current retry count
          setRetryCount((currentRetryCount) => {
            if (error === "No highlights found" && currentRetryCount < MAX_API_RETRIES) {
              const newRetryCount = currentRetryCount + 1;
              
              setChatHistory((prev) => [
                ...prev,
                {
                  role: "assistant",
                  content: `⚠️ No highlights found. Retrying automatically (attempt ${newRetryCount}/${MAX_API_RETRIES})...`,
                  timestamp: new Date().toISOString(),
                },
              ]);
              
              setProcessingStatus(`Retrying... (${newRetryCount}/${MAX_API_RETRIES})`);
              setTargetProgress(0);
              setProcessingProgress(0);
              
              // Wait 3 seconds before retry
              setTimeout(() => {
                processVideo().then((interval) => {
                  if (interval) {
                    // New polling started
                  }
                });
              }, 3000);
              
              return newRetryCount;
            } else {
              // Max retries reached or different error
              setError(error || "Video processing failed");
              setIsProcessing(false);
              
              const isMaxRetries = currentRetryCount >= MAX_API_RETRIES;
              setChatHistory((prev) => [
                ...prev,
                {
                  role: "assistant",
                  content: `❌ ${error || "Video processing failed"}${isMaxRetries ? " (max retries reached)" : ""}`,
                  timestamp: new Date().toISOString(),
                },
              ]);
              
              return 0; // Reset for next attempt
            }
          });
        } else if (attempts >= maxAttempts) {
          clearInterval(poll);
          setError("Processing timeout - please try again");
          setIsProcessing(false);
          setRetryCount(0);
        }
      } catch (err) {
        clearInterval(poll);
        setError("Failed to check processing status");
        setIsProcessing(false);
        setRetryCount(0);
        console.error("Error polling job status:", err);
      }
    }, 1000);

    return poll; // Return interval ID for cleanup
  };

  const formatTime = (timeInput) => {
    // Handle both timestamp strings (MM:SS or HH:MM:SS) and seconds (number)
    let seconds = 0;

    if (typeof timeInput === "string") {
      // Parse timestamp string (e.g., "00:30" or "01:30:45")
      const parts = timeInput.split(":").map(Number);
      if (parts.length === 2) {
        // MM:SS format
        seconds = parts[0] * 60 + parts[1];
      } else if (parts.length === 3) {
        // HH:MM:SS format
        seconds = parts[0] * 3600 + parts[1] * 60 + parts[2];
      }
    } else if (typeof timeInput === "number") {
      seconds = timeInput;
    }

    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);

    if (hours > 0) {
      return `${String(hours).padStart(2, "0")}:${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
    }
    return `00:${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  };

  // Sync properties panel with selected clip
  useEffect(() => {
    if (selectedClip) {
      setClipTitle(selectedClip.title);
      setClipDuration(selectedClip.duration);
    }
  }, [selectedClipIndex, selectedClip]);

  // Update clip in array when title or duration changes
  useEffect(() => {
    if (!selectedClip) return;

    const newClips = [...clips];
    if (newClips[selectedClipIndex]) {
      newClips[selectedClipIndex] = {
        ...newClips[selectedClipIndex],
        title: clipTitle,
        duration: clipDuration,
      };
      setClips(newClips);
    }
  }, [clipTitle, clipDuration]);

  // Chat panel resize handlers
  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isResizing) return;

      const newWidth = e.clientX;
      if (newWidth >= 280 && newWidth <= 600) {
        setChatPanelWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
    };

    if (isResizing) {
      document.addEventListener("mousemove", handleMouseMove);
      document.addEventListener("mouseup", handleMouseUp);
    }

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isResizing]);

  const handleResizeStart = () => {
    setIsResizing(true);
  };

  const toggleChatExpand = () => {
    if (isChatExpanded) {
      setChatPanelWidth(320); // Reset to default
      setIsChatExpanded(false);
    } else {
      setChatPanelWidth(600); // Expand to max width
      setIsChatExpanded(true);
    }
  };

  const handlePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
      } else {
        videoRef.current
          .play()
          .catch((err) => console.log("Autoplay prevented:", err));
      }
      setIsPlaying(!isPlaying);
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      const videoDuration = videoRef.current.duration;
      console.log('Video metadata loaded, duration:', videoDuration);
      setDuration(videoDuration);
      videoRef.current.volume = volume;
    }
  };

  const handleProgressClick = (e) => {
    if (videoRef.current && duration > 0) {
      const rect = e.currentTarget.getBoundingClientRect();
      const pos = (e.clientX - rect.left) / rect.width;
      const newTime = pos * duration;
      console.log('Progress bar clicked:', { pos, newTime, duration });
      videoRef.current.currentTime = newTime;
      setCurrentTime(newTime);
    }
  };

  const handleVolumeChange = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const pos = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    setVolume(pos);
    if (videoRef.current) {
      videoRef.current.volume = pos;
    }
    if (pos > 0) setIsMuted(false);
  };

  const toggleMute = () => {
    if (videoRef.current) {
      if (isMuted) {
        videoRef.current.volume = volume;
        setIsMuted(false);
      } else {
        videoRef.current.volume = 0;
        setIsMuted(true);
      }
    }
  };

  const formatTimeDisplay = (seconds) => {
    if (!seconds || Number.isNaN(seconds)) return "0:00";
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!chatMessage.trim() || isAiThinking) return;

    const userMessage = chatMessage.trim();
    setChatMessage("");

    // Add user message to chat
    setChatHistory((prev) => [
      ...prev,
      {
        role: "user",
        content: userMessage,
        timestamp: new Date().toISOString(),
      },
    ]);

    // Show AI thinking state
    setIsAiThinking(true);
    setChatHistory((prev) => [
      ...prev,
      {
        role: "assistant",
        content: "🤔 Processing your request...",
        timestamp: new Date().toISOString(),
        isThinking: true,
      },
    ]);

    try {
      // Call the new chat API with clips state
      const response = await axios.post("/api/v1/chat", {
        message: userMessage,
        clips: clips,
        selected_clip_index: selectedClipIndex,
      });

      const { clips: updatedClips, response: aiResponse, success } = response.data;

      // Remove thinking message
      setChatHistory((prev) => prev.filter((msg) => !msg.isThinking));

      // Show AI's response
      setChatHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          content: aiResponse || "Done!",
          timestamp: new Date().toISOString(),
        },
      ]);

      // Update clips if they changed
      if (success && updatedClips) {
        // Map updatedClips to proper format with URLs
        const formattedClips = updatedClips.map((clip, idx) => ({
          id: clip.id || idx + 1,
          title: clip.title || `Highlight ${idx + 1}`,
          startTime: clip.startTime || clip.start_time || "0:00",
          endTime: clip.endTime || clip.end_time || "0:30",
          duration: clip.duration || 30,
          filename: clip.filename,
          url: clip.download_url || clip.url || `/api/v1/download/${clip.filename}`,
          has_captions: clip.has_captions || clip.hasCaptions || false,
        }));
        
        setClips(formattedClips);
        
        // Force video reload for the current clip
        if (videoRef.current && formattedClips[selectedClipIndex]) {
          const newClip = formattedClips[selectedClipIndex];
          // Force reload by appending timestamp to bypass cache
          const videoUrl = `${newClip.url}?t=${Date.now()}`;
          videoRef.current.src = videoUrl;
          videoRef.current.load();
        }
      }
    } catch (error) {
      // Remove thinking message
      setChatHistory((prev) => prev.filter((msg) => !msg.isThinking));

      setChatHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `❌ Sorry, I encountered an error: ${error.response?.data?.detail || error.message}. Please try again.`,
          timestamp: new Date().toISOString(),
        },
      ]);
      console.error("Chat error:", error);
    } finally {
      setIsAiThinking(false);
    }
  };

  // Execute AI-determined actions
  const executeAiAction = async (action, parameters, updatedClips) => {
    switch (action) {
      case "trim_clip":
        if (
          parameters.clipIndex !== undefined &&
          parameters.startTime !== undefined &&
          parameters.endTime !== undefined
        ) {
          const newClips = [...clips];
          newClips[parameters.clipIndex] = {
            ...newClips[parameters.clipIndex],
            startTime: formatTime(parameters.startTime),
            endTime: formatTime(parameters.endTime),
            duration: parameters.endTime - parameters.startTime,
          };
          setClips(newClips);
        }
        break;

      case "update_duration":
        if (
          parameters.clipIndex !== undefined &&
          parameters.duration !== undefined
        ) {
          const newClips = [...clips];
          newClips[parameters.clipIndex] = {
            ...newClips[parameters.clipIndex],
            duration: parameters.duration,
          };
          setClips(newClips);
          setClipDuration(parameters.duration);
        }
        break;

      case "update_title":
        if (parameters.clipIndex !== undefined && parameters.title) {
          const newClips = [...clips];
          newClips[parameters.clipIndex] = {
            ...newClips[parameters.clipIndex],
            title: parameters.title,
          };
          setClips(newClips);
          setClipTitle(parameters.title);
        }
        break;

      case "select_clip":
        if (
          parameters.clipIndex !== undefined &&
          parameters.clipIndex < clips.length
        ) {
          setSelectedClipIndex(parameters.clipIndex);
        }
        break;

      case "delete_clip":
        if (parameters.clipIndex !== undefined) {
          const newClips = clips.filter(
            (_, idx) => idx !== parameters.clipIndex,
          );
          setClips(newClips);
          setSelectedClipIndex(Math.max(0, parameters.clipIndex - 1));
        }
        break;

      case "duplicate_clip":
        if (parameters.clipIndex !== undefined) {
          const clipToDuplicate = clips[parameters.clipIndex];
          const newClip = {
            ...clipToDuplicate,
            id: clips.length + 1,
            title: `${clipToDuplicate.title} (Copy)`,
          };
          setClips([...clips, newClip]);
        }
        break;

      case "update_clips":
        if (updatedClips && Array.isArray(updatedClips)) {
          setClips(updatedClips);
        }
        break;

      case "generate_captions":
        await generateCaptions();
        break;

      case "apply_caption_style": {
        const style = parameters.style || "bold_modern";
        setSelectedCaptionStyle(style);
        await applyCaptionStyle(style);
        break;
      }

      default:
        console.log("Unknown action:", action);
    }
  };

  const handleQuickAction = async (action) => {
    // Don't allow if AI is already thinking
    if (isAiThinking) return;

    // Check if this is "Add live captions" action
    const isCaptionAction = action.toLowerCase().includes("caption");
    
    if (isCaptionAction) {
      // Start the caption generation timer
      setIsCaptionGenerating(true);
      setCaptionTimerSeconds(90); // Reset to 1:30
      
      // Start countdown timer
      captionTimerRef.current = setInterval(() => {
        setCaptionTimerSeconds((prev) => {
          if (prev <= 1) {
            if (captionTimerRef.current) {
              clearInterval(captionTimerRef.current);
            }
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }

    // Add user message to chat
    setChatHistory((prev) => [
      ...prev,
      {
        role: "user",
        content: action,
        timestamp: new Date().toISOString(),
      },
    ]);

    // Show AI thinking state
    setIsAiThinking(true);
    setChatHistory((prev) => [
      ...prev,
      {
        role: "assistant",
        content: "🤔 Processing your request...",
        timestamp: new Date().toISOString(),
        isThinking: true,
      },
    ]);

    try {
      // Call the chat API with the quick action
      const response = await axios.post("/api/v1/chat", {
        message: action,
        clips: clips,
        selected_clip_index: selectedClipIndex,
      });

      const { clips: updatedClips, response: aiResponse, success } = response.data;

      // Remove thinking message
      setChatHistory((prev) => prev.filter((msg) => !msg.isThinking));

      // Show AI's response
      setChatHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          content: aiResponse || "Done!",
          timestamp: new Date().toISOString(),
        },
      ]);

      // Update clips if they changed
      if (success && updatedClips) {
        // Map updatedClips to proper format with URLs
        const formattedClips = updatedClips.map((clip, idx) => ({
          id: clip.id || idx + 1,
          title: clip.title || `Highlight ${idx + 1}`,
          startTime: clip.startTime || clip.start_time || "0:00",
          endTime: clip.endTime || clip.end_time || "0:30",
          duration: clip.duration || 30,
          filename: clip.filename,
          url: clip.download_url || clip.url || `/api/v1/download/${clip.filename}`,
          has_captions: clip.has_captions || clip.hasCaptions || false,
        }));
        
        setClips(formattedClips);
        
        // If captions were added, stop the timer
        if (isCaptionAction && formattedClips[selectedClipIndex]?.has_captions) {
          if (captionTimerRef.current) {
            clearInterval(captionTimerRef.current);
          }
          setIsCaptionGenerating(false);
        }
        
        // Force video reload for the current clip
        if (videoRef.current && formattedClips[selectedClipIndex]) {
          const newClip = formattedClips[selectedClipIndex];
          // Force reload by appending timestamp to bypass cache
          const videoUrl = `${newClip.url}?t=${Date.now()}`;
          videoRef.current.src = videoUrl;
          videoRef.current.load();
        }
      }
    } catch (error) {
      // Remove thinking message
      setChatHistory((prev) => prev.filter((msg) => !msg.isThinking));

      setChatHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `❌ Sorry, I encountered an error: ${error.response?.data?.detail || error.message}. Please try again.`,
          timestamp: new Date().toISOString(),
        },
      ]);
      console.error("Quick action error:", error);
      
      // Stop timer on error
      if (isCaptionAction) {
        if (captionTimerRef.current) {
          clearInterval(captionTimerRef.current);
        }
        setIsCaptionGenerating(false);
      }
    } finally {
      setIsAiThinking(false);
    }
  };

  const moveClip = (direction) => {
    const newIndex = selectedClipIndex + direction;
    if (newIndex >= 0 && newIndex < clips.length) {
      const newClips = [...clips];
      [newClips[selectedClipIndex], newClips[newIndex]] = [
        newClips[newIndex],
        newClips[selectedClipIndex],
      ];
      setClips(newClips);
      setSelectedClipIndex(newIndex);
    }
  };

  const addClip = () => {
    const newClip = {
      id: clips.length + 1,
      title: `New Clip ${clips.length + 1}`,
      startTime: "00:00:00",
      endTime: "00:00:30",
      duration: 30,
    };
    setClips([...clips, newClip]);
    setSelectedClipIndex(clips.length);
  };

  const handleExport = async () => {
    if (clips.length === 0) return;

    try {
      const clip = clips[selectedClipIndex];

      // Show notification
      setChatHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "📥 Downloading video...",
          timestamp: new Date().toISOString(),
        },
      ]);

      // Get the video URL - use download_url if available, otherwise construct it
      const videoUrl = clip.download_url || `/api/v1/download/${clip.filename}`;

      // Fetch the video file
      const response = await axios.get(videoUrl, {
        responseType: "blob",
        onDownloadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percentCompleted = Math.round(
              (progressEvent.loaded * 100) / progressEvent.total,
            );
            setProcessingStatus(`Downloading... ${percentCompleted}%`);
          }
        },
      });

      // Create blob URL and trigger download
      const blob = new Blob([response.data], { type: "video/mp4" });
      const url = globalThis.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download =
        clip.filename || `short_${clip.title || selectedClipIndex + 1}.mp4`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      globalThis.URL.revokeObjectURL(url);

      // Success notification
      setChatHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `✅ Video "${clip.title}" downloaded successfully!`,
          timestamp: new Date().toISOString(),
        },
      ]);
    } catch (error) {
      setChatHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "❌ Failed to download video. Please try again.",
          timestamp: new Date().toISOString(),
        },
      ]);
      console.error("Download error:", error);
    }
  };

  const handlePublish = () => {
    if (clips.length === 0) return;

    // Open publish modal instead of directly navigating
    setShowPublishModal(true);
  };

  const handlePlatformToggle = (platform) => {
    if (selectedPlatforms.includes(platform)) {
      setSelectedPlatforms(selectedPlatforms.filter((p) => p !== platform));
    } else {
      setSelectedPlatforms([...selectedPlatforms, platform]);
    }
  };

  const handlePublishConfirm = async () => {
    if (selectedPlatforms.length === 0) {
      setChatHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "⚠️ Please select at least one platform to publish.",
          timestamp: new Date().toISOString(),
        },
      ]);
      return;
    }

    if (!selectedClip?.short_id) {
      setChatHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "⚠️ Cannot publish: Missing video ID. Please regenerate the clip.",
          timestamp: new Date().toISOString(),
        },
      ]);
      return;
    }

    setShowPublishModal(false);

    // Show publishing notification
    setChatHistory((prev) => [
      ...prev,
      {
        role: "assistant",
        content: `🚀 Publishing to ${selectedPlatforms.join(", ")}...`,
        timestamp: new Date().toISOString(),
      },
    ]);

    try {
      // Map frontend platform names to backend platform names
      const platformMap = {
        youtube: "youtube_shorts",
        instagram: "instagram",
        tiktok: "tiktok",
        facebook: "facebook",
      };
      
      const mappedPlatforms = selectedPlatforms.map(
        (platform) => platformMap[platform] || platform
      );

      // Call actual publishing API
      const response = await axios.post("/api/v1/share", {
        short_id: selectedClip.short_id,
        platforms: mappedPlatforms,
        text: publishSettings.description || publishSettings.title || "",
      });

      // Show success with publication details
      const publicationCount = response.data.publications?.length || 0;
      setChatHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `✅ Publishing started! ${publicationCount} publication(s) queued. Check dashboard for status.`,
          timestamp: new Date().toISOString(),
        },
      ]);

      // Redirect to dashboard after a short delay
      setTimeout(() => {
        navigate("/dashboard");
      }, 2000);
    } catch (error) {
      console.error("Publishing error:", error);
      setChatHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `❌ Publishing failed: ${error.response?.data?.detail || error.message || "Unknown error"}. Please try again.`,
          timestamp: new Date().toISOString(),
        },
      ]);
    }
  };

  // Caption generation functions
  const generateCaptions = async () => {
    if (!selectedClip) return;

    // Add loading message to chat
    const loadingMessageId = Date.now();
    setChatHistory((prev) => [
      ...prev,
      {
        role: "assistant",
        content: "🎤 Generating captions from audio... This may take a minute.",
        timestamp: new Date().toISOString(),
        isLoading: true,
        id: loadingMessageId,
      },
    ]);

    try {
      // Start caption generation
      const response = await axios.post(
        `/api/v1/clips/${selectedClip.id}/generate-captions`,
      );

      const jobId = response.data.job_id;

      // Poll for completion
      pollCaptionJob(jobId, loadingMessageId);
    } catch (error) {
      console.error("Caption generation failed:", error);
      
      // Remove loading message and add error
      setChatHistory((prev) => 
        prev.filter(msg => msg.id !== loadingMessageId).concat({
          role: "assistant",
          content: `❌ Failed to generate captions: ${error.message}`,
          timestamp: new Date().toISOString(),
        })
      );
    }
  };

  const pollCaptionJob = (jobId, loadingMessageId) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await axios.get(`/api/v1/job/${jobId}`);
        const { status, progress } = response.data;

        // Update loading message with progress
        setChatHistory((prev) => 
          prev.map(msg => 
            msg.id === loadingMessageId 
              ? { ...msg, content: `🎤 Generating captions... ${Math.round(progress || 0)}%` }
              : msg
          )
        );

        if (status === "completed") {
          clearInterval(pollInterval);

          // Fetch captions
          const captionsResponse = await axios.get(
            `/api/v1/clips/${selectedClip.id}/captions`,
          );

          setCaptions(captionsResponse.data.captions);
          setShowCaptionPreview(true);

          // Remove loading message and add success message
          setChatHistory((prev) => 
            prev.filter(msg => msg.id !== loadingMessageId).concat({
              role: "assistant",
              content: "✅ Captions generated! Choose a style and preview below.",
              timestamp: new Date().toISOString(),
            })
          );
        } else if (status === "failed") {
          clearInterval(pollInterval);
          
          // Remove loading message and add error
          setChatHistory((prev) => 
            prev.filter(msg => msg.id !== loadingMessageId).concat({
              role: "assistant",
              content: "❌ Caption generation failed. Please try again.",
              timestamp: new Date().toISOString(),
            })
          );
        }
      } catch (error) {
        clearInterval(pollInterval);
        console.error("Caption poll error:", error);
        
        // Remove loading message and add error
        setChatHistory((prev) => 
          prev.filter(msg => msg.id !== loadingMessageId).concat({
            role: "assistant",
            content: "❌ Error checking caption status. Please try again.",
            timestamp: new Date().toISOString(),
          })
        );
      }
    }, 2000);
  };

  const applyCaptionStyle = async (styleName) => {
    if (!captions) {
      setChatHistory((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "⚠️ Please generate captions first.",
          timestamp: new Date().toISOString(),
        },
      ]);
      return;
    }

    // Add loading message to chat
    const loadingMessageId = Date.now();
    setChatHistory((prev) => [
      ...prev,
      {
        role: "assistant",
        content: `🎨 Applying ${CAPTION_STYLES[styleName].name} style to video...`,
        timestamp: new Date().toISOString(),
        isLoading: true,
        id: loadingMessageId,
      },
    ]);

    setIsProcessing(true);
    setProcessingStatus("Applying caption style...");

    try {
      const response = await axios.post(
        `/api/v1/clips/${selectedClip.id}/apply-captions`,
        null,
        { params: { style_name: styleName } },
      );

      const jobId = response.data.job_id;

      // Poll for completion
      pollCaptionBurnJob(jobId, loadingMessageId, styleName);
    } catch (error) {
      console.error("Apply captions failed:", error);
      setIsProcessing(false);
      
      // Remove loading message and add error
      setChatHistory((prev) => 
        prev.filter(msg => msg.id !== loadingMessageId).concat({
          role: "assistant",
          content: `❌ Failed to apply captions: ${error.message}`,
          timestamp: new Date().toISOString(),
        })
      );
    }
  };

  const pollCaptionBurnJob = (jobId, loadingMessageId, styleName) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await axios.get(`/api/v1/job/${jobId}`);
        const { status, progress, result } = response.data;

        // Update loading message with progress
        setChatHistory((prev) => 
          prev.map(msg => 
            msg.id === loadingMessageId 
              ? { ...msg, content: `🎨 Applying ${CAPTION_STYLES[styleName].name} style... ${Math.round(progress || 0)}%` }
              : msg
          )
        );

        setProcessingStatus(`Burning captions into video... ${Math.round(progress || 0)}%`);
        setProcessingProgress(progress || 0);

        if (status === "completed") {
          clearInterval(pollInterval);

          console.log("Caption burn completed, full result:", JSON.stringify(result, null, 2));

          // Update clip with new captioned video URL
          const updatedClips = [...clips];
          // Try multiple possible field names from the API
          const newVideoUrl = result.new_file_path || result.file_path || result.url || result.output_path || selectedClip.url;
          // Add timestamp to force reload
          const urlWithTimestamp = `${newVideoUrl}?t=${Date.now()}`;
          
          console.log("Available result fields:", Object.keys(result));
          console.log("Selected new video URL:", newVideoUrl);
          console.log("Current clip URL:", selectedClip.url);
          
          updatedClips[selectedClipIndex] = {
            ...updatedClips[selectedClipIndex],
            url: urlWithTimestamp,
            hasCaptions: true,
            captionStyle: styleName,
          };
          
          console.log("Updating clip URL from:", selectedClip.url);
          console.log("Updating clip URL to:", urlWithTimestamp);
          console.log("Updated clip object:", updatedClips[selectedClipIndex]);
          setClips(updatedClips);

          // Force video reload by resetting the video element
          setTimeout(() => {
            if (videoRef.current) {
              console.log("Force reloading video with new URL");
              videoRef.current.load();
              videoRef.current.currentTime = 0;
            }
          }, 100);

          // Remove loading message and add success message
          setChatHistory((prev) => 
            prev.filter(msg => msg.id !== loadingMessageId).concat({
              role: "assistant",
              content: "✅ Captions applied successfully! The video has been updated with captions.",
              timestamp: new Date().toISOString(),
            })
          );

          // Stop the caption timer if it's running
          if (captionTimerRef.current) {
            clearInterval(captionTimerRef.current);
          }
          setIsCaptionGenerating(false);

          setIsProcessing(false);
          setProcessingProgress(0);
        } else if (status === "failed") {
          clearInterval(pollInterval);
          setIsProcessing(false);
          setProcessingProgress(0);
          
          // Stop the caption timer on failure
          if (captionTimerRef.current) {
            clearInterval(captionTimerRef.current);
          }
          setIsCaptionGenerating(false);
          
          // Remove loading message and add error
          setChatHistory((prev) => 
            prev.filter(msg => msg.id !== loadingMessageId).concat({
              role: "assistant",
              content: "❌ Failed to apply captions to video. Please try again.",
              timestamp: new Date().toISOString(),
            })
          );
        }
      } catch (error) {
        clearInterval(pollInterval);
        setIsProcessing(false);
        setProcessingProgress(0);
        console.error("Caption burn poll error:", error);
        
        // Stop the caption timer on error
        if (captionTimerRef.current) {
          clearInterval(captionTimerRef.current);
        }
        setIsCaptionGenerating(false);
        
        // Remove loading message and add error
        setChatHistory((prev) => 
          prev.filter(msg => msg.id !== loadingMessageId).concat({
            role: "assistant",
            content: "❌ Error checking caption application status. Please try again.",
            timestamp: new Date().toISOString(),
          })
        );
      }
    }, 2000);
  };

  // Update current caption word based on video time (for preview)
  useEffect(() => {
    if (!captions || !showCaptionPreview || !captions.words) return;

    const updateCaption = () => {
      const time = videoRef.current?.currentTime || 0;

      // Find all words within a time window for scrolling effect
      const timeWindow = 3; // Show words within 3 seconds
      const currentWords = captions.words.filter(
        word => time >= word.start - 1 && time <= word.end + timeWindow
      );
      
      // Find the current active word
      const activeWordIndex = currentWords.findIndex(
        word => time >= word.start && time <= word.end
      );
      
      if (activeWordIndex >= 0) {
        // Show current word and next word (2 lines visible)
        setCurrentCaption(currentWords[activeWordIndex].word);
      } else {
        setCurrentCaption("");
      }
    };

    const interval = setInterval(updateCaption, 100);
    return () => clearInterval(interval);
  }, [captions, showCaptionPreview]);

  // Force video reload when URL changes (especially for captioned videos)
  useEffect(() => {
    if (selectedClip?.url && videoRef.current) {
      console.log("Video URL changed to:", selectedClip.url);
      // Pause current playback
      setIsPlaying(false);
      // Force reload
      videoRef.current.load();
    }
  }, [selectedClip?.url]);

  // Auto-scroll chat to bottom when new messages arrive
  useEffect(() => {
    if (chatScrollRef.current) {
      // Use setTimeout to ensure DOM has updated
      setTimeout(() => {
        const scrollContainer = chatScrollRef.current?.querySelector('[data-radix-scroll-area-viewport]');
        if (scrollContainer) {
          scrollContainer.scrollTo({
            top: scrollContainer.scrollHeight,
            behavior: 'smooth'
          });
        }
      }, 100);
    }
  }, [chatHistory]);

  // Cleanup caption timer on unmount
  useEffect(() => {
    return () => {
      if (captionTimerRef.current) {
        clearInterval(captionTimerRef.current);
      }
    };
  }, []);

  // Watch for caption completion and stop timer
  useEffect(() => {
    if (isCaptionGenerating && selectedClip?.has_captions) {
      // Caption video is ready, stop the timer
      if (captionTimerRef.current) {
        clearInterval(captionTimerRef.current);
      }
      // Don't close immediately, keep showing "Ready!" state
      setCaptionTimerSeconds(0);
      
      // Auto-hide the timer after 3 seconds
      setTimeout(() => {
        setIsCaptionGenerating(false);
      }, 3000);
    }
  }, [isCaptionGenerating, selectedClip?.has_captions]);

  return (
    <div className="h-screen bg-white flex overflow-hidden">
        {/* Left Panel - Assistant Chat */}
        {isLeftPanelVisible && (
          <aside
          className="h-full border-r border-gray-200 bg-white flex flex-col overflow-hidden relative"
            style={{
              width: `${chatPanelWidth}px`,
              minWidth: "280px",
              maxWidth: "600px",
            }}
          >
            {/* Resize Handle */}
            <div
              className="absolute right-0 top-0 bottom-0 w-2 cursor-col-resize hover:bg-gray-100 z-10 flex items-center justify-center"
              onMouseDown={handleResizeStart}
              role="separator"
              aria-orientation="vertical"
              aria-label="Resize chat panel"
            >
              <GripVertical className="h-4 w-4 text-gray-400 pointer-events-none" />
            </div>

          {/* Header with Back Button and Expand Icon */}
          <div className="border-b border-gray-200 px-3 flex items-center justify-between bg-gray-50">
            <Button variant="ghost" size="icon" onClick={() => navigate("/")}>
              <ArrowLeft className="h-4 w-4" />
            </Button>
              <Button variant="ghost" size="icon" onClick={toggleChatExpand}>
                {isChatExpanded ? (
                  <Minimize className="h-4 w-4" />
                ) : (
                  <Maximize className="h-4 w-4" />
                )}
              </Button>
            </div>

            <div className="border-b border-gray-200 p-4 bg-white">
              <p className="text-xs font-semibold text-gray-500 uppercase mb-3">
                Suggestions
              </p>
              <div className="flex flex-wrap gap-2">
                <Badge
                  variant="outline"
                  className="cursor-pointer hover:bg-gray-100"
                  onClick={() => handleQuickAction("Use example video")}
                >
                  <Video className="h-3 w-3 mr-1" />
                  Use example video
                </Badge>
                <Badge
                  variant="outline"
                  className="cursor-pointer hover:bg-gray-100"
                  onClick={() => handleQuickAction("Add live captions")}
                >
                  <Type className="h-3 w-3 mr-1" />
                  Add live captions
                </Badge>
                <Badge
                  variant="outline"
                  className="cursor-pointer hover:bg-gray-100"
                  onClick={() => handleQuickAction("Dub in Kannada")}
                >
                  <Volume2 className="h-3 w-3 mr-1" />
                  Dub in Kannada
                </Badge>
                <Badge
                  variant="outline"
                  className="cursor-pointer hover:bg-gray-100"
                  onClick={() => handleQuickAction("Summarize scenes")}
                >
                  <Wand2 className="h-3 w-3 mr-1" />
                  Summarize scenes
                </Badge>
                <Badge
                  variant="outline"
                  className="cursor-pointer hover:bg-gray-100"
                  onClick={() => handleQuickAction("Change video URL")}
                >
                  <ArrowLeft className="h-3 w-3 mr-1" />
                  Change video URL
                </Badge>
              </div>
            </div>

            {/* Caption Generation Timer */}
            {isCaptionGenerating && (
              <div className="border-b border-gray-200 px-4 py-3 bg-gradient-to-r from-purple-50 to-pink-50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {captionTimerSeconds > 0 ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin text-purple-600" />
                        <span className="text-sm font-medium text-gray-700">
                          Generating captions...
                        </span>
                      </>
                    ) : (
                      <>
                        <div className="h-5 w-5 rounded-full bg-green-500 flex items-center justify-center shadow-sm">
                          <svg className="h-3 w-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                          </svg>
                        </div>
                        <span className="text-sm font-semibold text-green-700">
                          Ready!
                        </span>
                      </>
                    )}
                  </div>
                  <div className={cn(
                    "flex items-center gap-2 text-sm font-mono font-semibold px-3 py-1.5 rounded-md shadow-sm transition-all",
                    captionTimerSeconds > 0 
                      ? "bg-purple-100 text-purple-700 border border-purple-200" 
                      : "bg-green-100 text-green-700 border border-green-200"
                  )}>
                    {captionTimerSeconds > 0 && (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    )}
                    <span>
                      {captionTimerSeconds > 0 
                        ? `≈ ${Math.floor(captionTimerSeconds / 60)}:${String(captionTimerSeconds % 60).padStart(2, '0')}`
                        : "✓ 0:00"
                      }
                    </span>
                  </div>
                </div>
              </div>
            )}

            <ScrollArea ref={chatScrollRef} className="flex-1 p-4">
              <div className="space-y-4">
                {chatHistory.map((msg, idx) => (
                  <div
                    key={`msg-${idx}-${msg.content.substring(0, 20)}`}
                    className="flex gap-3"
                  >
                    <div
                      className={cn(
                        "w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0",
                        msg.role === "assistant"
                          ? "bg-[#1E201E] text-white"
                          : "bg-gray-200 text-gray-700",
                      )}
                    >
                      {msg.role === "assistant" ? (
                        <Sparkles className="h-4 w-4" />
                      ) : (
                        <span className="text-xs font-semibold">You</span>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-semibold text-gray-900">
                          {msg.role === "assistant" ? "Copilot" : "You"}
                        </span>
                        <span className="text-xs text-gray-500">
                          {new Date(msg.timestamp).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                      </div>
                      <div
                        className={cn(
                          "text-sm text-gray-700 leading-relaxed",
                          msg.isThinking &&
                            "animate-pulse text-gray-500 italic",
                          msg.isExecuting && "text-blue-600 font-medium",
                          msg.isLoading && "flex items-center gap-2",
                        )}
                      >
                        {msg.isLoading && (
                          <Loader2 className="h-4 w-4 animate-spin text-purple-600" />
                        )}
                        {msg.content}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>

            <form
              className="border-t border-gray-200 p-4 bg-gray-50"
              onSubmit={handleSendMessage}
            >
              <div className="flex items-center gap-2 bg-white border border-gray-300 rounded-lg px-3 focus-within:ring-2 focus-within:ring-[#1E201E] focus-within:border-[#1E201E]">
                <Input
                  type="text"
                  placeholder={
                    isAiThinking
                      ? "AI is processing..."
                      : "Ask Copilot to edit your video..."
                  }
                  value={chatMessage}
                  onChange={(e) => setChatMessage(e.target.value)}
                  disabled={isAiThinking}
                  className="border-0 focus-visible:ring-0 focus-visible:ring-offset-0"
                />
                <Button
                  type="submit"
                  size="icon"
                  variant="ghost"
                  disabled={isAiThinking || !chatMessage.trim()}
                  aria-label="Send message"
                >
                  {isAiThinking ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                </Button>
              </div>
              <p className="text-xs text-gray-500 mt-2 text-center">
                💡 Try: "Trim clip to 20s" or "Change title to Marketing Tips"
              </p>
            </form>
          </aside>
        )}

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden relative">
        {/* Top Bar with Export and Publish buttons - Fixed position */}
        <div className="fixed top-0 right-0 z-50 bg-white border-b border-l border-gray-200 px-4 py-2 flex items-center gap-2 shadow-sm">
          <Button
            variant="outline"
            size="sm"
            onClick={handleExport}
            disabled={isProcessing || clips.length === 0}
          >
            <Download className="h-4 w-4" />
            Export
          </Button>
          <Button
            className="bg-[#1E201E] hover:bg-[#1E201E]/90 text-white"
            size="sm"
            onClick={handlePublish}
            disabled={isProcessing || clips.length === 0}
          >
            <Share2 className="h-4 w-4" />
            Publish
          </Button>
        </div>
        <div
          className="flex-1 grid overflow-hidden transition-all duration-300"
          style={{
            gridTemplateColumns: isRightPanelVisible ? "1fr 350px" : "1fr",
          }}
        >
        {/* Center Panel - Video Preview (Fixed Size) */}
        <main className="flex flex-col bg-white p-6 overflow-hidden">
          <div className="flex-1 flex items-center justify-center min-h-0">
            <div className="relative w-[640px] aspect-video bg-black rounded-3xl overflow-hidden shadow-2xl" style={{ transform: 'translateY(-2%)' }}>
              {isProcessing ? (
                // New shimmer loading animation
                <div className="relative w-full h-full rounded-3xl overflow-hidden">
                  {thumbnailUrl && (
                    <img
                      src={thumbnailUrl}
                      alt="Video thumbnail"
                      className="w-full h-full object-cover blur-2xl brightness-50 opacity-50 rounded-3xl"
                    />
                  )}
                  <div className="absolute inset-0 flex items-center justify-center bg-black/30 backdrop-blur-md rounded-3xl">
                    <div className="relative px-8">
                      {/* Shimmer effect text */}
                      <div className="relative">
                        <h2 className="text-7xl font-bold text-white/25 select-none">
                          {loadingSteps[currentLoadingStep]?.text || "Processing..."}
                        </h2>
                        {/* Shimmer overlay that sweeps left to right */}
                        <div className="absolute inset-0 overflow-hidden">
                          <div className="animate-shimmer absolute inset-0"></div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <>
                  {clips.length > 0 && selectedClip?.url ? (
                    // Show video player with fixed dimensions
                    <div className="relative w-full h-full bg-black rounded-3xl overflow-hidden">
                      <video
                        ref={videoRef}
                        className="w-full h-full object-cover rounded-3xl"
                        onTimeUpdate={handleTimeUpdate}
                        onLoadedMetadata={handleLoadedMetadata}
                        onError={(e) => {
                          console.error("Video load error:", e);
                          console.error("Video URL:", selectedClip.url);
                          console.error(
                            "Video element error details:",
                            videoRef.current?.error,
                          );
                          setError(
                            `Failed to load video: ${videoRef.current?.error?.message || "Unknown error"}`,
                          );
                        }}
                        onCanPlay={() => {
                          console.log("Video can play, URL:", selectedClip.url);
                          setError("");
                        }}
                        onEnded={() => setIsPlaying(false)}
                        src={selectedClip.url}
                        key={selectedClip.url}
                        controls={false}
                        preload="metadata"
                      >
                        <track kind="captions" srcLang="en" label="English" />
                      </video>

                      <div className="absolute top-5 left-5 px-3 py-1.5 bg-black/60 backdrop-blur-md text-white rounded-xl text-sm font-semibold border border-white/20">
                        Clip #{selectedClipIndex + 1}
                      </div>

                      {/* Live Caption Preview Overlay */}
                      {showCaptionPreview && currentCaption && (
                        <div
                          className={`caption-overlay caption-style-${selectedCaptionStyle}`}
                        >
                          {currentCaption}
                        </div>
                      )}

                      {/* Video Controls */}
                      <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/80 via-black/40 to-transparent backdrop-blur-sm opacity-0 hover:opacity-100 transition-opacity rounded-b-3xl">
                        <div
                          className="w-full h-1.5 bg-white/20 rounded-full cursor-pointer mb-3 hover:h-2 transition-all relative group"
                          onClick={handleProgressClick}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              handleProgressClick(e);
                            }
                          }}
                          role="progressbar"
                          aria-label="Video progress"
                          aria-valuenow={currentTime}
                          aria-valuemin={0}
                          aria-valuemax={duration}
                          tabIndex={0}
                        >
                          <div
                            className="h-full bg-gradient-to-r from-[#1E201E] via-purple-600 to-pink-500 rounded-full transition-all shadow-lg shadow-[#1E201E]/50 relative"
                            style={{
                              width: `${duration > 0 ? (currentTime / duration) * 100 : 0}%`,
                            }}
                          >
                            {/* Progress Pin/Thumb */}
                            <div className="absolute -right-2 top-1/2 -translate-y-1/2 w-4 h-4 bg-white rounded-full shadow-lg border-2 border-purple-500 opacity-0 group-hover:opacity-100 transition-opacity cursor-grab active:cursor-grabbing"></div>
                          </div>
                        </div>

                        <div className="flex items-center gap-3 text-white">
                          <Button
                            size="icon"
                            className="h-11 w-11 bg-[#1E201E] hover:bg-[#1E201E]/90 text-white rounded-full"
                            onClick={handlePlayPause}
                            aria-label={isPlaying ? "Pause" : "Play"}
                          >
                            {isPlaying ? (
                              <Pause className="h-5 w-5" />
                            ) : (
                              <Play className="h-5 w-5" />
                            )}
                          </Button>

                          <Button
                            size="icon"
                            variant="ghost"
                            className="h-11 w-11 bg-white/10 hover:bg-white/20 text-white rounded-full border border-white/20"
                            onClick={toggleMute}
                            aria-label={isMuted ? "Unmute" : "Mute"}
                          >
                            {isMuted ? (
                              <Volume2 className="h-5 w-5 opacity-50" />
                            ) : (
                              <Volume2 className="h-5 w-5" />
                            )}
                          </Button>

                          <div className="flex items-center gap-2">
                            <div
                              className="w-20 h-1.5 bg-white/20 rounded-full cursor-pointer hover:h-2 transition-all"
                              onClick={handleVolumeChange}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter' || e.key === ' ') {
                                  e.preventDefault();
                                  handleVolumeChange(e);
                                }
                              }}
                              role="slider"
                              aria-label="Volume"
                              aria-valuenow={isMuted ? 0 : Math.round(volume * 100)}
                              aria-valuemin={0}
                              aria-valuemax={100}
                              tabIndex={0}
                            >
                              <div
                                className="h-full bg-white rounded-full transition-all"
                                style={{
                                  width: `${(isMuted ? 0 : volume) * 100}%`,
                                }}
                              />
                            </div>
                          </div>

                          <span className="text-sm font-medium ml-auto text-shadow">
                            {formatTimeDisplay(currentTime)} /{" "}
                            {formatTimeDisplay(duration)}
                          </span>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center justify-center p-8 text-gray-500 bg-gray-50 rounded-3xl">
                      <p>{error || "No video available"}</p>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </main>

        {/* Right Panel - Timeline */}
        {isRightPanelVisible && (
          <aside className="flex flex-col bg-white border-l border-gray-200 overflow-hidden">
            {/* Timeline Section */}
            <div className="border-t border-gray-200 bg-gray-50 p-4 flex flex-col pt-16 space-y-4">
              <h4 className="text-sm font-semibold text-gray-900">Timeline</h4>
              
              {/* Add Clip Button */}
              <Button
                size="sm"
                variant="outline"
                onClick={addClip}
                disabled={isProcessing}
                className="w-full justify-start"
              >
                <Plus className="h-4 w-4 mr-2" />
                Add Clip
              </Button>
              
              {/* Move Up Button */}
              <Button
                size="sm"
                variant="outline"
                onClick={() => moveClip(-1)}
                disabled={selectedClipIndex === 0 || isProcessing}
                className="w-full justify-start"
              >
                <ChevronUp className="h-4 w-4 mr-2" />
                Move Up
              </Button>
              
              {/* Move Down Button */}
              <Button
                size="sm"
                variant="outline"
                onClick={() => moveClip(1)}
                disabled={
                  selectedClipIndex === clips.length - 1 || isProcessing
                }
                className="w-full justify-start"
              >
                <ChevronDown className="h-4 w-4 mr-2" />
                Move Down
              </Button>

              {/* Time Ruler */}
              {!isProcessing && clips.length > 0 && selectedClip && (
                <div className="relative h-10 bg-gray-200 rounded-lg overflow-hidden">
                  <div className="flex h-full relative">
                    {Array.from(
                      { length: Math.ceil(selectedClip.duration / 5) + 1 },
                      (_, i) => (
                        <div
                          key={i}
                          className="flex-1 flex flex-col items-start justify-start p-1"
                        >
                          <div className="w-0.5 h-2 bg-gray-400 mb-1"></div>
                          <span className="text-xs text-gray-600">{i * 5}s</span>
                        </div>
                      ),
                    )}
                  </div>
                  <div
                    className="absolute top-0 bottom-0 w-0.5 bg-[#1E201E] z-10 transition-all"
                    style={{
                      left: `${(currentTime / selectedClip.duration) * 100}%`,
                    }}
                  >
                    <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-3 h-3 bg-[#1E201E] rounded-full border-2 border-white shadow-lg"></div>
                  </div>
                </div>
              )}
            </div>
          </aside>
        )}
            </div>
      </div>

      {/* Publish Modal */}
      <Dialog open={showPublishModal} onOpenChange={setShowPublishModal}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Publish Your Short</DialogTitle>
            <DialogDescription>
              Choose platforms and configure your video settings
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-6 py-4">
            {/* Platform Selection */}
            <div>
              <h3 className="text-base font-semibold text-gray-900 mb-2">
                Select Platforms
              </h3>
              <p className="text-sm text-gray-600 mb-4">
                Choose where you want to publish your video
              </p>
              <div className="grid grid-cols-2 gap-3">
                <Card
                  className={cn(
                    "cursor-pointer transition-all",
                    selectedPlatforms.includes("youtube")
                      ? "border-[#1E201E] border-2 bg-[#1E201E]/5"
                      : "border-gray-200 hover:border-gray-300",
                  )}
                  onClick={() => handlePlatformToggle("youtube")}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 bg-red-600 rounded-lg flex items-center justify-center">
                        <Play className="h-6 w-6 text-white" />
                      </div>
                      <div className="flex-1">
                        <h4 className="text-sm font-semibold text-gray-900">
                          YouTube Shorts
                        </h4>
                        <p className="text-xs text-gray-500">9:16 • 60s max</p>
                      </div>
                      {selectedPlatforms.includes("youtube") && (
                        <div className="w-6 h-6 bg-[#1E201E] rounded-full flex items-center justify-center text-white text-xs font-bold">
                          ✓
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>

                <Card
                  className={cn(
                    "cursor-pointer transition-all",
                    selectedPlatforms.includes("instagram")
                      ? "border-[#1E201E] border-2 bg-[#1E201E]/5"
                      : "border-gray-200 hover:border-gray-300",
                  )}
                  onClick={() => handlePlatformToggle("instagram")}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 bg-gradient-to-r from-purple-600 via-pink-600 to-orange-500 rounded-lg flex items-center justify-center">
                        <Video className="h-6 w-6 text-white" />
                      </div>
                      <div className="flex-1">
                        <h4 className="text-sm font-semibold text-gray-900">
                          Instagram Reels
                        </h4>
                        <p className="text-xs text-gray-500">9:16 • 90s max</p>
                      </div>
                      {selectedPlatforms.includes("instagram") && (
                        <div className="w-6 h-6 bg-[#1E201E] rounded-full flex items-center justify-center text-white text-xs font-bold">
                          ✓
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>

                <Card
                  className={cn(
                    "cursor-pointer transition-all",
                    selectedPlatforms.includes("tiktok")
                      ? "border-[#1E201E] border-2 bg-[#1E201E]/5"
                      : "border-gray-200 hover:border-gray-300",
                  )}
                  onClick={() => handlePlatformToggle("tiktok")}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 bg-black rounded-lg flex items-center justify-center">
                        <Play className="h-6 w-6 text-white" />
                      </div>
                      <div className="flex-1">
                        <h4 className="text-sm font-semibold text-gray-900">
                          TikTok
                        </h4>
                        <p className="text-xs text-gray-500">9:16 • 10m max</p>
                      </div>
                      {selectedPlatforms.includes("tiktok") && (
                        <div className="w-6 h-6 bg-[#1E201E] rounded-full flex items-center justify-center text-white text-xs font-bold">
                          ✓
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>

                <Card
                  className={cn(
                    "cursor-pointer transition-all",
                    selectedPlatforms.includes("facebook")
                      ? "border-[#1E201E] border-2 bg-[#1E201E]/5"
                      : "border-gray-200 hover:border-gray-300",
                  )}
                  onClick={() => handlePlatformToggle("facebook")}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center">
                        <Video className="h-6 w-6 text-white" />
                      </div>
                      <div className="flex-1">
                        <h4 className="text-sm font-semibold text-gray-900">
                          Facebook Reels
                        </h4>
                        <p className="text-xs text-gray-500">9:16 • 90s max</p>
                      </div>
                      {selectedPlatforms.includes("facebook") && (
                        <div className="w-6 h-6 bg-[#1E201E] rounded-full flex items-center justify-center text-white text-xs font-bold">
                          ✓
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>

            <Separator />

            {/* Video Settings */}
            <div>
              <h3 className="text-base font-semibold text-gray-900 mb-4">
                Video Settings
              </h3>
              <div className="space-y-4">
                <div>
                  <label
                    htmlFor="video-title"
                    className="text-sm font-medium text-gray-700 mb-2 block"
                  >
                    Title
                  </label>
                  <Input
                    id="video-title"
                    type="text"
                    placeholder="Enter video title..."
                    value={publishSettings.title}
                    onChange={(e) =>
                      setPublishSettings({
                        ...publishSettings,
                        title: e.target.value,
                      })
                    }
                  />
                </div>

                <div>
                  <label
                    htmlFor="video-description"
                    className="text-sm font-medium text-gray-700 mb-2 block"
                  >
                    Description
                  </label>
                  <textarea
                    id="video-description"
                    placeholder="Add a description..."
                    value={publishSettings.description}
                    onChange={(e) =>
                      setPublishSettings({
                        ...publishSettings,
                        description: e.target.value,
                      })
                    }
                    className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                    rows="3"
                  />
                </div>

                <div>
                  <label
                    htmlFor="video-tags"
                    className="text-sm font-medium text-gray-700 mb-2 block"
                  >
                    Tags (comma separated)
                  </label>
                  <Input
                    id="video-tags"
                    type="text"
                    placeholder="trending, viral, shorts..."
                    value={publishSettings.tags}
                    onChange={(e) =>
                      setPublishSettings({
                        ...publishSettings,
                        tags: e.target.value,
                      })
                    }
                  />
                </div>

                <div>
                  <label
                    htmlFor="aspect-ratio"
                    className="text-sm font-medium text-gray-700 mb-2 block"
                  >
                    Aspect Ratio
                  </label>
                  <select
                    id="aspect-ratio"
                    value={publishSettings.aspectRatio}
                    onChange={(e) =>
                      setPublishSettings({
                        ...publishSettings,
                        aspectRatio: e.target.value,
                      })
                    }
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  >
                    <option value="9:16">9:16 (Vertical - Recommended)</option>
                    <option value="1:1">1:1 (Square)</option>
                    <option value="16:9">16:9 (Horizontal)</option>
                    <option value="4:5">4:5 (Instagram Feed)</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowPublishModal(false)}
            >
              Cancel
            </Button>
            <Button
              className="bg-[#1E201E] hover:bg-[#1E201E]/90 text-white"
              onClick={handlePublishConfirm}
              disabled={selectedPlatforms.length === 0}
            >
              <Share2 className="h-4 w-4 mr-2" />
              {(() => {
                if (selectedPlatforms.length === 0) return "Publish to Platforms";
                const platformText = selectedPlatforms.length > 1 ? "Platforms" : "Platform";
                return `Publish to ${selectedPlatforms.length} ${platformText}`;
              })()}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default VideoEditor;
