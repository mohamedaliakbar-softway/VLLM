import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Video, Sparkles, ArrowRight, Zap, Clock, Share2, LogOut, User } from 'lucide-react';
import axios from 'axios';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';

function Landing() {
  console.log("hi");
  
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [user, setUser] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      const response = await axios.get('/auth/me', { withCredentials: true });
      if (response.data.authenticated) {
        setUser(response.data.user);
      }
    } catch (error) {
      console.log('Not authenticated');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleSignIn = () => {
    window.location.href = '/auth/login';
  };

  const handleLogout = () => {
    window.location.href = '/auth/logout';
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');
    
    // Validate YouTube URL format
    if (!youtubeUrl.includes('youtube.com') && !youtubeUrl.includes('youtu.be')) {
      setError('Please enter a valid YouTube URL');
      return;
    }

    // Redirect to editor with YouTube URL - processing will happen there
    navigate('/editor', { state: { youtubeUrl } });
  };

  return (
    <div className="min-h-screen bg-white relative overflow-hidden">
      {/* Navigation Bar */}
      <nav className="border-b border-gray-200 bg-white/80 backdrop-blur-sm relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-[#1E201E] rounded-lg flex items-center justify-center">
                <Video className="h-6 w-6 text-white" />
              </div>
              <span className="text-xl font-semibold text-gray-900">HighlightAI</span>
            </div>
            <div className="hidden md:flex items-center gap-6">
              <a href="#features" className="text-sm text-gray-600 hover:text-gray-900">Features</a>
              <a href="#how-it-works" className="text-sm text-gray-600 hover:text-gray-900">How It Works</a>
              <a href="#pricing" className="text-sm text-gray-600 hover:text-gray-900">Pricing</a>
            </div>
            <div className="flex items-center gap-3">
              {authLoading ? (
                <div className="h-9 w-20 bg-gray-100 animate-pulse rounded-md"></div>
              ) : user ? (
                <>
                  <div className="flex items-center gap-2">
                    {user.profile_image_url ? (
                      <img 
                        src={user.profile_image_url} 
                        alt={user.first_name || 'User'} 
                        className="w-8 h-8 rounded-full object-cover"
                      />
                    ) : (
                      <div className="w-8 h-8 rounded-full bg-[#1E201E] flex items-center justify-center">
                        <User className="h-4 w-4 text-white" />
                      </div>
                    )}
                    <span className="text-sm font-medium text-gray-900">
                      {user.first_name || user.email || 'User'}
                    </span>
                  </div>
                  <Button variant="ghost" onClick={handleLogout} size="sm">
                    <LogOut className="h-4 w-4" />
                    Logout
                  </Button>
                </>
              ) : (
                <>
                  <Button variant="ghost" onClick={handleSignIn}>
                    Sign In
                  </Button>
                  <Button className="bg-[#1E201E] hover:bg-[#1E201E]/90 text-white" onClick={handleSignIn}>
                    <Sparkles className="h-4 w-4" />
                    Get Started
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16 sm:py-24 text-center relative z-10">
        <Badge variant="outline" className="mb-8 inline-flex items-center gap-2 border-gray-300 text-gray-700">
          <Sparkles className="h-4 w-4" />
          AI-Powered Video Highlights
        </Badge>
        
        <h1 className="text-5xl sm:text-6xl font-bold text-gray-900 mb-6">
          Transform Videos into
          <span className="block h-16 bg-gradient-to-r from-[#1E201E] to-gray-600 rounded-lg mt-2 max-w-2xl mx-auto"></span>
        </h1>

        <p className="text-lg sm:text-xl text-gray-600 mb-12 max-w-2xl mx-auto">
          Paste any YouTube URL and let our advanced AI extract the most
          <br className="hidden sm:block" />
          engaging moments in seconds. Perfect for creating Shorts, Reels, and TikToks.
        </p>

        {/* URL Input */}
        <form onSubmit={handleSubmit} className="max-w-2xl mx-auto mb-6">
          <div className="flex flex-col sm:flex-row gap-3 p-1 bg-gray-50 rounded-xl border border-gray-200">
            <Input
              type="url"
              placeholder="https://youtube.com/watch?v=..."
              value={youtubeUrl}
              onChange={(e) => setYoutubeUrl(e.target.value)}
              required
              disabled={loading}
              className="flex-1 border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0"
            />
            <Button 
              type="submit" 
              disabled={!youtubeUrl || loading} 
              className="bg-[#1E201E] hover:bg-[#1E201E]/90 text-white whitespace-nowrap"
            >
              <Sparkles className="h-4 w-4" />
              Generate
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </form>

        {error && (
          <Alert variant="destructive" className="max-w-2xl mx-auto mb-6 border-red-200 bg-red-50">
            <AlertDescription className="text-red-800">{error}</AlertDescription>
          </Alert>
        )}

        <div className="flex items-center justify-center gap-2 text-sm text-gray-500 mb-12">
          <div className="text-green-600 font-bold">✓</div>
          <span>No credit card required • Free trial available</span>
        </div>

        {/* Feature Highlights */}
        <div className="flex flex-wrap items-center justify-center gap-8">
          <div className="flex items-center gap-2 text-gray-700">
            <Zap className="h-5 w-5 text-[#1E201E]" />
            <span className="text-sm font-medium">AI-Powered Detection</span>
          </div>
          <div className="flex items-center gap-2 text-gray-700">
            <Clock className="h-5 w-5 text-[#1E201E]" />
            <span className="text-sm font-medium">2-Minute Processing</span>
          </div>
          <div className="flex items-center gap-2 text-gray-700">
            <Share2 className="h-5 w-5 text-[#1E201E]" />
            <span className="text-sm font-medium">Multi-Platform Export</span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Landing;
