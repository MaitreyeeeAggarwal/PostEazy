import React from 'react';
import { motion, useTransform, useSpring } from 'framer-motion';

const FloatingCard = ({ 
  title, 
  description, 
  imageUrl, 
  mouseX, 
  mouseY, 
  xOffset, 
  yOffset, 
  zIndex, 
  isFocused, 
  isProcessing,
  onClick 
}) => {
  // If focused, it overrides everything to move to center stage
  const isBackground = !isFocused && zIndex < 15;
  const scaleMultiplier = isFocused ? 2.2 : (isBackground ? 0.7 : 1);
  const blurAmount = isFocused ? 'blur(0px)' : (isBackground ? 'blur(4px)' : 'blur(0px)');
  const opacityAmount = isFocused ? 1 : (isBackground ? 0.6 : 0.9);
  
  const parallaxFactor = zIndex * 2; 

  const rotateX = useTransform(mouseY, [0, window.innerHeight || 1000], [25, -25]);
  const rotateY = useTransform(mouseX, [0, window.innerWidth || 1000], [-25, 25]);
  
  const moveX = useTransform(mouseX, [0, window.innerWidth], [-parallaxFactor, parallaxFactor]);
  const moveY = useTransform(mouseY, [0, window.innerHeight], [-parallaxFactor, parallaxFactor]);

  const springConfig = { damping: 25, stiffness: 80 };
  const smoothRotateX = useSpring(rotateX, springConfig);
  const smoothRotateY = useSpring(rotateY, springConfig);
  const smoothMoveX = useSpring(moveX, springConfig);
  const smoothMoveY = useSpring(moveY, springConfig);

  const floatAnimation = isFocused ? {
    left: '50%',
    top: '20%',
    x: '-50%',
    y: '-50%',
    rotateX: 0,
    rotateY: 0,
    scale: 2.2,
    filter: 'blur(0px)',
    opacity: 1,
    zIndex: 100,
    transition: { type: 'spring', damping: 25, stiffness: 120 }
  } : {
    left: `calc(50% + ${xOffset}px)`,
    top: `calc(50% + ${yOffset}px)`,
    scale: scaleMultiplier,
    filter: blurAmount,
    opacity: opacityAmount,
    zIndex: zIndex,
    y: [0, -15, 0],
    transition: {
      y: {
        duration: 4 + (zIndex % 3),
        repeat: Infinity,
        ease: "easeInOut"
      },
      default: { type: 'spring', damping: 25, stiffness: 120 }
    }
  };

  return (
    <motion.div
      onClick={!isFocused ? onClick : undefined}
      animate={floatAnimation}
      style={isFocused ? { position: 'absolute' } : {
        position: 'absolute',
        x: smoothMoveX,
        y: smoothMoveY,
        rotateX: smoothRotateX,
        rotateY: smoothRotateY,
      }}
      whileHover={!isFocused ? { scale: scaleMultiplier * 1.1, opacity: 1, filter: 'blur(0px)', zIndex: 100 } : {}}
      whileTap={!isFocused ? { scale: scaleMultiplier * 0.95 } : {}}
      className={`group preserve-3d cursor-pointer rounded-xl overflow-hidden border transition-all duration-500 ${
        isFocused 
          ? (isProcessing 
              ? 'border-blue-400 shadow-[0_0_50px_rgba(59,130,246,0.8)]' 
              : 'border-blue-500 shadow-[0_0_30px_rgba(59,130,246,0.3)]') 
          : 'border-white/10 hover:border-white/30'
      }`}
    >
      <div className={`relative w-72 h-44 bg-black transition-all duration-500 ${isProcessing ? 'animate-pulse' : ''}`}>
        <img 
          src={imageUrl} 
          alt={title}
          className={`w-full h-full object-cover transition-opacity duration-300 ${isFocused ? 'opacity-100' : 'opacity-70 group-hover:opacity-100'}`}
        />
        
        <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/40 to-transparent" />
        
        <div className="absolute bottom-0 left-0 p-4 w-full translate-z-10">
          <h3 className={`text-sm font-bold tracking-wider uppercase mb-1 ${isFocused ? 'text-accent' : 'text-white'}`}>
            {title}
          </h3>
          <p className={`text-[10px] text-gray-400 leading-tight transition-opacity duration-300 ${isFocused ? 'opacity-100' : 'opacity-0 group-hover:opacity-100 delay-100'}`}>
            {description}
          </p>
        </div>

        {isProcessing && (
          <div className="absolute inset-0 bg-blue-500/20 backdrop-blur-[2px] flex items-center justify-center">
            <div className="w-8 h-8 border-2 border-white border-t-transparent rounded-full animate-spin" />
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default FloatingCard;
