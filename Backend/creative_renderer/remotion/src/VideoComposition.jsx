import React from 'react';
import {AbsoluteFill, OffthreadVideo, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

export const CreativeVideo = ({videoPath, title}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const intro = spring({frame, fps, config: {damping: 150, stiffness: 120}});
  const outro = interpolate(frame, [durationInFrames - 36, durationInFrames], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const sparkle = Math.sin(frame / 10) * 8;
  return <AbsoluteFill style={{backgroundColor: '#070b16'}}>
    <OffthreadVideo src={videoPath} />
    <AbsoluteFill style={{pointerEvents: 'none', opacity: outro}}>
      <div style={{position: 'absolute', left: 34, top: 34, width: 118, height: 118, border: '4px solid rgba(255,255,255,.82)', borderRight: 0, borderBottom: 0, borderRadius: 18}} />
      <div style={{position: 'absolute', right: 34, bottom: 34, width: 118, height: 118, border: '4px solid rgba(255,216,77,.92)', borderLeft: 0, borderTop: 0, borderRadius: 18}} />
      <div style={{position: 'absolute', right: 68, top: 84 + sparkle, color: '#ffd84d', fontSize: 76, fontWeight: 800, transform: `rotate(${8 + sparkle / 8}deg)`, textShadow: '0 3px 18px rgba(0,0,0,.42)'}}>✦</div>
      <div style={{position: 'absolute', left: 54, bottom: 62, opacity: intro, transform: `translateY(${(1 - intro) * 26}px)`, maxWidth: 610, color: 'white', fontFamily: 'Arial, sans-serif', fontSize: 22, fontWeight: 700, letterSpacing: 2, textTransform: 'uppercase', textShadow: '0 2px 14px rgba(0,0,0,.5)'}}>{title}</div>
    </AbsoluteFill>
  </AbsoluteFill>;
};
