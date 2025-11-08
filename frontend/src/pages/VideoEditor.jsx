import { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { 
  Play, Pause, Download, Share2, ArrowLeft,
  Send, Plus, ChevronUp, ChevronDown, SkipForward, SkipBackIcon,
  Loader2, Scissors, Type, Volume2, Wand2, Layers, Copy, Trash2, 
  ZoomIn, ZoomOut, RotateCw, Maximize2, Save, Sparkles, Video,
  GripVertical, Maximize, Minimize, ChevronLeft, ChevronRight, PanelLeft, PanelRight
} from 'lucide-react';
import axios from 'axios';
import { extractVideoId, getThumbnailUrl } from '../utils/youtube';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Slider } from '@/components/ui/slider';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { cn } from '@/lib/utils';

function VideoEditor() {
  const navigate = useNavigate();
  const location = useLocation();
  const videoRef = useRef(null);
  const hasProcessedRef = useRef(false); // Track if video has been processed to prevent double submission
  
  const youtubeUrl = location.state?.youtubeUrl;
  const videoId = extractVideoId(youtubeUrl);
  const thumbnailUrl = getThumbnailUrl(videoId);

  // Processing states
  const [isProcessing, setIsProcessing] = useState(true);
  const [processingStatus, setProcessingStatus] = useState('Analyzing video...');
  const [processingProgress, setProcessingProgress] = useState(0);
  const [error, setError] = useState('');
  
  // Loading animation states
  const [loadingSteps] = useState([
    { id: 1, text: 'Connecting to YouTube', completed: false },
    { id: 2, text: 'Extracting video transcript', completed: false },
    { id: 3, text: 'Analyzing content with AI', completed: false },
    { id: 4, text: 'Identifying key highlights', completed: false },
    { id: 5, text: 'Downloading video segments', completed: false },
    { id: 6, text: 'Applying smart cropping', completed: false },
    { id: 7, text: 'Generating short clips', completed: false },
    { id: 8, text: 'Finalizing your videos', completed: false }
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
    title: '',
    description: '',
    tags: '',
    aspectRatio: '9:16' // Default for shorts
  });
  
  // Chat states
  const [chatMessage, setChatMessage] = useState('');
  const [isAiThinking, setIsAiThinking] = useState(false);
  const [chatHistory, setChatHistory] = useState([
    { 
      role: 'assistant', 
      content: 'Hello! I\'m your AI video editor assistant. I can help you trim clips, adjust duration, add effects, and more. Just tell me what you want to do!',
      timestamp: new Date().toISOString()
    }
  ]);

  // Resizable chat panel states
  const [chatPanelWidth, setChatPanelWidth] = useState(320);
  const [isResizing, setIsResizing] = useState(false);
  const [isChatExpanded, setIsChatExpanded] = useState(false);

  // Caption states
  const [captions, setCaptions] = useState(null);
  const [selectedCaptionStyle, setSelectedCaptionStyle] = useState('bold_modern');
  const [showCaptionPreview, setShowCaptionPreview] = useState(false);
  const [isGeneratingCaptions, setIsGeneratingCaptions] = useState(false);
  const [currentCaption, setCurrentCaption] = useState('');

  // Available caption styles
  const CAPTION_STYLES = {
    bold_modern: {
      name: "Bold & Modern",
      preview: "💪 HELLO WORLD",
      description: "Bold text with strong contrast"
    },
    elegant_serif: {
      name: "Elegant Serif",
      preview: "✨ Hello World",
      description: "Sophisticated serif font"
    },
    fun_playful: {
      name: "Fun & Playful",
      preview: "🎉 HELLO WORLD!",
      description: "Colorful and energetic"
    }
  };

  // Panel visibility states (collapsible panels)
  const [isLeftPanelVisible, setIsLeftPanelVisible] = useState(true);
  const [isRightPanelVisible, setIsRightPanelVisible] = useState(true);
  
  // Load panel preferences from localStorage
  useEffect(() => {
    const savedLeftPanel = localStorage.getItem('editor-left-panel-visible');
    const savedRightPanel = localStorage.getItem('editor-right-panel-visible');
    if (savedLeftPanel !== null) setIsLeftPanelVisible(savedLeftPanel === 'true');
    if (savedRightPanel !== null) setIsRightPanelVisible(savedRightPanel === 'true');
  }, []);

  // Save panel preferences to localStorage
  useEffect(() => {
    localStorage.setItem('editor-left-panel-visible', String(isLeftPanelVisible));
  }, [isLeftPanelVisible]);

  useEffect(() => {
    localStorage.setItem('editor-right-panel-visible', String(isRightPanelVisible));
  }, [isRightPanelVisible]);

  // Clips data
  const [clips, setClips] = useState([]);
  const selectedClip = clips[selectedClipIndex];
  const [clipTitle, setClipTitle] = useState(selectedClip?.title || '');
  const [clipDuration, setClipDuration] = useState(selectedClip?.duration || 30);

  // Redirect if no YouTube URL
  useEffect(() => {
    if (!youtubeUrl) {
      navigate('/');
    }
  }, [youtubeUrl, navigate]);

  // Update loading step based on processing progress
  useEffect(() => {
    // Each step represents 12.5% of progress (100% / 8 steps)
    const stepIndex = Math.floor(processingProgress / 12.5);
    if (stepIndex !== currentLoadingStep && stepIndex <= 8) {
      setCurrentLoadingStep(stepIndex);
    }
  }, [processingProgress, currentLoadingStep]);

  // Process video function
  const processVideo = async () => {
    try {
      setProcessingStatus('Extracting transcript...');
      
      const response = await axios.post('/api/v1/generate-shorts', {
        youtube_url: youtubeUrl,
        max_shorts: 1,
        "platform": "youtube_shorts"
      });

      setProcessingStatus('AI analyzing highlights...');
      
      // Poll for results
      const jobId = response.data.job_id;
      const pollInterval = pollJobStatus(jobId);
      
      return pollInterval;
      
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to process video');
      setIsProcessing(false);
      setChatHistory(prev => [...prev, { 
        role: 'assistant', 
        content: `Error: ${err.response?.data?.detail || 'Failed to process video'}` 
      }]);
      return null;
    }
  };

  // Trigger video processing on mount
  useEffect(() => {
    let pollInterval = null;
    
    if (youtubeUrl && !hasProcessedRef.current) {
      hasProcessedRef.current = true;
      processVideo().then(interval => {
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
        const { status, shorts: generatedShorts, progress, percent } = response.data;

        if (progress) {
          setProcessingStatus(progress);
        }

        // Update progress percentage (0-100)
        if (typeof percent === 'number') {
          setProcessingProgress(Math.min(Math.max(percent, 0), 100));
        } else {
          // Estimate based on attempts if backend doesn't provide
          setProcessingProgress(Math.min((attempts / maxAttempts) * 100, 95));
        }

        if (status === 'completed' && generatedShorts && generatedShorts.length > 0) {
          clearInterval(poll);
          setProcessingProgress(100);
          
          // Convert shorts to clips format
          const newClips = generatedShorts.map((short, idx) => ({
            id: idx + 1,
            title: short.title || `Highlight ${idx + 1}`,
            startTime: formatTime(short.start_time),
            endTime: formatTime(short.end_time),
            duration: short.duration || short.duration_seconds || 30,
            filename: short.filename,
            url: short.download_url || `/api/v1/download/${short.filename}`
          }));
          
          setClips(newClips);
          setIsProcessing(false);
          setChatHistory(prev => [...prev, { 
            role: 'assistant', 
            content: `✅ Generated ${generatedShorts.length} video highlights! Click any clip to preview.`,
            timestamp: new Date().toISOString()
          }]);
        } else if (status === 'failed') {
          clearInterval(poll);
          setError('Video processing failed');
          setIsProcessing(false);
        } else if (attempts >= maxAttempts) {
          clearInterval(poll);
          setError('Processing timeout - please try again');
          setIsProcessing(false);
        }
      } catch (err) {
        clearInterval(poll);
        setError('Failed to check processing status');
        setIsProcessing(false);
        console.error('Error polling job status:', err);
      }
    }, 1000);

    return poll; // Return interval ID for cleanup
  };

  const formatTime = (timeInput) => {
    // Handle both timestamp strings (MM:SS or HH:MM:SS) and seconds (number)
    let seconds = 0;
    
    if (typeof timeInput === 'string') {
      // Parse timestamp string (e.g., "00:30" or "01:30:45")
      const parts = timeInput.split(':').map(Number);
      if (parts.length === 2) {
        // MM:SS format
        seconds = parts[0] * 60 + parts[1];
      } else if (parts.length === 3) {
        // HH:MM:SS format
        seconds = parts[0] * 3600 + parts[1] * 60 + parts[2];
      }
    } else if (typeof timeInput === 'number') {
      seconds = timeInput;
    }
    
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }
    return `00:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
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
        duration: clipDuration
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
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
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
        videoRef.current.play().catch(err => console.log('Autoplay prevented:', err));
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
      setDuration(videoRef.current.duration);
      videoRef.current.volume = volume;
    }
  };

  const handleProgressClick = (e) => {
    if (videoRef.current) {
      const rect = e.currentTarget.getBoundingClientRect();
      const pos = (e.clientX - rect.left) / rect.width;
      videoRef.current.currentTime = pos * videoRef.current.duration;
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
    if (!seconds || isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!chatMessage.trim() || isAiThinking) return;

    const userMessage = chatMessage.trim();
    setChatMessage('');

    // Add user message to chat
    setChatHistory(prev => [...prev, {
      role: 'user',
      content: userMessage,
      timestamp: new Date().toISOString()
    }]);

    // Show AI thinking state
    setIsAiThinking(true);
    setChatHistory(prev => [...prev, {
      role: 'assistant',
      content: '🤔 Analyzing your request...',
      timestamp: new Date().toISOString(),
      isThinking: true
    }]);

    try {
      // Send message to Gemini AI agent
      const response = await axios.post('/api/v1/ai-agent/execute', {
        message: userMessage,
        context: {
          clips,
          selectedClipIndex,
          selectedClip,
          videoInfo: {
            youtubeUrl,
            videoId
          }
        }
      });

      const { action, parameters, message: aiMessage, updatedClips } = response.data;

      // Remove thinking message
      setChatHistory(prev => prev.filter(msg => !msg.isThinking));

      // IMMEDIATELY show AI's conversational reply (Copilot-like)
      setChatHistory(prev => [...prev, {
        role: 'assistant',
        content: aiMessage || 'Got it! Working on that...',
        timestamp: new Date().toISOString()
      }]);

      // THEN execute the action in the background
      if (action && parameters) {
        // Show what action is being performed
        setChatHistory(prev => [...prev, {
          role: 'assistant',
          content: `🔄 Executing: ${action}...`,
          timestamp: new Date().toISOString(),
          isExecuting: true
        }]);

        await executeAiAction(action, parameters, updatedClips);

        // Remove executing message and show completion
        setChatHistory(prev => prev.filter(msg => !msg.isExecuting));
        setChatHistory(prev => [...prev, {
          role: 'assistant',
          content: '✅ Done! Anything else I can help with?',
          timestamp: new Date().toISOString()
        }]);
      }

    } catch (error) {
      // Remove thinking message
      setChatHistory(prev => prev.filter(msg => !msg.isThinking));

      setChatHistory(prev => [...prev, {
        role: 'assistant',
        content: `❌ Sorry, I encountered an error: ${error.response?.data?.detail || error.message}. Please try again.`,
        timestamp: new Date().toISOString()
      }]);
      console.error('AI Agent error:', error);
    } finally {
      setIsAiThinking(false);
    }
  };

  // Execute AI-determined actions
  const executeAiAction = async (action, parameters, updatedClips) => {
    switch (action) {
      case 'trim_clip':
        if (parameters.clipIndex !== undefined && parameters.startTime !== undefined && parameters.endTime !== undefined) {
          const newClips = [...clips];
          newClips[parameters.clipIndex] = {
            ...newClips[parameters.clipIndex],
            startTime: formatTime(parameters.startTime),
            endTime: formatTime(parameters.endTime),
            duration: parameters.endTime - parameters.startTime
          };
          setClips(newClips);
        }
        break;

      case 'update_duration':
        if (parameters.clipIndex !== undefined && parameters.duration !== undefined) {
          const newClips = [...clips];
          newClips[parameters.clipIndex] = {
            ...newClips[parameters.clipIndex],
            duration: parameters.duration
          };
          setClips(newClips);
          setClipDuration(parameters.duration);
        }
        break;

      case 'update_title':
        if (parameters.clipIndex !== undefined && parameters.title) {
          const newClips = [...clips];
          newClips[parameters.clipIndex] = {
            ...newClips[parameters.clipIndex],
            title: parameters.title
          };
          setClips(newClips);
          setClipTitle(parameters.title);
        }
        break;

      case 'select_clip':
        if (parameters.clipIndex !== undefined && parameters.clipIndex < clips.length) {
          setSelectedClipIndex(parameters.clipIndex);
        }
        break;

      case 'delete_clip':
        if (parameters.clipIndex !== undefined) {
          const newClips = clips.filter((_, idx) => idx !== parameters.clipIndex);
          setClips(newClips);
          setSelectedClipIndex(Math.max(0, parameters.clipIndex - 1));
        }
        break;

      case 'duplicate_clip':
        if (parameters.clipIndex !== undefined) {
          const clipToDuplicate = clips[parameters.clipIndex];
          const newClip = {
            ...clipToDuplicate,
            id: clips.length + 1,
            title: `${clipToDuplicate.title} (Copy)`
          };
          setClips([...clips, newClip]);
        }
        break;

      case 'update_clips':
        if (updatedClips && Array.isArray(updatedClips)) {
          setClips(updatedClips);
        }
        break;

      case 'generate_captions':
        await generateCaptions();
        break;

      case 'apply_caption_style':
        const style = parameters.style || 'bold_modern';
        setSelectedCaptionStyle(style);
        await applyCaptionStyle(style);
        break;

      default:
        console.log('Unknown action:', action);
    }
  };

  const handleQuickAction = async (action) => {
    setChatHistory(prev => [...prev, {
      role: 'user',
      content: action,
      timestamp: new Date().toISOString()
    }]);
    
    // Trigger AI processing for quick actions
    const fakeEvent = { preventDefault: () => {}, target: { value: action } };
    setChatMessage(action);
    await handleSendMessage(fakeEvent);
  };

  const moveClip = (direction) => {
    const newIndex = selectedClipIndex + direction;
    if (newIndex >= 0 && newIndex < clips.length) {
      const newClips = [...clips];
      [newClips[selectedClipIndex], newClips[newIndex]] = [newClips[newIndex], newClips[selectedClipIndex]];
      setClips(newClips);
      setSelectedClipIndex(newIndex);
    }
  };

  const addClip = () => {
    const newClip = {
      id: clips.length + 1,
      title: `New Clip ${clips.length + 1}`,
      startTime: '00:00:00',
      endTime: '00:00:30',
      duration: 30
    };
    setClips([...clips, newClip]);
    setSelectedClipIndex(clips.length);
  };

  const handleExport = async () => {
    if (clips.length === 0) return;
    
    try {
      const clip = clips[selectedClipIndex];
      
      // Show notification
      setChatHistory(prev => [...prev, { 
        role: 'assistant', 
        content: '📥 Downloading video...',
        timestamp: new Date().toISOString()
      }]);

      // Get the video URL - use download_url if available, otherwise construct it
      const videoUrl = clip.download_url || `/api/v1/download/${clip.filename}`;
      
      // Fetch the video file
      const response = await axios.get(videoUrl, {
        responseType: 'blob',
        onDownloadProgress: (progressEvent) => {
          if (progressEvent.total) {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            setProcessingStatus(`Downloading... ${percentCompleted}%`);
          }
        }
      });

      // Create blob URL and trigger download
      const blob = new Blob([response.data], { type: 'video/mp4' });
      const url = globalThis.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = clip.filename || `short_${clip.title || selectedClipIndex + 1}.mp4`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      globalThis.URL.revokeObjectURL(url);

      // Success notification
      setChatHistory(prev => [...prev, { 
        role: 'assistant', 
        content: `✅ Video "${clip.title}" downloaded successfully!`,
        timestamp: new Date().toISOString()
      }]);
    } catch (error) {
      setChatHistory(prev => [...prev, { 
        role: 'assistant', 
        content: '❌ Failed to download video. Please try again.',
        timestamp: new Date().toISOString()
      }]);
      console.error('Download error:', error);
    }
  };

  const handlePublish = () => {
    if (clips.length === 0) return;
    
    // Open publish modal instead of directly navigating
    setShowPublishModal(true);
  };

  const handlePlatformToggle = (platform) => {
    if (selectedPlatforms.includes(platform)) {
      setSelectedPlatforms(selectedPlatforms.filter(p => p !== platform));
    } else {
      setSelectedPlatforms([...selectedPlatforms, platform]);
    }
  };

  const handlePublishConfirm = async () => {
    if (selectedPlatforms.length === 0) {
      setChatHistory(prev => [...prev, { 
        role: 'assistant', 
        content: '⚠️ Please select at least one platform to publish.',
        timestamp: new Date().toISOString()
      }]);
      return;
    }

    setShowPublishModal(false);
    
    // Show publishing notification
    setChatHistory(prev => [...prev, { 
      role: 'assistant', 
      content: `🚀 Publishing to ${selectedPlatforms.join(', ')}...`,
      timestamp: new Date().toISOString()
    }]);
    
    // Simulate publishing
    setTimeout(() => {
      setChatHistory(prev => [...prev, { 
        role: 'assistant', 
        content: `✅ Successfully published to ${selectedPlatforms.join(', ')}! Redirecting to dashboard...`,
        timestamp: new Date().toISOString()
      }]);
      
      setTimeout(() => {
        navigate('/dashboard');
      }, 1500);
    }, 2000);
  };

  const handleDuplicateClip = () => {
    if (!selectedClip) return;
    
    const newClip = {
      ...selectedClip,
      id: clips.length + 1,
      title: `${selectedClip.title} (Copy)`
    };
    setClips([...clips, newClip]);
    setChatHistory(prev => [...prev, { 
      role: 'assistant', 
      content: '✅ Clip duplicated successfully!' 
    }]);
  };

  const handleDeleteClip = () => {
    if (!selectedClip || clips.length <= 1) return;
    
    const newClips = clips.filter((_, idx) => idx !== selectedClipIndex);
    setClips(newClips);
    setSelectedClipIndex(Math.max(0, selectedClipIndex - 1));
    setChatHistory(prev => [...prev, { 
      role: 'assistant', 
      content: '🗑️ Clip deleted successfully!' 
    }]);
  };

  // Caption generation functions
  const generateCaptions = async () => {
    if (!selectedClip) return;
    
    setIsGeneratingCaptions(true);
    
    try {
      setChatHistory(prev => [...prev, {
        role: 'assistant',
        content: '🎤 Generating captions from audio... This may take a minute.',
        timestamp: new Date().toISOString()
      }]);

      // Start caption generation
      const response = await axios.post(
        `/api/v1/clips/${selectedClip.id}/generate-captions`
      );
      
      const jobId = response.data.job_id;
      
      // Poll for completion
      pollCaptionJob(jobId);
      
    } catch (error) {
      console.error('Caption generation failed:', error);
      setChatHistory(prev => [...prev, {
        role: 'assistant',
        content: `❌ Failed to generate captions: ${error.message}`,
        timestamp: new Date().toISOString()
      }]);
      setIsGeneratingCaptions(false);
    }
  };

  const pollCaptionJob = (jobId) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await axios.get(`/api/v1/job/${jobId}`);
        const { status, progress } = response.data;
        
        setProcessingStatus(`Generating captions... ${progress}%`);
        
        if (status === 'completed') {
          clearInterval(pollInterval);
          
          // Fetch captions
          const captionsResponse = await axios.get(
            `/api/v1/clips/${selectedClip.id}/captions`
          );
          
          setCaptions(captionsResponse.data.captions);
          setShowCaptionPreview(true);
          setIsGeneratingCaptions(false);
          
          setChatHistory(prev => [...prev, {
            role: 'assistant',
            content: '✅ Captions generated! Choose a style and preview below.',
            timestamp: new Date().toISOString()
          }]);
          
        } else if (status === 'failed') {
          clearInterval(pollInterval);
          setIsGeneratingCaptions(false);
          setChatHistory(prev => [...prev, {
            role: 'assistant',
            content: '❌ Caption generation failed. Please try again.',
            timestamp: new Date().toISOString()
          }]);
        }
      } catch (error) {
        clearInterval(pollInterval);
        setIsGeneratingCaptions(false);
        console.error('Caption poll error:', error);
      }
    }, 2000);
  };

  const applyCaptionStyle = async (styleName) => {
    if (!captions) {
      setChatHistory(prev => [...prev, {
        role: 'assistant',
        content: '⚠️ Please generate captions first.',
        timestamp: new Date().toISOString()
      }]);
      return;
    }
    
    setIsProcessing(true);
    setProcessingStatus('Applying caption style...');
    
    try {
      const response = await axios.post(
        `/api/v1/clips/${selectedClip.id}/apply-captions`,
        null,
        { params: { style_name: styleName } }
      );
      
      const jobId = response.data.job_id;
      
      setChatHistory(prev => [...prev, {
        role: 'assistant',
        content: `🎨 Applying ${CAPTION_STYLES[styleName].name} style to video...`,
        timestamp: new Date().toISOString()
      }]);
      
      // Poll for completion
      pollCaptionBurnJob(jobId);
      
    } catch (error) {
      console.error('Apply captions failed:', error);
      setIsProcessing(false);
      setChatHistory(prev => [...prev, {
        role: 'assistant',
        content: `❌ Failed to apply captions: ${error.message}`,
        timestamp: new Date().toISOString()
      }]);
    }
  };

  const pollCaptionBurnJob = (jobId) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await axios.get(`/api/v1/job/${jobId}`);
        const { status, progress, result } = response.data;
        
        setProcessingStatus(`Burning captions into video... ${progress}%`);
        setProcessingProgress(progress);
        
        if (status === 'completed') {
          clearInterval(pollInterval);
          
          // Update clip with new file
          const updatedClips = [...clips];
          updatedClips[selectedClipIndex] = {
            ...updatedClips[selectedClipIndex],
            url: result.new_file_path,
            hasCaptions: true
          };
          setClips(updatedClips);
          
          // Reload video
          if (videoRef.current) {
            videoRef.current.load();
          }
          
          setChatHistory(prev => [...prev, {
            role: 'assistant',
            content: '✅ Captions applied successfully! Check the preview.',
            timestamp: new Date().toISOString()
          }]);
          
          setIsProcessing(false);
          setProcessingProgress(0);
          
        } else if (status === 'failed') {
          clearInterval(pollInterval);
          setIsProcessing(false);
          setProcessingProgress(0);
          setChatHistory(prev => [...prev, {
            role: 'assistant',
            content: '❌ Caption burning failed. Please try again.',
            timestamp: new Date().toISOString()
          }]);
        }
      } catch (error) {
        clearInterval(pollInterval);
        setIsProcessing(false);
        setProcessingProgress(0);
        console.error('Caption burn poll error:', error);
      }
    }, 2000);
  };

  // Update current caption word based on video time (for preview)
  useEffect(() => {
    if (!captions || !showCaptionPreview || !captions.words) return;
    
    const updateCaption = () => {
      const time = videoRef.current?.currentTime || 0;
      
      // Find current word
      const currentWord = captions.words.find(
        word => time >= word.start && time <= word.end
      );
      
      if (currentWord) {
        setCurrentCaption(currentWord.word);
      } else {
        setCurrentCaption('');
      }
    };
    
    const interval = setInterval(updateCaption, 100);
    return () => clearInterval(interval);
  }, [captions, showCaptionPreview]);

  return (
    <div className="min-h-screen bg-white flex flex-col">
      {/* Top Navigation */}
      <div className="border-b border-gray-200 bg-white px-4 py-3 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" onClick={() => navigate('/')}>
            <ArrowLeft className="h-4 w-4" />
            Back
          </Button>
          <h2 className="text-lg font-semibold text-gray-900">Video Editor</h2>
        </div>
        <div className="flex items-center gap-2">
          <Button 
            variant="ghost" 
            size="icon"
            onClick={() => setIsLeftPanelVisible(!isLeftPanelVisible)}
            aria-label={isLeftPanelVisible ? 'Hide Copilot panel' : 'Show Copilot panel'}
            className={!isLeftPanelVisible ? 'bg-gray-100' : ''}
          >
            <PanelLeft className="h-4 w-4" />
          </Button>
          <Button 
            variant="ghost" 
            size="icon"
            onClick={() => setIsRightPanelVisible(!isRightPanelVisible)}
            aria-label={isRightPanelVisible ? 'Hide Properties panel' : 'Show Properties panel'}
            className={!isRightPanelVisible ? 'bg-gray-100' : ''}
          >
            <PanelRight className="h-4 w-4" />
          </Button>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleExport} disabled={isProcessing || clips.length === 0}>
            <Download className="h-4 w-4" />
            Export
          </Button>
          <Button className="bg-[#1E201E] hover:bg-[#1E201E]/90 text-white" onClick={handlePublish} disabled={isProcessing || clips.length === 0}>
            <Share2 className="h-4 w-4" />
            Publish
          </Button>
        </div>
      </div>

      <div 
        className="flex-1 grid overflow-hidden transition-all duration-300"
        style={{
          gridTemplateColumns: isLeftPanelVisible && isRightPanelVisible 
            ? `${chatPanelWidth}px 1fr 350px` 
            : isLeftPanelVisible 
            ? `${chatPanelWidth}px 1fr 0px`
            : isRightPanelVisible 
            ? `0px 1fr 350px`
            : '1fr'
        }}
      >
        {/* Left Panel - Assistant Chat */}
        {isLeftPanelVisible && (
          <aside className="border-r border-gray-200 bg-white flex flex-col overflow-hidden relative" style={{ width: `${chatPanelWidth}px`, minWidth: '280px', maxWidth: '600px' }}>
            {/* Resize Handle */}
            <div 
              className="absolute right-0 top-0 bottom-0 w-2 cursor-col-resize hover:bg-gray-100 z-10 flex items-center justify-center"
              onMouseDown={handleResizeStart}
              aria-label="Resize chat panel"
            >
              <GripVertical className="h-4 w-4 text-gray-400 pointer-events-none" />
            </div>

            <div className="border-b border-gray-200 p-4 flex items-center justify-between bg-gray-50">
              <div className="flex items-center gap-3">
                <Sparkles className="h-4 w-4 text-[#1E201E]" />
                <div>
                  <h3 className="text-sm font-semibold text-gray-900">Copilot</h3>
                  <span className="text-xs text-gray-500">{isAiThinking ? 'Thinking...' : 'Ready to assist'}</span>
                </div>
              </div>
              <Button variant="ghost" size="icon" onClick={toggleChatExpand}>
                {isChatExpanded ? <Minimize className="h-4 w-4" /> : <Maximize className="h-4 w-4" />}
              </Button>
            </div>

            <div className="border-b border-gray-200 p-4 bg-white">
              <p className="text-xs font-semibold text-gray-500 uppercase mb-3">Suggestions</p>
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline" className="cursor-pointer hover:bg-gray-100" onClick={() => handleQuickAction('Use example video')}>
                  <Video className="h-3 w-3 mr-1" />
                  Use example video
                </Badge>
                <Badge variant="outline" className="cursor-pointer hover:bg-gray-100" onClick={() => handleQuickAction('Add live captions')}>
                  <Type className="h-3 w-3 mr-1" />
                  Add live captions
                </Badge>
                <Badge variant="outline" className="cursor-pointer hover:bg-gray-100" onClick={() => handleQuickAction('Dub in Kannada')}>
                  <Volume2 className="h-3 w-3 mr-1" />
                  Dub in Kannada
                </Badge>
                <Badge variant="outline" className="cursor-pointer hover:bg-gray-100" onClick={() => handleQuickAction('Summarize scenes')}>
                  <Wand2 className="h-3 w-3 mr-1" />
                  Summarize scenes
                </Badge>
                <Badge variant="outline" className="cursor-pointer hover:bg-gray-100" onClick={() => handleQuickAction('Change video URL')}>
                  <ArrowLeft className="h-3 w-3 mr-1" />
                  Change video URL
                </Badge>
              </div>
            </div>

            <ScrollArea className="flex-1 p-4">
              <div className="space-y-4">
                {chatHistory.map((msg, idx) => (
                  <div key={`msg-${idx}-${msg.content.substring(0, 20)}`} className="flex gap-3">
                    <div className={cn(
                      "w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0",
                      msg.role === 'assistant' ? "bg-[#1E201E] text-white" : "bg-gray-200 text-gray-700"
                    )}>
                      {msg.role === 'assistant' ? (
                        <Sparkles className="h-4 w-4" />
                      ) : (
                        <span className="text-xs font-semibold">You</span>
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-semibold text-gray-900">
                          {msg.role === 'assistant' ? 'Copilot' : 'You'}
                        </span>
                        <span className="text-xs text-gray-500">
                          {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                      <div className={cn(
                        "text-sm text-gray-700 leading-relaxed",
                        msg.isThinking && "animate-pulse text-gray-500 italic",
                        msg.isExecuting && "text-blue-600 font-medium"
                      )}>
                        {msg.content}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>

            <form className="border-t border-gray-200 p-4 bg-gray-50" onSubmit={handleSendMessage}>
              <div className="flex items-center gap-2 bg-white border border-gray-300 rounded-lg px-3 focus-within:ring-2 focus-within:ring-[#1E201E] focus-within:border-[#1E201E]">
                <Input
                  type="text"
                  placeholder={isAiThinking ? "AI is processing..." : "Ask Copilot to edit your video..."}
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
                  {isAiThinking ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                </Button>
              </div>
              <p className="text-xs text-gray-500 mt-2 text-center">💡 Try: "Trim clip to 20s" or "Change title to Marketing Tips"</p>
            </form>
          </aside>
        )}

        {/* Center Panel - Video Preview (Fixed Size) */}
        <main className="flex flex-col bg-white p-6 overflow-hidden">
          <div className="flex-1 flex items-center justify-center">
            <div className="relative w-[360px] h-[640px] bg-black rounded-3xl overflow-hidden shadow-2xl">
            {isProcessing ? (
              // Loading animation with strike-through list
              <div className="relative w-full h-full rounded-3xl overflow-hidden">
                {thumbnailUrl && (
                  <img 
                    src={thumbnailUrl} 
                    alt="Video thumbnail" 
                    className="w-full h-full object-cover blur-2xl brightness-50 opacity-50 rounded-3xl"
                  />
                )}
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/30 backdrop-blur-md rounded-3xl p-8 border border-white/10">
                  {/* Loading steps list */}
                  <div className="relative z-10 w-full max-w-md">
                    <div className="mb-6 text-center">
                      <div className="loader-wrapper-processing">
                        <span className="loader-letter">G</span>
                        <span className="loader-letter">e</span>
                        <span className="loader-letter">n</span>
                        <span className="loader-letter">e</span>
                        <span className="loader-letter">r</span>
                        <span className="loader-letter">a</span>
                        <span className="loader-letter">t</span>
                        <span className="loader-letter">i</span>
                        <span className="loader-letter">n</span>
                        <span className="loader-letter">g</span>
                        <div className="loader"></div>
                      </div>
                      <p className="text-lg font-semibold text-white mt-4">{Math.round(processingProgress)}%</p>
                    </div>
                    
                    <div className="bg-white/10 backdrop-blur-md rounded-2xl border border-white/20 p-6">
                      <div className="space-y-3">
                        {loadingSteps.map((step, index) => {
                          const isCompleted = currentLoadingStep > index;
                          const isCurrent = currentLoadingStep === index;
                          const isUpcoming = currentLoadingStep < index;
                          
                          return (
                            <div
                              key={step.id}
                              className={`
                                transition-all duration-500 transform
                                ${isCurrent ? 'scale-105' : 'scale-100'}
                                ${isUpcoming && index === currentLoadingStep + 1 ? 'opacity-50' : ''}
                                ${isUpcoming && index > currentLoadingStep + 1 ? 'opacity-30' : ''}
                              `}
                            >
                              <div className="flex items-center gap-3">
                                <div className={`
                                  w-5 h-5 rounded-full flex items-center justify-center transition-all duration-500
                                  ${isCompleted ? 'bg-green-500' : isCurrent ? 'bg-gradient-to-r from-purple-500 to-pink-500 animate-pulse' : 'bg-white/20'}
                                `}>
                                  {isCompleted && (
                                    <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                                    </svg>
                                  )}
                                  {isCurrent && (
                                    <div className="w-2 h-2 bg-white rounded-full"></div>
                                  )}
                                </div>
                                <span className={`
                                  text-sm font-medium transition-all duration-500
                                  ${isCompleted ? 'text-gray-400 line-through' : isCurrent ? 'text-white' : 'text-gray-500'}
                                `}>
                                  {step.text}
                                </span>
                              </div>
                              {isCurrent && (
                                <div className="ml-8 mt-1">
                                  <div className="h-1 bg-white/20 rounded-full overflow-hidden">
                                    <div 
                                      className="h-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-1000"
                                      style={{ width: `${(processingProgress % 12.5) * 8}%` }}
                                    ></div>
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                    
                    <div className="mt-6 text-center">
                      <p className="text-sm text-white/70">{processingStatus}</p>
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
                        console.error('Video load error:', e);
                        console.error('Video URL:', selectedClip.url);
                        console.error('Video element error details:', videoRef.current?.error);
                        setError(`Failed to load video: ${videoRef.current?.error?.message || 'Unknown error'}`);
                      }}
                      onCanPlay={() => {
                        console.log('Video can play, URL:', selectedClip.url);
                        setError('');
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
                      <div className={`caption-overlay caption-style-${selectedCaptionStyle}`}>
                        {currentCaption}
                      </div>
                    )}
                    
                    {/* Video Controls */}
                    <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/80 via-black/40 to-transparent backdrop-blur-sm opacity-0 hover:opacity-100 transition-opacity rounded-b-3xl">
                      <div 
                        className="w-full h-1.5 bg-white/20 rounded-full cursor-pointer mb-3 hover:h-2 transition-all"
                        onClick={handleProgressClick}
                        role="progressbar"
                        aria-label="Video progress"
                      >
                        <div 
                          className="h-full bg-gradient-to-r from-[#1E201E] via-purple-600 to-pink-500 rounded-full transition-all shadow-lg shadow-[#1E201E]/50"
                          style={{ width: `${duration > 0 ? (currentTime / duration) * 100 : 0}%` }}
                        />
                      </div>
                      
                      <div className="flex items-center gap-3 text-white">
                        <Button 
                          size="icon"
                          className="h-11 w-11 bg-[#1E201E] hover:bg-[#1E201E]/90 text-white rounded-full"
                          onClick={handlePlayPause}
                          aria-label={isPlaying ? "Pause" : "Play"}
                        >
                          {isPlaying ? <Pause className="h-5 w-5" /> : <Play className="h-5 w-5" />}
                        </Button>
                        
                        <Button 
                          size="icon"
                          variant="ghost"
                          className="h-11 w-11 bg-white/10 hover:bg-white/20 text-white rounded-full border border-white/20"
                          onClick={toggleMute}
                          aria-label={isMuted ? "Unmute" : "Mute"}
                        >
                          {isMuted ? <Volume2 className="h-5 w-5 opacity-50" /> : <Volume2 className="h-5 w-5" />}
                        </Button>
                        
                        <div className="flex items-center gap-2">
                          <div 
                            className="w-20 h-1.5 bg-white/20 rounded-full cursor-pointer hover:h-2 transition-all"
                            onClick={handleVolumeChange}
                            role="slider"
                          >
                            <div 
                              className="h-full bg-white rounded-full transition-all"
                              style={{ width: `${(isMuted ? 0 : volume) * 100}%` }}
                            />
                          </div>
                        </div>
                        
                        <span className="text-sm font-medium ml-auto text-shadow">
                          {formatTimeDisplay(currentTime)} / {formatTimeDisplay(duration)}
                        </span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center justify-center p-8 text-gray-500 bg-gray-50 rounded-3xl">
                    <p>{error || 'No video available'}</p>
                  </div>
                )}
              </>
            )}
            </div>
          </div>

          {/* Timeline Section */}
          <div className="border-t border-gray-200 bg-gray-50 p-4">
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-sm font-semibold text-gray-900">Timeline</h4>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={addClip} disabled={isProcessing}>
                  <Plus className="h-4 w-4" />
                  Add Clip
                </Button>
                <Button 
                  size="sm" 
                  variant="outline"
                  onClick={() => moveClip(-1)} 
                  disabled={selectedClipIndex === 0 || isProcessing}
                >
                  <ChevronUp className="h-4 w-4" />
                  Move Up
                </Button>
                <Button 
                  size="sm" 
                  variant="outline"
                  onClick={() => moveClip(1)} 
                  disabled={selectedClipIndex === clips.length - 1 || isProcessing}
                >
                  <ChevronDown className="h-4 w-4" />
                  Move Down
                </Button>
              </div>
            </div>

            {/* Time Ruler */}
            {!isProcessing && clips.length > 0 && selectedClip && (
              <div className="relative h-10 bg-gray-200 rounded-lg mb-4 overflow-hidden">
                <div className="flex h-full relative">
                  {Array.from({ length: Math.ceil(selectedClip.duration / 5) + 1 }, (_, i) => (
                    <div key={i} className="flex-1 flex flex-col items-start justify-start p-1">
                      <div className="w-0.5 h-2 bg-gray-400 mb-1"></div>
                      <span className="text-xs text-gray-600">{i * 5}s</span>
                    </div>
                  ))}
                </div>
                <div 
                  className="absolute top-0 bottom-0 w-0.5 bg-[#1E201E] z-10 transition-all"
                  style={{ left: `${(currentTime / selectedClip.duration) * 100}%` }}
                >
                  <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-3 h-3 bg-[#1E201E] rounded-full border-2 border-white shadow-lg"></div>
                </div>
              </div>
            )}

            <ScrollArea className="w-full">
              <div className="flex gap-3 pb-2">
                {isProcessing ? (
                  <div className="w-full text-center py-8 text-gray-500">
                    <p>Generating clips...</p>
                  </div>
                ) : (
                  <>
                    {clips.length > 0 ? (
                      clips.map((clip, idx) => (
                        <Card
                          key={clip.id}
                          className={cn(
                            "min-w-[200px] cursor-pointer transition-all",
                            idx === selectedClipIndex 
                              ? "border-[#1E201E] border-2 bg-[#1E201E]/5 shadow-md" 
                              : "border-gray-200 hover:border-gray-300"
                          )}
                          onClick={() => setSelectedClipIndex(idx)}
                        >
                          <CardContent className="p-4">
                            <div className="text-xs font-bold text-[#1E201E] mb-2">#{idx + 1}</div>
                            <div className="text-sm font-semibold text-gray-900 mb-1 truncate">{clip.title}</div>
                            <div className="text-xs text-[#1E201E] font-semibold mb-1">{clip.duration}s</div>
                            <div className="text-xs text-gray-500 font-mono">
                              {clip.startTime} - {clip.endTime}
                            </div>
                          </CardContent>
                        </Card>
                      ))
                    ) : (
                      <div className="w-full text-center py-8 text-gray-500">
                        <p>No clips yet</p>
                      </div>
                    )}
                  </>
                )}
              </div>
            </ScrollArea>
          </div>
        </main>

        {/* Right Panel - Properties */}
        {isRightPanelVisible && (
          <aside className="border-l border-gray-200 bg-white overflow-y-auto">
            <div className="border-b border-gray-200 p-4 bg-gray-50">
              <h3 className="text-base font-semibold text-gray-900">Properties</h3>
              <p className="text-sm text-gray-500">Edit selected clip</p>
            </div>

            {selectedClip ? (
              <ScrollArea className="p-4">
                <div className="space-y-6">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm">Title</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <Input
                        type="text"
                        value={clipTitle}
                        onChange={(e) => setClipTitle(e.target.value)}
                        disabled={isProcessing}
                        aria-label="Clip title"
                      />
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm">Time Range</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 gap-2">
                        <Input
                          type="text"
                          value={selectedClip.startTime}
                          readOnly
                          className="text-center"
                          aria-label="Start time"
                        />
                        <Input
                          type="text"
                          value={selectedClip.endTime}
                          readOnly
                          className="text-center"
                          aria-label="End time"
                        />
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm">Duration</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="flex items-center gap-3">
                        <Slider
                          value={[clipDuration]}
                          onValueChange={(value) => setClipDuration(value[0])}
                          min={15}
                          max={60}
                          step={1}
                          disabled={isProcessing}
                          className="flex-1"
                        />
                        <span className="text-sm font-semibold text-[#1E201E] min-w-[40px]">{clipDuration}s</span>
                      </div>
                      <div className="grid grid-cols-3 gap-2">
                        <Button
                          variant={clipDuration === 15 ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => setClipDuration(15)}
                          disabled={isProcessing}
                          className={clipDuration === 15 ? 'bg-[#1E201E] hover:bg-[#1E201E]/90 text-white' : ''}
                        >
                          15s
                        </Button>
                        <Button
                          variant={clipDuration === 30 ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => setClipDuration(30)}
                          disabled={isProcessing}
                          className={clipDuration === 30 ? 'bg-[#1E201E] hover:bg-[#1E201E]/90 text-white' : ''}
                        >
                          30s
                        </Button>
                        <Button
                          variant={clipDuration === 60 ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => setClipDuration(60)}
                          disabled={isProcessing}
                          className={clipDuration === 60 ? 'bg-[#1E201E] hover:bg-[#1E201E]/90 text-white' : ''}
                        >
                          60s
                        </Button>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm">Editing Tools</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 gap-2">
                        <Button variant="outline" disabled={isProcessing} className="h-20 flex-col">
                          <Scissors className="h-5 w-5 mb-1" />
                          <span className="text-xs">Trim</span>
                        </Button>
                        <Button variant="outline" disabled={isProcessing} className="h-20 flex-col">
                          <Type className="h-5 w-5 mb-1" />
                          <span className="text-xs">Text</span>
                        </Button>
                        <Button variant="outline" disabled={isProcessing} className="h-20 flex-col">
                          <Volume2 className="h-5 w-5 mb-1" />
                          <span className="text-xs">Audio</span>
                        </Button>
                        <Button variant="outline" disabled={isProcessing} className="h-20 flex-col">
                          <Wand2 className="h-5 w-5 mb-1" />
                          <span className="text-xs">Effects</span>
                        </Button>
                        <Button variant="outline" disabled={isProcessing} className="h-20 flex-col">
                          <Layers className="h-5 w-5 mb-1" />
                          <span className="text-xs">Layers</span>
                        </Button>
                        <Button variant="outline" disabled={isProcessing} className="h-20 flex-col">
                          <RotateCw className="h-5 w-5 mb-1" />
                          <span className="text-xs">Rotate</span>
                        </Button>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm">Transform</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 gap-2">
                        <Button variant="outline" disabled={isProcessing} size="sm">
                          <ZoomIn className="h-4 w-4 mr-2" />
                          Zoom In
                        </Button>
                        <Button variant="outline" disabled={isProcessing} size="sm">
                          <ZoomOut className="h-4 w-4 mr-2" />
                          Zoom Out
                        </Button>
                        <Button variant="outline" disabled={isProcessing} size="sm" className="col-span-2">
                          <Maximize2 className="h-4 w-4 mr-2" />
                          Fit Screen
                        </Button>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm">Clip Actions</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <Button variant="outline" className="w-full justify-start" onClick={handleDuplicateClip} disabled={isProcessing}>
                        <Copy className="h-4 w-4 mr-2" />
                        Duplicate
                      </Button>
                      <Button variant="outline" className="w-full justify-start" disabled={isProcessing}>
                        <Save className="h-4 w-4 mr-2" />
                        Save
                      </Button>
                      <Button 
                        variant="outline" 
                        className="w-full justify-start text-red-600 hover:text-red-700 hover:bg-red-50" 
                        onClick={handleDeleteClip} 
                        disabled={isProcessing || clips.length <= 1}
                      >
                        <Trash2 className="h-4 w-4 mr-2" />
                        Delete
                      </Button>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm">Trim Controls</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 gap-2">
                        <Button variant="outline" disabled={isProcessing} size="sm">
                          <SkipBackIcon className="h-4 w-4 mr-2" />
                          Trim Start
                        </Button>
                        <Button variant="outline" disabled={isProcessing} size="sm">
                          Trim End
                          <SkipForward className="h-4 w-4 ml-2" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle className="text-sm">Clip Order</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-center gap-2">
                        <Input
                          type="number"
                          value={selectedClipIndex + 1}
                          readOnly
                          className="w-16 text-center"
                        />
                        <span className="text-sm text-gray-600">of {clips.length}</span>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </ScrollArea>
            ) : (
              <div className="p-8 text-center text-gray-500">
                <p>{isProcessing ? 'Processing video...' : 'No clip selected'}</p>
              </div>
            )}
          </aside>
        )}
      </div>

      {/* Publish Modal */}
      <Dialog open={showPublishModal} onOpenChange={setShowPublishModal}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Publish Your Short</DialogTitle>
            <DialogDescription>Choose platforms and configure your video settings</DialogDescription>
          </DialogHeader>

          <div className="space-y-6 py-4">
            {/* Platform Selection */}
            <div>
              <h3 className="text-base font-semibold text-gray-900 mb-2">Select Platforms</h3>
              <p className="text-sm text-gray-600 mb-4">Choose where you want to publish your video</p>
              <div className="grid grid-cols-2 gap-3">
                <Card
                  className={cn(
                    "cursor-pointer transition-all",
                    selectedPlatforms.includes('youtube') ? "border-[#1E201E] border-2 bg-[#1E201E]/5" : "border-gray-200 hover:border-gray-300"
                  )}
                  onClick={() => handlePlatformToggle('youtube')}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 bg-red-600 rounded-lg flex items-center justify-center">
                        <Play className="h-6 w-6 text-white" />
                      </div>
                      <div className="flex-1">
                        <h4 className="text-sm font-semibold text-gray-900">YouTube Shorts</h4>
                        <p className="text-xs text-gray-500">9:16 • 60s max</p>
                      </div>
                      {selectedPlatforms.includes('youtube') && (
                        <div className="w-6 h-6 bg-[#1E201E] rounded-full flex items-center justify-center text-white text-xs font-bold">✓</div>
                      )}
                    </div>
                  </CardContent>
                </Card>

                <Card
                  className={cn(
                    "cursor-pointer transition-all",
                    selectedPlatforms.includes('instagram') ? "border-[#1E201E] border-2 bg-[#1E201E]/5" : "border-gray-200 hover:border-gray-300"
                  )}
                  onClick={() => handlePlatformToggle('instagram')}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 bg-gradient-to-r from-purple-600 via-pink-600 to-orange-500 rounded-lg flex items-center justify-center">
                        <Video className="h-6 w-6 text-white" />
                      </div>
                      <div className="flex-1">
                        <h4 className="text-sm font-semibold text-gray-900">Instagram Reels</h4>
                        <p className="text-xs text-gray-500">9:16 • 90s max</p>
                      </div>
                      {selectedPlatforms.includes('instagram') && (
                        <div className="w-6 h-6 bg-[#1E201E] rounded-full flex items-center justify-center text-white text-xs font-bold">✓</div>
                      )}
                    </div>
                  </CardContent>
                </Card>

                <Card
                  className={cn(
                    "cursor-pointer transition-all",
                    selectedPlatforms.includes('tiktok') ? "border-[#1E201E] border-2 bg-[#1E201E]/5" : "border-gray-200 hover:border-gray-300"
                  )}
                  onClick={() => handlePlatformToggle('tiktok')}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 bg-black rounded-lg flex items-center justify-center">
                        <Play className="h-6 w-6 text-white" />
                      </div>
                      <div className="flex-1">
                        <h4 className="text-sm font-semibold text-gray-900">TikTok</h4>
                        <p className="text-xs text-gray-500">9:16 • 10m max</p>
                      </div>
                      {selectedPlatforms.includes('tiktok') && (
                        <div className="w-6 h-6 bg-[#1E201E] rounded-full flex items-center justify-center text-white text-xs font-bold">✓</div>
                      )}
                    </div>
                  </CardContent>
                </Card>

                <Card
                  className={cn(
                    "cursor-pointer transition-all",
                    selectedPlatforms.includes('facebook') ? "border-[#1E201E] border-2 bg-[#1E201E]/5" : "border-gray-200 hover:border-gray-300"
                  )}
                  onClick={() => handlePlatformToggle('facebook')}
                >
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 bg-blue-600 rounded-lg flex items-center justify-center">
                        <Video className="h-6 w-6 text-white" />
                      </div>
                      <div className="flex-1">
                        <h4 className="text-sm font-semibold text-gray-900">Facebook Reels</h4>
                        <p className="text-xs text-gray-500">9:16 • 90s max</p>
                      </div>
                      {selectedPlatforms.includes('facebook') && (
                        <div className="w-6 h-6 bg-[#1E201E] rounded-full flex items-center justify-center text-white text-xs font-bold">✓</div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>

            <Separator />

            {/* Video Settings */}
            <div>
              <h3 className="text-base font-semibold text-gray-900 mb-4">Video Settings</h3>
              <div className="space-y-4">
                <div>
                  <label htmlFor="video-title" className="text-sm font-medium text-gray-700 mb-2 block">Title</label>
                  <Input
                    id="video-title"
                    type="text"
                    placeholder="Enter video title..."
                    value={publishSettings.title}
                    onChange={(e) => setPublishSettings({...publishSettings, title: e.target.value})}
                  />
                </div>

                <div>
                  <label htmlFor="video-description" className="text-sm font-medium text-gray-700 mb-2 block">Description</label>
                  <textarea
                    id="video-description"
                    placeholder="Add a description..."
                    value={publishSettings.description}
                    onChange={(e) => setPublishSettings({...publishSettings, description: e.target.value})}
                    className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                    rows="3"
                  />
                </div>

                <div>
                  <label htmlFor="video-tags" className="text-sm font-medium text-gray-700 mb-2 block">Tags (comma separated)</label>
                  <Input
                    id="video-tags"
                    type="text"
                    placeholder="trending, viral, shorts..."
                    value={publishSettings.tags}
                    onChange={(e) => setPublishSettings({...publishSettings, tags: e.target.value})}
                  />
                </div>

                <div>
                  <label htmlFor="aspect-ratio" className="text-sm font-medium text-gray-700 mb-2 block">Aspect Ratio</label>
                  <select
                    id="aspect-ratio"
                    value={publishSettings.aspectRatio}
                    onChange={(e) => setPublishSettings({...publishSettings, aspectRatio: e.target.value})}
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
            <Button variant="outline" onClick={() => setShowPublishModal(false)}>
              Cancel
            </Button>
            <Button 
              className="bg-[#1E201E] hover:bg-[#1E201E]/90 text-white"
              onClick={handlePublishConfirm}
              disabled={selectedPlatforms.length === 0}
            >
              <Share2 className="h-4 w-4 mr-2" />
              Publish to {selectedPlatforms.length > 0 ? `${selectedPlatforms.length} Platform${selectedPlatforms.length > 1 ? 's' : ''}` : 'Platforms'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default VideoEditor;
