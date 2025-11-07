import { useState, useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Send, Download, Share2, Loader, Video, Wand2 } from 'lucide-react';
import axios from 'axios';

function Editor() {
  const location = useLocation();
  const navigate = useNavigate();
  const [jobId, setJobId] = useState(location.state?.jobId || null);
  const [jobData, setJobData] = useState(null);
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState('Initializing...');
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [selectedShort, setSelectedShort] = useState(null);
  const [processing, setProcessing] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (!jobId) {
      navigate('/');
      return;
    }

    let eventSource;
    let pollingInterval;
    
    const fetchJobResults = async () => {
      try {
        const response = await axios.get(`/api/v1/job/${jobId}`);
        
        if (response.data.status === 'completed') {
          setJobData(response.data);
          setProgress(100);
          setStatusMessage('Completed!');
          
          if (response.data.shorts && response.data.shorts.length > 0) {
            setSelectedShort(response.data.shorts[0]);
            setMessages([
              {
                type: 'system',
                content: `I've generated ${response.data.shorts.length} shorts from "${response.data.video_title}". You can ask me to add captions, change voice dubbing, adjust timing, or make other edits!`,
              },
            ]);
          }
          return true;
        } else if (response.data.status === 'failed') {
          setStatusMessage(`Failed: ${response.data.error || 'Unknown error'}`);
          setMessages([{ type: 'system', content: `Error: ${response.data.error}` }]);
          return true;
        }
        return false;
      } catch (error) {
        console.error('Failed to fetch job results:', error);
        return false;
      }
    };
    
    const startPolling = () => {
      pollingInterval = setInterval(async () => {
        const isComplete = await fetchJobResults();
        if (isComplete && pollingInterval) {
          clearInterval(pollingInterval);
        }
      }, 2000);
    };
    
    const connectSSE = () => {
      eventSource = new EventSource(`/api/v1/progress/${jobId}`);
      
      eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === 'heartbeat') return;
        
        setProgress(data.progress || 0);
        setStatusMessage(data.message || 'Processing...');
        
        if (data.status === 'completed') {
          fetchJobResults();
          eventSource.close();
        } else if (data.status === 'failed') {
          setMessages([{ type: 'system', content: `Error: ${data.message}` }]);
          eventSource.close();
        }
      };
      
      eventSource.onerror = () => {
        console.log('SSE failed, falling back to polling');
        eventSource.close();
        startPolling();
      };
    };
    
    fetchJobResults().then((isComplete) => {
      if (!isComplete) {
        connectSSE();
      }
    });
    
    return () => {
      if (eventSource) eventSource.close();
      if (pollingInterval) clearInterval(pollingInterval);
    };
  }, [jobId, navigate]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    if (!inputMessage.trim() || processing) return;

    const userMessage = inputMessage.trim();
    setInputMessage('');
    setMessages((prev) => [...prev, { type: 'user', content: userMessage }]);

    setProcessing(true);
    
    setTimeout(() => {
      const aiResponse = generateAIResponse(userMessage);
      setMessages((prev) => [...prev, { type: 'ai', content: aiResponse }]);
      setProcessing(false);
    }, 1500);
  };

  const generateAIResponse = (message) => {
    const lowerMsg = message.toLowerCase();

    if (lowerMsg.includes('caption') || lowerMsg.includes('subtitle')) {
      return "I'll add captions to your video! This feature will automatically generate and overlay subtitles. (Caption generation will be implemented in the enhanced backend)";
    } else if (lowerMsg.includes('kannada') || lowerMsg.includes('dub') || lowerMsg.includes('voice')) {
      return "Voice dubbing to Kannada is an exciting feature! This will use text-to-speech to translate and dub your video audio. (Voice dubbing will be implemented with AI TTS integration)";
    } else if (lowerMsg.includes('timing') || lowerMsg.includes('duration')) {
      return "I can help you adjust the timing! You can specify the exact start and end times you'd like.";
    } else if (lowerMsg.includes('platform') || lowerMsg.includes('publish') || lowerMsg.includes('share')) {
      return "I can help you publish to multiple platforms! Just click the share button on any short to post it to YouTube, Instagram, Facebook, LinkedIn, or TikTok with AI-generated marketing copy.";
    } else {
      return "I'm here to help edit your shorts! You can ask me to:\n• Add captions/subtitles\n• Dub to different languages (Kannada, Hindi, etc.)\n• Adjust timing and duration\n• Enhance visuals\n• Generate platform-specific marketing copy\n• Publish to social media";
    }
  };

  const handleDownload = async (short) => {
    try {
      window.open(short.download_url, '_blank');
    } catch (error) {
      console.error('Download failed:', error);
    }
  };

  const handleShare = (short) => {
    setMessages((prev) => [
      ...prev,
      {
        type: 'system',
        content: `Ready to share "${short.filename}"! Social media integration coming soon. You'll be able to post to YouTube Shorts, Instagram Reels, Facebook, LinkedIn, and TikTok with one click.`,
      },
    ]);
  };

  if (!jobId) {
    return null;
  }

  if (!jobData) {
    return (
      <div className="editor-container">
        <div className="progress-container">
          <div className="progress-card">
            <Loader className="spinner-large" size={64} />
            <h2>Processing Your Video</h2>
            <p className="progress-message">{statusMessage}</p>
            <div className="progress-bar-container">
              <div className="progress-bar" style={{ width: `${progress}%` }}>
                <span className="progress-text">{progress}%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="editor-container">
      <div className="chat-panel">
        <div className="chat-header">
          <Wand2 size={24} />
          <h2>AI Video Editor</h2>
        </div>

        <div className="messages-container">
          {messages.map((msg, idx) => (
            <div key={idx} className={`message message-${msg.type}`}>
              {msg.type === 'user' && <div className="message-avatar">You</div>}
              {msg.type === 'ai' && <div className="message-avatar ai-avatar">AI</div>}
              {msg.type === 'system' && <div className="message-avatar system-avatar">ℹ️</div>}
              <div className="message-content">{msg.content}</div>
            </div>
          ))}
          {processing && (
            <div className="message message-ai">
              <div className="message-avatar ai-avatar">AI</div>
              <div className="message-content">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={handleSendMessage} className="chat-input-form">
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            placeholder="Ask me to add captions, change voice to Kannada, adjust timing..."
            disabled={processing}
            className="chat-input"
          />
          <button type="submit" disabled={processing || !inputMessage.trim()} className="send-btn">
            <Send size={20} />
          </button>
        </form>
      </div>

      <div className="preview-panel">
        <div className="preview-header">
          <Video size={24} />
          <h2>Generated Shorts</h2>
        </div>

        <div className="shorts-list">
          {jobData.shorts?.map((short) => (
            <div
              key={short.short_id}
              className={`short-card ${selectedShort?.short_id === short.short_id ? 'selected' : ''}`}
              onClick={() => setSelectedShort(short)}
            >
              <div className="short-thumbnail">
                <Video size={48} />
              </div>
              <div className="short-info">
                <h3>Short #{short.short_id}</h3>
                <p className="short-time">{short.start_time} - {short.end_time}</p>
                <p className="short-duration">{short.duration_seconds}s</p>
                <div className="engagement-score">
                  <span className="score-label">Engagement:</span>
                  <span className="score-value">{short.engagement_score}/10</span>
                </div>
                <p className="marketing-text">{short.marketing_effectiveness}</p>
                <p className="cta-text">💡 {short.suggested_cta}</p>
              </div>
              <div className="short-actions">
                <button onClick={(e) => { e.stopPropagation(); handleDownload(short); }} className="action-btn">
                  <Download size={18} />
                  Download
                </button>
                <button onClick={(e) => { e.stopPropagation(); handleShare(short); }} className="action-btn share-btn">
                  <Share2 size={18} />
                  Share
                </button>
              </div>
            </div>
          ))}
        </div>

        {selectedShort && (
          <div className="selected-preview">
            <h3>Preview: Short #{selectedShort.short_id}</h3>
            <div className="video-placeholder">
              <Video size={64} />
              <p>Video preview will appear here</p>
              <a href={selectedShort.download_url} target="_blank" rel="noopener noreferrer" className="preview-link">
                Open Video
              </a>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Editor;
