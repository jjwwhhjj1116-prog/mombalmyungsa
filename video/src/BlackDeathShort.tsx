import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Easing,
  Img,
  OffthreadVideo,
  Sequence,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import short from './data/black-death-v1-short.json';

type Scene = (typeof short.scenes)[number];
type CaptionPage = (typeof short.caption_pages)[number];

const fontFamily = 'Gmarket Sans Bold';
const amber = '#FFD21F';
const ink = '#080909';

const FontContract: React.FC = () => (
  <style>{`@font-face{font-family:'Gmarket Sans Bold';src:url('${staticFile('fonts/GmarketSansTTFBold.ttf')}') format('truetype');font-weight:700;font-style:normal;}`}</style>
);

const SceneVideo: React.FC<{scene: Scene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const duration = Math.max(1, scene.display_end_frame - scene.start_frame);
  const progress = interpolate(frame, [0, duration], [0, 1], {
    easing: Easing.inOut(Easing.cubic),
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const direction = Number(scene.sentence_id.slice(1)) % 2 === 0 ? 1 : -1;
  const x = interpolate(progress, [0, 1], [-18 * direction, 18 * direction]);
  const scale = interpolate(progress, [0, 1], [1.02, 1.08]);
  return (
    <AbsoluteFill style={{overflow: 'hidden', backgroundColor: ink}}>
      <OffthreadVideo
        src={staticFile(scene.public_source)}
        startFrom={Math.round(scene.source_in * short.fps)}
        playbackRate={scene.playback_rate}
        volume={0}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          objectPosition: scene.object_position,
          transform: `translateX(${x}px) scale(${scale})`,
        }}
      />
      <AbsoluteFill style={{background: 'linear-gradient(180deg,rgba(0,0,0,.32),transparent 24%,transparent 67%,rgba(0,0,0,.48))'}} />
      <AbsoluteFill style={{background: 'radial-gradient(ellipse at center,transparent 50%,rgba(0,0,0,.32) 100%)'}} />
    </AbsoluteFill>
  );
};

const CaptionWord: React.FC<{token: CaptionPage['tokens'][number]; active: boolean}> = ({token, active}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({frame: frame - token.start_frame, fps, config: {damping: 18, mass: .48, stiffness: 210}});
  return (
    <span style={{
      display: 'inline-block',
      margin: '0 8px 9px',
      color: active ? amber : '#FFFFFF',
      opacity: interpolate(enter, [0, 1], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
      transform: `scale(${interpolate(enter, [0, 1], [.9, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})})`,
      WebkitTextStroke: '30px #000000',
      paintOrder: 'stroke fill',
      textShadow: '0 14px 22px rgba(0,0,0,.92)',
    }}>{token.text}</span>
  );
};

const CaptionTrack: React.FC = () => {
  const frame = useCurrentFrame();
  if (frame < short.frame_zero_frames) return null;
  const page = short.caption_pages.find((item) => frame >= item.start_frame && frame < item.end_frame);
  if (!page) return null;
  return (
    <div style={{
      position: 'absolute',
      left: 540,
      top: 1200,
      width: 930,
      transform: 'translate(-50%,-50%)',
      padding: '24px 22px 18px',
      borderRadius: 26,
      background: 'linear-gradient(90deg,transparent,rgba(0,0,0,.46) 12%,rgba(0,0,0,.46) 88%,transparent)',
      textAlign: 'center',
      fontFamily,
      fontSize: 100,
      fontWeight: 700,
      lineHeight: 1.08,
      letterSpacing: '-.05em',
      zIndex: 100,
    }}>
      {page.tokens.map((token) => <CaptionWord key={`${page.page_id}-${token.start_frame}-${token.text}`} token={token} active={frame >= token.start_frame && frame <= token.end_frame} />)}
    </div>
  );
};

const TopBeat: React.FC = () => {
  const frame = useCurrentFrame();
  const event = short.semantic_events.find((item) => frame >= item.start_frame && frame <= item.end_frame);
  if (!event) return null;
  const enter = spring({frame: frame - event.start_frame, fps: short.fps, config: {damping: 18, mass: .6, stiffness: 185}});
  return (
    <div style={{
      position: 'absolute',
      left: 540,
      top: 165,
      maxWidth: 920,
      transform: `translate(-50%,${interpolate(enter, [0, 1], [-28, 0])}px)`,
      padding: '18px 26px 13px',
      borderRadius: 14,
      border: '4px solid #D99D36',
      background: 'rgba(10,10,9,.88)',
      color: '#FFF7E7',
      boxShadow: '0 18px 34px rgba(0,0,0,.48)',
      fontFamily,
      fontSize: event.label.length > 18 ? 46 : 58,
      lineHeight: 1.08,
      textAlign: 'center',
      letterSpacing: '-.045em',
      zIndex: 90,
    }}>{event.label}</div>
  );
};

const BrandBug: React.FC = () => (
  <div style={{position: 'absolute', top: 34, left: 34, zIndex: 120, padding: '12px 18px 8px', borderRadius: 8, background: 'rgba(8,9,9,.78)', border: '2px solid rgba(255,255,255,.68)', color: '#FFF', fontFamily, fontSize: 30}}>몸의 발명사</div>
);

export const BlackDeathShort: React.FC = () => (
  <AbsoluteFill style={{backgroundColor: ink}}>
    <FontContract />
    {short.scenes.map((scene) => {
      const duration = scene.display_end_frame - scene.start_frame;
      return (
        <Sequence key={scene.sentence_id} from={scene.start_frame} durationInFrames={duration} premountFor={30}>
          <SceneVideo scene={scene} />
          <Audio
            src={staticFile(short.audio_asset)}
            startFrom={scene.source_master_start_frame}
            endAt={scene.source_master_end_frame}
          />
        </Sequence>
      );
    })}
    <CaptionTrack />
    <TopBeat />
    <BrandBug />
    <Sequence from={0} durationInFrames={short.frame_zero_frames}>
      <Img src={staticFile(short.frame_zero_asset)} style={{width: '100%', height: '100%', objectFit: 'cover', zIndex: 200}} />
    </Sequence>
  </AbsoluteFill>
);
