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
import timeline from './data/black-death-v1-timeline.json';
import semantic from './data/black-death-v1-semantic.json';

type Scene = (typeof timeline.scenes)[number];
type CaptionPage = (typeof semantic.caption_pages)[number];
type SemanticEvent = (typeof semantic.semantic_events)[number];

const fontFamily = 'Gmarket Sans Bold';
const brass = '#D99D36';
const amber = '#FFD21F';
const ivory = '#FFF7E7';
const ink = '#080909';

const FontContract: React.FC = () => (
  <style>{`@font-face{font-family:'Gmarket Sans Bold';src:url('${staticFile('fonts/GmarketSansTTFBold.ttf')}') format('truetype');font-weight:700;font-style:normal;}`}</style>
);

const FilmFinish: React.FC = () => {
  const frame = useCurrentFrame();
  const noise = `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='220' height='220'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.86' numOctaves='2'/%3E%3C/filter%3E%3Crect width='220' height='220' filter='url(%23n)' opacity='.48'/%3E%3C/svg%3E")`;
  return (
    <AbsoluteFill style={{pointerEvents: 'none', zIndex: 70}}>
      <AbsoluteFill style={{background: 'linear-gradient(180deg,rgba(3,7,9,.18),transparent 28%,transparent 72%,rgba(0,0,0,.28))'}} />
      <AbsoluteFill style={{background: 'radial-gradient(ellipse at center,transparent 54%,rgba(0,0,0,.34) 100%)'}} />
      <AbsoluteFill style={{backgroundImage: noise, backgroundPosition: `${frame * 5 % 220}px ${frame * 9 % 220}px`, opacity: 0.038, mixBlendMode: 'overlay'}} />
    </AbsoluteFill>
  );
};

const BacteriaOverlay: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <svg width="1920" height="1080" viewBox="0 0 1920 1080" style={{position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 35}}>
      <defs>
        <filter id="bacteriaGlow"><feGaussianBlur stdDeviation="3" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      </defs>
      {Array.from({length: 24}).map((_, index) => {
        const travel = (frame * (2.2 + (index % 4) * 0.35) + index * 79) % 920;
        const x = 420 + travel;
        const y = 390 + Math.sin((frame + index * 17) / 18) * 95 + (index % 5) * 28;
        const rotate = (index * 31 + frame * 1.3) % 180;
        return <rect key={index} x={x} y={y} width={30 + index % 3 * 8} height={10} rx={5} fill={index % 4 === 0 ? '#F0C25E' : '#7FC5B8'} opacity={0.42 + index % 3 * 0.15} transform={`rotate(${rotate} ${x} ${y})`} filter="url(#bacteriaGlow)" />;
      })}
    </svg>
  );
};

const GeneratedTextMask: React.FC = () => (
  <div style={{position: 'absolute', right: 24, top: 22, width: 560, height: 132, borderRadius: 12, background: 'linear-gradient(145deg,#12110e 0%,#201b13 100%)', border: `3px solid ${brass}`, boxShadow: '0 14px 32px rgba(0,0,0,.55)', zIndex: 42, display: 'grid', placeItems: 'center', color: ivory, fontFamily, fontSize: 48, letterSpacing: '-.04em'}}>
    감염의 길 전체
  </div>
);

