import React from 'react';

const SpaceBackground = ({ children }) => {
  return (
    <div className="relative min-h-screen w-full bg-[#06080D] overflow-hidden flex items-center justify-center font-sans">
      {/* Volumetric Light Ray from top */}
      <div className="absolute inset-0 volumetric-light z-0 pointer-events-none" />
      
      {/* Deep Space Stars */}
      <div className="absolute inset-0 z-0 opacity-20 pointer-events-none" style={{
        backgroundImage: 'radial-gradient(circle, #ffffff 1px, transparent 1px)',
        backgroundSize: '120px 120px',
        backgroundPosition: '0 0, 60px 60px'
      }} />

      {/* HUD Elements */}
      <div className="hud-corner hud-tl pointer-events-none z-10" />
      <div className="hud-corner hud-tr pointer-events-none z-10" />
      <div className="hud-corner hud-bl pointer-events-none z-10" />
      <div className="hud-corner hud-br pointer-events-none z-10" />

      {/* Decorative Crosshairs */}
      <div className="crosshair pointer-events-none z-10" style={{ top: '25%', left: '20%' }} />
      <div className="crosshair pointer-events-none z-10" style={{ top: '75%', right: '25%' }} />
      <div className="crosshair pointer-events-none z-10" style={{ top: '15%', right: '15%' }} />
      
      {/* Coordinates text (decorative) */}
      <div className="absolute bottom-10 right-12 text-[10px] tracking-[0.2em] text-white/30 uppercase pointer-events-none">
        System <br/>
        <span className="text-white/80">Online</span>
      </div>

      {/* Content wrapper */}
      <div className="relative z-20 w-full h-full flex items-center justify-center perspective-1000">
        {children}
      </div>
    </div>
  );
};

export default SpaceBackground;
