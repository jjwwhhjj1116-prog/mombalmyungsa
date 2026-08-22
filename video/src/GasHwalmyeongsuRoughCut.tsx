import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Img,
  OffthreadVideo,
  Sequence,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import timeline from './data/gas-hwalmyeongsu-v6-timeline.json';
import {theme} from './theme';

type Scene = (typeof timeline.scenes)[number];

const BgMesh: React.FC = () => {
  const frame = useCurrentFrame();
  const d1 = Math.sin(frame / 55) * 50;
  const d2 = Math.cos(frame / 70) * 40;
  return (
    <AbsoluteFill style={{background: theme.colors.bg}}>
      <div style={{position: 'absolute', width: 1200, height: 1200, borderRadius: '50%', top: -450, left: -300 + d1, filter: 'blur(50px)', background: `radial-gradient(circle, ${theme.colors.amber}33, transparent 62%)`}} />
      <div style={{position: 'absolute', width: 900, height: 900, borderRadius: '50%', bottom: -400, right: -250 - d2, filter: 'blur(70px)', background: `radial-gradient(circle, ${theme.colors.teal}22, transparent 65%)`}} />
    </AbsoluteFill>
  );
};

const Grade: React.FC = () => (
  <AbsoluteFill style={{pointerEvents: 'none'}}>
    <AbsoluteFill style={{backgroundColor: theme.colors.amber, mixBlendMode: 'soft-light', opacity: 0.12}} />
    <AbsoluteFill style={{background: 'linear-gradient(180deg, rgba(0,0,0,0.10), transparent 28%, transparent 72%, rgba(0,0,0,0.22))'}} />
  </AbsoluteFill>
);

const Grain: React.FC = () => {
  const frame = useCurrentFrame();
  const noise = `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='220' height='220'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/%3E%3C/filter%3E%3Crect width='220' height='220' filter='url(%23n)' opacity='0.5'/%3E%3C/svg%3E")`;
  return <AbsoluteFill style={{pointerEvents: 'none', backgroundImage: noise, backgroundSize: '220px', backgroundPosition: `${(frame * 7) % 220}px ${(frame * 13) % 220}px`, opacity: 0.045, mixBlendMode: 'overlay'}} />;
};

const Vignette: React.FC = () => (
  <AbsoluteFill style={{pointerEvents: 'none', background: 'radial-gradient(ellipse at center, transparent 56%, rgba(0,0,0,0.25) 100%)'}} />
);

const U12ShelfRepair: React.FC<{scene: Scene}> = ({scene}) => {
  if (!scene.u12_release_blocking_mask) return null;
  const opacity = 1;
  const blankShelfSign = (left: number, top: number, width: number, height: number, rotate: number) => (
    <div
      style={{
        position: 'absolute',
        left,
        top,
        width,
        height,
        opacity,
        transform: `rotate(${rotate}deg)`,
        transformOrigin: '50% 50%',
        borderRadius: 7,
        border: '2px solid rgba(44, 79, 81, 0.55)',
        background: 'linear-gradient(180deg, #0b8584 0 24px, #e4e8e2 24px 100%)',
        boxShadow: '0 8px 22px rgba(7, 27, 30, 0.24)',
      }}
    />
  );
  return (
    <AbsoluteFill style={{pointerEvents: 'none'}}>
      {blankShelfSign(-22, 100, 285, 146, -1.4)}
      {blankShelfSign(312, 82, 455, 150, 0.3)}
      {blankShelfSign(858, 95, 250, 150, 1.5)}
    </AbsoluteFill>
  );
};

const SceneVideo: React.FC<{scene: Scene}> = ({scene}) => {
  const {fps} = useVideoConfig();
  const localFrame = useCurrentFrame();
  const firstVideoFrame = scene.sentence_id === 's01' ? timeline.frame_zero_frames : 0;
  return (
    <AbsoluteFill style={{overflow: 'hidden', backgroundColor: theme.colors.bg}}>
      {scene.sentence_id === 's01' && localFrame < timeline.frame_zero_frames ? (
        <Img src={staticFile('gas/frame-zero-v20-owner-red-box-final.png')} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
      ) : (
        <AbsoluteFill>
          <OffthreadVideo
            src={staticFile(scene.public_source)}
            startFrom={Math.round(scene.source_in * fps)}
            playbackRate={scene.playback_rate}
            volume={0}
            style={{width: '100%', height: '100%', objectFit: 'cover'}}
          />
        </AbsoluteFill>
      )}
      <U12ShelfRepair scene={scene} />
    </AbsoluteFill>
  );
};

export const GasHwalmyeongsuRoughCut: React.FC = () => {
  return (
    <AbsoluteFill style={{backgroundColor: theme.colors.bg}}>
      <BgMesh />
      {timeline.scenes.map((scene) => (
        <Sequence key={scene.sentence_id} from={scene.start_frame} durationInFrames={scene.display_end_frame - scene.start_frame} premountFor={30}>
          <SceneVideo scene={scene} />
        </Sequence>
      ))}
      <Audio src={staticFile('gas/gas-hwalmyeongsu-v6-elevenlabs-take2.mp3')} />
      <Grade />
      <Grain />
      <Vignette />
    </AbsoluteFill>
  );
};