const SceneVideo: React.FC<{scene: Scene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const duration = Math.max(1, scene.display_end_frame - scene.start_frame);
  const progress = interpolate(frame, [0, duration], [0, 1], {easing: Easing.inOut(Easing.cubic), extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const drift = Number(scene.sentence_id.slice(1)) % 2 === 0 ? 1 : -1;
  const scale = interpolate(progress, [0, 1], [1.012, 1.036]);
  const x = interpolate(progress, [0, 1], [-8 * drift, 8 * drift]);
  return (
    <AbsoluteFill style={{overflow: 'hidden', backgroundColor: ink}}>
      <OffthreadVideo
        src={staticFile(scene.public_source)}
        startFrom={Math.round(scene.source_in * fps)}
        playbackRate={scene.playback_rate}
        volume={0}
        style={{width: '100%', height: '100%', objectFit: 'cover', transform: `translateX(${x}px) scale(${scale})`}}
      />
      {scene.bacteria_overlay ? <BacteriaOverlay /> : null}
      {scene.generated_text_mask ? <GeneratedTextMask /> : null}
    </AbsoluteFill>
  );
};

const CaptionWord: React.FC<{token: CaptionPage['tokens'][number]; active: boolean}> = ({token, active}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({frame: frame - token.start_frame, fps, config: {damping: 17, mass: 0.48, stiffness: 210}});
  return (
    <span style={{display: 'inline-block', margin: '0 11px', color: active ? amber : '#FFFFFF', opacity: interpolate(enter, [0, 1], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}), transform: `scale(${interpolate(enter, [0, 1], [.9, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})})`, WebkitTextStroke: '20px #000000', paintOrder: 'stroke fill', textShadow: '0 10px 18px rgba(0,0,0,.9)'}}>
      {token.text}
    </span>
  );
};

const CaptionTrack: React.FC = () => {
  const frame = useCurrentFrame();
  if (frame < timeline.frame_zero_frames) return null;
  const page = semantic.caption_pages.find((item) => frame >= item.start_frame && frame < item.end_frame);
  if (!page) return null;
  const lineCounts = page.lines.map((line) => line.trim().split(/\s+/).length);
  let cursor = 0;
  return (
    <div style={{position: 'absolute', left: 960, top: 675, width: 1720, transform: 'translate(-50%,-50%)', padding: '22px 34px 18px', borderRadius: 24, background: 'linear-gradient(90deg,transparent,rgba(0,0,0,.44) 16%,rgba(0,0,0,.44) 84%,transparent)', textAlign: 'center', fontFamily, fontSize: 100, fontWeight: 700, lineHeight: 1.09, letterSpacing: '-.048em', zIndex: 100}}>
      {lineCounts.map((count, lineIndex) => {
        const tokens = page.tokens.slice(cursor, cursor + count);
        cursor += count;
        return <div key={`${page.page_id}-${lineIndex}`} style={{whiteSpace: 'nowrap'}}>{tokens.map((token) => <CaptionWord key={`${page.page_id}-${token.start_frame}-${token.text}`} token={token} active={frame >= token.start_frame && frame <= token.end_frame} />)}</div>;
      })}
    </div>
  );
};

const EventShell: React.FC<{event: SemanticEvent; children: React.ReactNode}> = ({event, children}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({frame: frame - event.start_frame, fps, config: {damping: 18, mass: .65, stiffness: 175}});
  const exit = interpolate(frame, [Math.max(event.start_frame, event.end_frame - 8), event.end_frame], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.in(Easing.cubic)});
  return <AbsoluteFill style={{pointerEvents: 'none', zIndex: 58, opacity: enter * exit, transform: `translateY(${interpolate(enter, [0, 1], [-22, 0])}px)`}}>{children}</AbsoluteFill>;
};

const BrassLabel: React.FC<{text: string; size?: number}> = ({text, size = 64}) => (
  <div style={{position: 'absolute', left: '50%', top: 60, transform: 'translateX(-50%)', padding: '18px 30px 13px', borderRadius: 12, border: `4px solid ${brass}`, background: 'rgba(14,12,9,.9)', boxShadow: '0 16px 34px rgba(0,0,0,.48)', color: ivory, fontFamily, fontWeight: 700, fontSize: size, letterSpacing: '-.045em', whiteSpace: 'nowrap'}}>{text}</div>
);

const BrokenChain: React.FC = () => {
  const frame = useCurrentFrame();
  const gap = Math.min(120, Math.max(0, (frame % 120) * 3));
  return <svg width="1920" height="1080" style={{position: 'absolute', inset: 0}}><path d={`M370 300 C650 220 ${870-gap} 430 ${900-gap} 430`} fill="none" stroke="#CFA25A" strokeWidth="24" strokeDasharray="38 24"/><path d={`M${1020+gap} 430 C1160 430 1320 260 1560 300`} fill="none" stroke="#CFA25A" strokeWidth="24" strokeDasharray="38 24"/><circle cx="960" cy="430" r="42" fill="none" stroke="#F6D37A" strokeWidth="14" opacity=".82"/></svg>;
};

