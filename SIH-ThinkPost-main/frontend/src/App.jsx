import React, { useState, useEffect } from 'react';
import { useMotionValue, motion, useTransform, useSpring, AnimatePresence } from 'framer-motion';
import { X, CheckCircle2 } from 'lucide-react';
import SpaceBackground from './components/SpaceBackground';
import FloatingCard from './components/FloatingCard';
import TransformationEngine from './components/TransformationEngine';

// Local image mockups to be placed in frontend/public/mockups/
const FORMATS = [
  { id: 'linkedin', title: 'LinkedIn Post', desc: 'Professional post preview layout', img: '/mockups/linkedin.jpg', x: -350, y: -250, z: 20 },
  { id: 'twitter', title: 'X/Twitter Thread', desc: 'Multiple connected posts', img: '/mockups/twitter.jpg', x: 250, y: -300, z: 12 },
  { id: 'presentation', title: 'Presentation Slide', desc: 'Clean title & data slide', img: '/mockups/presentation.png', x: -500, y: 50, z: 10 },
  { id: 'executive', title: 'Exec Summary', desc: 'One-page briefing document', img: '/mockups/executive.png', x: 450, y: 100, z: 18 },
  { id: 'advisory', title: 'Advisory Doc', desc: 'Structured warning/report', img: '/mockups/advisory.png', x: -200, y: 250, z: 15 },
  { id: 'infographic', title: 'Infographic', desc: 'Stats, icons & key points', img: '/mockups/infographic.png', x: 200, y: 280, z: 22 },
  { id: 'storyboard', title: 'Video Storyboard', desc: 'Scene thumbnail + narration', img: '/mockups/storyboard.png', x: 0, y: -350, z: 8 },
  { id: 'youtube', title: 'YouTube Preview', desc: 'Thumbnail, title & captions', img: '/mockups/youtube.png', x: 550, y: -150, z: 10 },
  { id: 'instagram', title: 'Instagram Post', desc: 'Visual communication output', img: '/mockups/instagram.png', x: -600, y: -100, z: 8 },
  { id: 'email', title: 'Email Newsletter', desc: 'Subject, headline, body', img: '/mockups/email.png', x: -100, y: 380, z: 12 },
  { id: 'press', title: 'Press Release', desc: 'Headline + summary article', img: '/mockups/press.png', x: 600, y: 250, z: 9 },
  { id: 'research', title: 'Research Report', desc: 'Chart + highlighted findings', img: '/mockups/research.png', x: -400, y: 300, z: 14 },
  { id: 'mobile', title: 'Mobile Notification', desc: 'Short urgent update card', img: '/mockups/mobile.png', x: 350, y: -50, z: 25 },
  { id: 'blog', title: 'Blog Article', desc: 'Hero image + text structure', img: '/mockups/blog.png', x: -250, y: -80, z: 28 },
  { id: 'analytics', title: 'Analytics Card', desc: 'Visual summary of insights', img: '/mockups/analytics.png', x: 150, y: 120, z: 30 },
];

