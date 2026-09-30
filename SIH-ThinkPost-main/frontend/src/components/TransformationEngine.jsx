import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Upload, FileText, Link as LinkIcon, X, ArrowRight, CloudUpload } from 'lucide-react';

const TransformationEngine = ({ focusedFormat, isProcessing, onSubmit, onCancel }) => {
  const [activeTab, setActiveTab] = useState('upload');
  const [textInput, setTextInput] = useState('');
  const [file, setFile] = useState(null);
  
  const [targetAudience, setTargetAudience] = useState('General');
  const [tone, setTone] = useState('Professional');

  const audiences = ['General', 'Executives', 'Technical', 'Students', 'Marketing', 'Custom'];
  const tones = ['Professional', 'Conversational', 'Informative', 'Persuasive', 'Custom'];

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!textInput && !file) return;
    
    onSubmit({
      text: textInput,
      file: file,
      options: { tone: tone.toLowerCase(), audience: targetAudience.toLowerCase() }
    });
  };

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20, x: '-50%' }}
      animate={{ opacity: 1, y: 0, x: '-50%' }}
      exit={{ opacity: 0, y: 20, x: '-50%' }}
      className="absolute top-[45%] left-1/2 w-full max-w-2xl z-[100]"
    >
      {/* The glowing connection line from the card above */}
      <div className="absolute -top-8 left-1/2 -translate-x-1/2 w-px h-8 bg-blue-500 shadow-[0_0_15px_rgba(59,130,246,1)]" />
      <div className="absolute -top-8 left-1/2 -translate-x-1/2 w-2 h-2 rounded-full bg-blue-400 shadow-[0_0_10px_rgba(59,130,246,1)]" />

      <div className="bg-[#0a0f18] border border-gray-800 p-6 rounded-2xl shadow-2xl relative">
        <button 
          onClick={onCancel}
          className="absolute top-4 right-4 text-gray-500 hover:text-white transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="mb-6">
          <h2 className="text-[10px] tracking-[0.2em] uppercase text-gray-400 mb-1">Configure Output</h2>
          <h3 className="text-xl font-bold text-white capitalize">{focusedFormat?.title || 'Output'}</h3>
          <p className="text-xs text-gray-500 mt-1">Add your content source to get started</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          
          {/* Tabs */}
          <div className="flex bg-[#121824] rounded-lg p-1 border border-gray-800">
            <button
              type="button"
              onClick={() => setActiveTab('upload')}
              className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs font-medium rounded-md transition-all ${
                activeTab === 'upload' ? 'bg-[#1a2b4c] text-blue-400 border border-blue-900/50' : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              <Upload className="w-4 h-4" /> Upload File
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('text')}
              className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs font-medium rounded-md transition-all ${
                activeTab === 'text' ? 'bg-[#1a2b4c] text-blue-400 border border-blue-900/50' : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              <FileText className="w-4 h-4" /> Paste Text
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('url')}
              className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs font-medium rounded-md transition-all ${
                activeTab === 'url' ? 'bg-[#1a2b4c] text-blue-400 border border-blue-900/50' : 'text-gray-400 hover:text-gray-200'
              }`}
            >
              <LinkIcon className="w-4 h-4" /> Add URL
            </button>
          </div>

          {/* Input Area */}
          {activeTab === 'upload' ? (
            <label className="flex flex-col items-center justify-center w-full py-8 border border-dashed border-gray-700 rounded-xl cursor-pointer hover:border-blue-500 hover:bg-[#121824] transition-all group">
              <CloudUpload className="w-8 h-8 text-blue-500 mb-3 group-hover:scale-110 transition-transform" />
              <span className="text-sm text-gray-300 font-medium mb-1">
                {file ? file.name : 'Drag & drop your file here'}
              </span>
              <span className="text-xs text-gray-600 mb-4">or</span>
              <div className="px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-full transition-colors">
                Add File
              </div>
              <span className="text-[10px] text-gray-500 mt-4">Supports PDF, DOC, DOCX, TXT (Max 50MB)</span>
              <input 
                type="file" 
                className="hidden" 
                onChange={(e) => setFile(e.target.files[0])}
                disabled={isProcessing}
              />
            </label>
          ) : (
            <textarea
              className="w-full h-32 bg-[#121824] border border-gray-800 rounded-xl p-4 text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 transition-all resize-none text-sm"
              placeholder={activeTab === 'text' ? "Paste raw text or notes here..." : "Paste URL here..."}
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              disabled={isProcessing}
            />
          )}

          {/* Configuration Pills */}
          <div className="flex gap-8">
            <div className="flex-1 space-y-3">
              <label className="text-[10px] font-semibold tracking-widest uppercase text-gray-500 flex items-center gap-2">
                <div className="w-1 h-1 bg-gray-500 rounded-full" /> Target Audience
              </label>
              <div className="flex flex-wrap gap-2">
                {audiences.map(aud => (
                  <button
                    key={aud}
                    type="button"
                    onClick={() => setTargetAudience(aud)}
                    className={`px-3 py-1.5 rounded-full text-[10px] transition-all border ${
                      targetAudience === aud 
                        ? 'bg-[#1a2b4c] border-blue-500 text-blue-400' 
                        : 'bg-transparent border-gray-800 text-gray-400 hover:border-gray-600 hover:text-gray-200'
                    }`}
                  >
                    {aud}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex-1 space-y-3">
              <label className="text-[10px] font-semibold tracking-widest uppercase text-gray-500 flex items-center gap-2">
                <div className="w-1 h-1 bg-blue-500 rounded-full shadow-[0_0_5px_rgba(59,130,246,1)]" /> Tone
              </label>
              <div className="flex flex-wrap gap-2">
                {tones.map(t => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => setTone(t)}
                    className={`px-3 py-1.5 rounded-full text-[10px] transition-all border ${
                      tone === t 
                        ? 'bg-[#1a2b4c] border-blue-500 text-blue-400' 
                        : 'bg-transparent border-gray-800 text-gray-400 hover:border-gray-600 hover:text-gray-200'
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <button
            type="submit"
            disabled={(!textInput && !file) || isProcessing}
            className={`w-full py-3 rounded-lg font-bold text-sm flex items-center justify-center gap-2 transition-all ${
              isProcessing 
                ? 'bg-blue-600/50 text-white/50 cursor-not-allowed' 
                : 'bg-blue-600 text-white hover:bg-blue-500 hover:shadow-[0_0_20px_rgba(37,99,235,0.4)]'
            } ${(!textInput && !file) ? 'opacity-50 cursor-not-allowed' : ''}`}
          >
            {isProcessing ? (
              <>
                <div className="w-4 h-4 border-2 border-white/50 border-t-transparent rounded-full animate-spin" />
                Processing...
              </>
            ) : (
              <>
                <span className="mr-1 mt-0.5">✨</span> Generate {focusedFormat?.title?.split(' ')[0] || 'Content'}
                <ArrowRight className="w-4 h-4 ml-1" />
              </>
            )}
          </button>
        </form>
      </div>
    </motion.div>
  );
};

export default TransformationEngine;