const FiveLayers: React.FC = () => (
  <div style={{position: 'absolute', left: 140, right: 140, top: 72, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12}}>
    {['격리','원인','벼룩','설치류','치료'].map((text, index) => <React.Fragment key={text}><div style={{padding: '16px 22px 12px', borderRadius: 10, color: index === 4 ? '#101010' : ivory, background: index === 4 ? amber : 'rgba(15,14,12,.9)', border: `3px solid ${brass}`, fontFamily, fontSize: 50, boxShadow: '0 12px 26px rgba(0,0,0,.42)'}}>{text}</div>{index < 4 ? <div style={{color: amber, fontFamily, fontSize: 48}}>→</div> : null}</React.Fragment>)}
  </div>
);

const SemanticGraphic: React.FC<{event: SemanticEvent}> = ({event}) => {
  if (event.kind === 'dilemma') return <EventShell event={event}><div style={{position: 'absolute', left: 170, top: 70, padding: '18px 30px', background: 'rgba(70,23,18,.92)', border: '4px solid #CC6E55', borderRadius: 12, color: '#FFF', fontFamily, fontSize: 62}}>도시의 생계</div><div style={{position: 'absolute', right: 170, top: 70, padding: '18px 30px', background: 'rgba(20,55,57,.92)', border: '4px solid #5EA6A2', borderRadius: 12, color: '#FFF', fontFamily, fontSize: 62}}>감염 위험</div></EventShell>;
  if (event.kind === 'question_flip') return <EventShell event={event}><div style={{position: 'absolute', top: 65, left: 245, color: '#BBB', fontFamily, fontSize: 52, textDecoration: 'line-through'}}>아픈 사람만 찾기</div><div style={{position: 'absolute', top: 55, right: 220, color: amber, fontFamily, fontSize: 66}}>멀쩡해 보여도 멈추기</div><div style={{position: 'absolute', top: 58, left: 900, color: amber, fontFamily, fontSize: 64}}>→</div></EventShell>;
  if (event.kind === 'chain_break' || event.kind === 'disconnect') return <EventShell event={event}><BrokenChain/><BrassLabel text={event.label} /></EventShell>;
  if (event.kind === 'five_layers') return <EventShell event={event}><FiveLayers /></EventShell>;
  const size = event.kind === 'death_toll' ? 82 : event.label.length > 24 ? 48 : 64;
  return <EventShell event={event}><BrassLabel text={event.label} size={size} /></EventShell>;
};

const SemanticLayer: React.FC = () => {
  const frame = useCurrentFrame();
  return <>{semantic.semantic_events.filter((event) => frame >= event.start_frame && frame <= event.end_frame).map((event) => <SemanticGraphic key={event.event_id} event={event} />)}</>;
};

const SoundLayer: React.FC = () => (
  <>{semantic.semantic_events.filter((event) => event.sound_asset).map((event) => <Sequence key={`snd-${event.event_id}`} from={Math.max(0, event.start_frame - event.sound_lead_frames)} durationInFrames={30} premountFor={8}><Audio src={staticFile(`sfx/${event.sound_asset}`)} volume={event.kind === 'death_toll' ? .16 : .105} /></Sequence>)}</>
);

const BrandBug: React.FC = () => (
  <div style={{position: 'absolute', top: 28, left: 34, zIndex: 120, padding: '11px 18px 8px', borderRadius: 8, background: 'rgba(8,9,9,.76)', border: '2px solid rgba(255,255,255,.68)', color: '#FFF', fontFamily, fontSize: 30, letterSpacing: '-.04em'}}>몸의 발명사</div>
);

export const BlackDeathFinal: React.FC = () => (
  <AbsoluteFill style={{backgroundColor: ink}}>
    <FontContract />
    {timeline.scenes.map((scene) => <Sequence key={scene.sentence_id} from={scene.start_frame} durationInFrames={scene.display_end_frame - scene.start_frame} premountFor={30}><SceneVideo scene={scene} /></Sequence>)}
    <Audio src={staticFile(timeline.audio_asset)} />
    <FilmFinish />
    <SemanticLayer />
    <CaptionTrack />
    <SoundLayer />
    <BrandBug />
    <Sequence from={0} durationInFrames={timeline.frame_zero_frames}><Img src={staticFile(timeline.frame_zero_asset)} style={{width: '100%', height: '100%', objectFit: 'cover', zIndex: 200}} /></Sequence>
  </AbsoluteFill>
);
