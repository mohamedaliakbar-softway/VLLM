import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Landing from './pages/Landing';
import Editor from './pages/Editor';
import Dashboard from './pages/Dashboard';
import VideoEditor from './pages/VideoEditor';
import './App.css';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/editor" element={<Editor />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/video-editor" element={<VideoEditor />} />
      </Routes>
    </Router>
  );
}

export default App;
