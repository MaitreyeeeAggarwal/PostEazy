import React from 'react';
import {Composition} from 'remotion';
import {CreativeVideo} from './VideoComposition.jsx';

export const RemotionRoot = () => (
  <Composition id="creative-video" component={CreativeVideo} width={1080} height={1920} fps={30} durationInFrames={900} defaultProps={{videoPath: '', title: 'PostEazy'}} />
);
