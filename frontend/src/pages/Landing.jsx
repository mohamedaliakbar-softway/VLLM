import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Sparkles, ArrowRight, Zap, Clock, Share2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';

function Landing() {
  const [youtubeUrl, setYoutubeUrl] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

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
    <div className="h-screen bg-white relative overflow-hidden">
      {/* Circular Gradient Background Loader */}
      <div className="loader-wrapper loader-wrapper-home">
        <span className="loader-letter"></span>
        <span className="loader-letter"></span>
        <span className="loader-letter"></span>
        <span className="loader-letter"></span>
        <span className="loader-letter"></span>
        <span className="loader-letter"></span>
        <span className="loader-letter"></span>
        <span className="loader-letter"></span>
        <span className="loader-letter"></span>
        <span className="loader-letter"></span>
        <div className="loader"></div>
      </div>

      {/* Floating Navigation Bar */}
      <nav className="fixed top-6 left-1/2 transform -translate-x-1/2 w-full max-w-7xl px-4 sm:px-6 lg:px-8 bg-white/70 backdrop-blur-md rounded-xl shadow-lg z-50 border border-gray-100">
        <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <img 
                src="/ApplyX.png" 
                alt="Zapp.ai Logo" 
                className="w-10 h-10 rounded-lg object-contain"
              />
            </div>

            {/* Center - Product Name */}
            <div className="absolute left-1/2 transform -translate-x-1/2">
              <span className="text-xl font-semibold text-gray-900">Zapp.ai</span>
            </div>

            {/* Right Side Actions - Login and Sign Up */}
            <div className="flex items-center gap-3">
              <Link to="/signin">
                <Button variant="ghost" className="text-gray-700 hover:text-gray-900">
                  Login
                </Button>
              </Link>
              <Link to="/signup">
                <Button className="bg-[#1E201E] hover:bg-[#1E201E]/90 text-white">
                  Sign Up
                </Button>
              </Link>
            </div>
        </div>
      </nav>

  {/* Hero Section */}
  <div className="h-full max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pt-24 sm:pt-28 pb-4 sm:pb-6 text-center relative z-10 flex flex-col items-center justify-center">
        <Badge variant="outline" className="mb-4 sm:mb-6 inline-flex items-center gap-2 border-gray-300 text-gray-700">
          <Sparkles className="h-4 w-4" />
          AI-Powered Video Highlights
        </Badge>
        
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-gray-900 mb-3 sm:mb-4">
          Transform Videos into
          <div className="relative mt-4 max-w-2xl mx-auto">
            {/* Liquid Glass Container */}
            <div className="relative rounded-2xl overflow-hidden backdrop-blur-2xl bg-gradient-to-br from-[#1E201E]/90 via-[#1E201E]/80 to-black/90 border border-white/20 shadow-[0_8px_32px_0_rgba(0,0,0,0.3)]">
              {/* Background pattern for glass effect */}
              <div className="absolute inset-0 bg-gradient-to-r from-black/20 via-gray-900/30 to-black/20"></div>
              
              {/* Animated liquid effect */}
              <div className="absolute inset-0 bg-gradient-to-br from-transparent via-white/5 to-transparent opacity-40"></div>
              
              {/* Shimmer shine effect */}
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent transform -skew-x-12 animate-shimmer"></div>
              
              {/* Inner glow */}
              <div className="absolute inset-[1px] rounded-2xl bg-gradient-to-b from-white/5 to-transparent"></div>
              
              {/* Highlights text */}
              <div className="relative h-full flex items-center justify-center z-10">
                <span className="relative text-3xl sm:text-4xl font-bold inline-block">
                  {/* Main text with liquid glass effect */}
                  <span 
                    className="relative z-10 text-white"
                    style={{
                      textShadow: `
                        0 0 10px rgba(255, 255, 255, 0.5),
                        0 0 20px rgba(255, 255, 255, 0.3),
                        0 0 30px rgba(255, 255, 255, 0.2),
                        0 2px 4px rgba(0, 0, 0, 0.3)
                      `,
                      filter: 'blur(0.5px)',
                      WebkitTextStroke: '0.5px rgba(255, 255, 255, 0.3)'
                    }}
                  >
                    Highlights
                  </span>
                  {/* Animated glass shine overlay */}
                  <span 
                    className="absolute inset-0 text-white/60 pointer-events-none overflow-hidden"
                    style={{
                      background: 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent)',
                      backgroundClip: 'text',
                      WebkitBackgroundClip: 'text',
                      WebkitTextFillColor: 'transparent',
                      transform: 'skewX(-12deg)',
                      animation: 'shimmer 3s infinite'
                    }}
                  >
                    Highlights
                  </span>
                  {/* Glow layer behind text */}
                  <span 
                    className="absolute inset-0 text-white/20 blur-md -z-10"
                  >
                    Highlights
                  </span>
                </span>
              </div>
            </div>
          </div>
        </h1>

        <p className="text-base sm:text-lg text-gray-600 mb-4 sm:mb-6 max-w-2xl mx-auto">
          Paste any YouTube URL and let our advanced AI extract the most
          <br className="hidden sm:block" />
          engaging moments in seconds. Perfect for creating Shorts, Reels, and TikToks.
        </p>

        {/* URL Input */}
        <form onSubmit={handleSubmit} className="max-w-2xl mx-auto mb-3 sm:mb-4">
          <div className="flex flex-col sm:flex-row gap-3 p-1 bg-gray-50 rounded-xl border border-gray-200">
            <Input
              type="url"
              placeholder="https://youtube.com/watch?v=..."
              value={youtubeUrl}
              onChange={(e) => setYoutubeUrl(e.target.value)}
              required
              className="flex-1 border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0"
            />
            <Button 
              type="submit" 
              disabled={!youtubeUrl} 
              className="bg-[#1E201E] hover:bg-[#1E201E]/90 text-white whitespace-nowrap"
            >
              <Sparkles className="h-4 w-4" />
              Generate
              <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </form>

        {error && (
          <Alert variant="destructive" className="max-w-2xl mx-auto mb-3 sm:mb-4 border-red-200 bg-red-50">
            <AlertDescription className="text-red-800">{error}</AlertDescription>
          </Alert>
        )}

        <div className="flex items-center justify-center gap-2 text-xs sm:text-sm text-gray-500 mb-3 sm:mb-4">
          <div className="text-green-600 font-bold">✓</div>
          <span>No credit card required • Free trial available</span>
        </div>

        {/* Feature Highlights */}
        <div className="flex flex-wrap items-center justify-center gap-4 sm:gap-6">
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