function App() {
  const [focusedFormat, setFocusedFormat] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [results, setResults] = useState(null);

  // Mouse tracking for parallax
  const mouseX = useMotionValue(typeof window !== 'undefined' ? window.innerWidth / 2 : 0);
  const mouseY = useMotionValue(typeof window !== 'undefined' ? window.innerHeight / 2 : 0);

  // Global camera pan
  const globalPanX = useTransform(mouseX, [0, window.innerWidth || 1000], [400, -400]);
  const globalPanY = useTransform(mouseY, [0, window.innerHeight || 1000], [300, -300]);
  const smoothGlobalPanX = useSpring(globalPanX, { damping: 30, stiffness: 60 });
  const smoothGlobalPanY = useSpring(globalPanY, { damping: 30, stiffness: 60 });

  const handleMouseMove = (e) => {
    // Only pan if we are not focused on a card
    if (!focusedFormat) {
      mouseX.set(e.clientX);
      mouseY.set(e.clientY);
    }
  };

  useEffect(() => {
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [focusedFormat]);

  const handleFocus = (formatId) => {
    setFocusedFormat(formatId);
    setResults(null);
    setIsProcessing(false);
    // Center the mouse so the camera stops panning wildly when focused
    mouseX.set(window.innerWidth / 2);
    mouseY.set(window.innerHeight / 2);
  };

  const handleCancel = () => {
    setFocusedFormat(null);
    setResults(null);
    setIsProcessing(false);
  };

  const handleGenerate = async (payload) => {
    setIsProcessing(true);
    
    try {
      const activeFormatData = FORMATS.find(f => f.id === focusedFormat);
      
      const formData = new FormData();
      
      // Construct the config exactly as the backend expects
      const config = {
        textContext: payload.text || "",
        tone: payload.options?.tone || "Professional",
        targetAudience: payload.options?.audience || "General Public",
        outputFormats: [activeFormatData.title]
      };
      
      formData.append('config', JSON.stringify(config));
      
      if (payload.file) {
        formData.append('files', payload.file);
      }

      const response = await fetch('http://localhost:5000/api/transform', {
        method: 'POST',
        body: formData,
      });

      const json = await response.json();

      if (!response.ok) {
        throw new Error(json.error || 'Transformation failed');
      }
      
      // The backend returns an object where keys are format names and values are the generated text
      if (json.success && json.data) {
        const generatedContents = Object.values(json.data);
        if (generatedContents.length > 0) {
          setResults(generatedContents[0]);
        } else {
          setResults("Error: No content generated.");
        }
      } else {
        setResults("Error: No content generated.");
      }
    } catch (error) {
      console.error(error);
      setResults(`Error: ${error.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const activeFormatData = FORMATS.find(f => f.id === focusedFormat);

  return (
    <SpaceBackground>
      {/* 3D Floating Cards Layer - Global Panning */}
      <motion.div 
        className="absolute inset-0 z-10" 
        style={{ x: smoothGlobalPanX, y: smoothGlobalPanY }}
      >
        {FORMATS.map((f) => (
          <FloatingCard
            key={f.id}
            title={f.title}
            description={f.desc}
            imageUrl={f.img}
            mouseX={mouseX}
            mouseY={mouseY}
            xOffset={f.x}
            yOffset={f.y}
            zIndex={f.z}
            isFocused={focusedFormat === f.id}
            isProcessing={isProcessing && focusedFormat === f.id}
            onClick={() => handleFocus(f.id)}
          />
        ))}
      </motion.div>

      {/* Central Typography - Hidden when focused */}
      <AnimatePresence>
        {!focusedFormat && (
          <motion.div 
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9, filter: 'blur(10px)' }}
            transition={{ duration: 0.5 }}
            className="relative z-50 flex flex-col items-center justify-center text-center pointer-events-none"
          >
            <div className="text-[10px] tracking-[0.5em] text-white/50 mb-4 uppercase">System Identity</div>
            <h1 className="text-5xl md:text-7xl font-black text-white uppercase tracking-tighter leading-none mix-blend-screen">
              Crafting Next-Gen<br />
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-white to-white/40">
                Content Engines
              </span>
            </h1>
            <p className="mt-6 text-sm text-gray-400 tracking-[0.2em] uppercase">
              Transformation • Architecture • Generation
            </p>
            <p className="mt-12 text-xs text-accent tracking-[0.3em] uppercase animate-pulse">
              Select a format to initialize
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Focus Mode Form */}
      <AnimatePresence>
        {focusedFormat && !results && (
          <TransformationEngine 
            focusedFormat={activeFormatData}
            isProcessing={isProcessing}
            onSubmit={handleGenerate}
            onCancel={handleCancel}
          />
        )}
      </AnimatePresence>

      {/* Output Panel (Option A: Slide-out panel) */}
      <AnimatePresence>
        {results && (
          <motion.div
            initial={{ opacity: 0, x: 100, y: '-50%' }}
            animate={{ opacity: 1, x: '10%', y: '-50%' }}
            exit={{ opacity: 0, x: 100, y: '-50%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 120 }}
            className="absolute top-1/2 left-1/2 w-full max-w-lg z-[100]"
          >
            <div className="bg-black/80 backdrop-blur-2xl border border-accent/30 p-8 rounded-2xl shadow-[0_0_50px_rgba(79,70,229,0.2)] relative">
              <button 
                onClick={handleCancel}
                className="absolute top-4 right-4 text-white/40 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>

              <div className="flex items-center gap-3 mb-6 border-b border-white/10 pb-4">
                <CheckCircle2 className="w-6 h-6 text-accent" />
                <div>
                  <h3 className="text-sm tracking-[0.2em] uppercase text-white/60">Transformation Complete</h3>
                  <h2 className="text-xl font-bold text-white capitalize">{activeFormatData?.title}</h2>
                </div>
              </div>

              <div className="prose prose-invert max-w-none">
                <pre className="whitespace-pre-wrap text-gray-300 font-sans text-sm leading-relaxed bg-white/5 p-4 rounded-xl border border-white/10 overflow-y-auto max-h-[50vh]">
                  {results}
                </pre>
              </div>

              <div className="mt-6 flex gap-4">
                <button 
                  onClick={() => setResults(null)}
                  className="flex-1 py-3 rounded-xl border border-white/20 text-white/80 hover:bg-white/5 hover:text-white transition-all text-xs tracking-widest uppercase font-bold"
                >
                  Edit Input
                </button>
                <button 
                  className="flex-1 py-3 rounded-xl bg-accent text-white hover:bg-accent/80 transition-all text-xs tracking-widest uppercase font-bold shadow-lg"
                >
                  Copy to Clipboard
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Global Close Area for Focus Mode */}
      {focusedFormat && !isProcessing && (
        <div 
          className="absolute inset-0 z-0 cursor-zoom-out"
          onClick={handleCancel}
        />
      )}
    </SpaceBackground>
  );
}

export default App;
