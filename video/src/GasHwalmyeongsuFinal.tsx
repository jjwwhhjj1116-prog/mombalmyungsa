import React from 'react';
import {AbsoluteFill, Audio, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import semantic from './data/gas-hwalmyeongsu-v6-semantic.json';
import timeline from './data/gas-hwalmyeongsu-v6-timeline.json';
import {GasHwalmyeongsuRoughCut} from './GasHwalmyeongsuRoughCut';
import {theme} from './theme';

type CaptionPage = (typeof semantic.caption_pages)[number];
type SemanticEvent = (typeof semantic.semantic_events)[number];

const fontFamily = 'Gmarket Sans Bold';

const FontContract: React.FC = () => (
  <style>{`@font-face{font-family:'Gmarket Sans Bold';src:url('${staticFile('fonts/GmarketSansTTFBold.ttf')}') format('truetype');font-weight:700;font-style:normal;}`}</style>
);

const CaptionWord: React.FC<{token: CaptionPage['tokens'][number]; active: boolean}> = ({token, active}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const enter = spring({frame: frame - token.start_frame, fps, config: {damping: 15, mass: 0.55, stiffness: 210}});
  const scale = interpolate(enter, [0, 1], [0.84, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  return (
    <span
      style={{
        display: 'inline-block',
        margin: '0 12px',
        color: active ? '#FFD21F' : '#FFFFFF',
        opacity: interpolate(enter, [0, 1], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}),
        transform: `scale(${scale})`,
        transformOrigin: '50% 72%',
        WebkitTextStroke: '30px #000000',
        paintOrder: 'stroke fill',
        textShadow: '0 12px 18px rgba(0,0,0,0.78)',
      }}
    >
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
    <div
      style={{
        position: 'absolute',
        left: 540,
        top: 1200,
        width: 980,
        transform: 'translate(-50%, -50%)',
        textAlign: 'center',
        fontFamily,
        fontSize: 100,
        fontWeight: 700,
        lineHeight: 1.12,
        letterSpacing: '-0.045em',
        zIndex: 90,
      }}
    >
      {lineCounts.map((count, lineIndex) => {
        const tokens = page.tokens.slice(cursor, cursor + count);
        cursor += count;
        return (
          <div key={`${page.page_id}-line-${lineIndex}`} style={{whiteSpace: 'nowrap'}}>
            {tokens.map((token) => (
              <CaptionWord key={`${page.page_id}-${token.start_frame}-${token.text}`} token={token} active={frame >= token.start_frame && frame <= token.end_frame} />
            ))}
          </div>
        );
      })}
    </div>
  );
};

const EventShell: React.FC<{event: SemanticEvent; children: React.ReactNode}> = ({event, children}) => {
  const frame = useCurrentFrame();
  const progress = interpolate(frame, [event.start_frame, Math.min(event.start_frame + 8, event.end_frame), event.end_frame], [0, 1, 1], {
    easing: theme.ease.out,
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  return (
    <AbsoluteFill style={{pointerEvents: 'none', opacity: progress, zIndex: 55}}>
      {children}
    </AbsoluteFill>
  );
};

const BrassLabel: React.FC<{text: string; top?: number; size?: number}> = ({text, top = 250, size = 78}) => (
  <div
    style={{
      position: 'absolute',
      left: '50%',
      top,
      transform: 'translateX(-50%)',
      padding: '20px 34px 14px',
      borderRadius: 12,
      border: `4px solid ${theme.colors.brass}`,
      background: 'rgba(25,16,10,0.88)',
      color: '#FFF7E7',
      fontFamily,
      fontSize: size,
      fontWeight: 700,
      letterSpacing: '-0.04em',
      boxShadow: '0 18px 40px rgba(0,0,0,0.36)',
      whiteSpace: 'nowrap',
    }}
  >
    {text}
  </div>
);

const Vapor: React.FC = () => {
  const frame = useCurrentFrame();
  const rise = (frame % 24) * 4;
  return (
    <svg width="1080" height="1920" viewBox="0 0 1080 1920" style={{position: 'absolute', inset: 0}}>
      {[0, 1, 2].map((index) => (
        <path
          key={index}
          d={`M ${460 + index * 70} ${760 - rise} C ${405 + index * 80} ${665 - rise}, ${595 - index * 35} ${590 - rise}, ${500 + index * 45} ${485 - rise}`}
          fill="none"
          stroke="rgba(255,247,225,0.82)"
          strokeWidth={13 - index * 2}
          strokeLinecap="round"
          filter="blur(2px)"
        />
      ))}
    </svg>
  );
};

const Bubbles: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill>
      {[0, 1, 2, 3, 4, 5].map((index) => {
        const y = 1120 - ((frame * (8 + index) + index * 170) % 760);
        const x = 410 + ((index * 83) % 290);
        const size = 28 + (index % 3) * 18;
        return <div key={index} style={{position: 'absolute', left: x, top: y, width: size, height: size, borderRadius: '50%', border: `6px solid ${theme.colors.brass}`, background: 'rgba(255,220,125,0.12)', boxShadow: 'inset 0 0 16px rgba(255,255,255,0.55)'}} />;
      })}
    </AbsoluteFill>
  );
};

const SemanticGraphic: React.FC<{event: SemanticEvent}> = ({event}) => {
  switch (event.kind) {
    case 'question_focus':
      return <EventShell event={event}><BrassLabel text="왜 이 소리가 날까?" /></EventShell>;
    case 'hiss_hit':
    case 'hiss_return':
      return <EventShell event={event}><Vapor /></EventShell>;
    case 'time_gap':
      return <EventShell event={event}><BrassLabel text="1897  →  약 70년  →  1967" size={67} /></EventShell>;
    case 'dilemma':
      return <EventShell event={event}><div style={{position: 'absolute', top: 260, left: 70, color: '#FFF', fontFamily, fontSize: 72, padding: 22, background: 'rgba(91,31,20,.88)', border: '4px solid #D47A55'}}>아픈 사람</div><div style={{position: 'absolute', top: 260, right: 70, color: '#FFF', fontFamily, fontSize: 72, padding: 22, background: 'rgba(25,67,69,.9)', border: `4px solid ${theme.colors.teal}`}}>느린 약</div></EventShell>;
    case 'identity':
      return <EventShell event={event}><BrassLabel text="궁중 선전관  민병호" /></EventShell>;
    case 'mechanism':
      return <EventShell event={event}><svg width="1080" height="1920"><path d="M540 350 C420 560 660 720 540 940" fill="none" stroke="#FFD36E" strokeWidth="18" strokeLinecap="round" strokeDasharray="30 24" /></svg></EventShell>;
    case 'ingredients':
      return <EventShell event={event}><div style={{position: 'absolute', top: 245, left: 95, right: 95, display: 'flex', justifyContent: 'space-between'}}>{['아선약', '정향', '멘톨'].map((label) => <div key={label} style={{width: 250, padding: '24px 0 18px', textAlign: 'center', borderRadius: 999, background: 'rgba(29,20,12,.9)', border: `5px solid ${theme.colors.brass}`, color: '#FFF7E7', fontFamily, fontSize: 62}}>{label}</div>)}</div></EventShell>;
    case 'evidence':
      return <EventShell event={event}><BrassLabel text="유사 제품  약 60종" size={92} /></EventShell>;
    case 'era_shift':
      return <EventShell event={event}><BrassLabel text="1960년대 중반" size={92} /></EventShell>;
    case 'principle':
      return <EventShell event={event}><Bubbles /><BrassLabel text="탄산가스  →  청량감" size={70} /></EventShell>;
    case 'taste_hit':
      return <EventShell event={event}><div style={{position: 'absolute', left: 540, top: 620, width: 260, height: 260, transform: 'translate(-50%,-50%)', borderRadius: '50%', border: `16px solid ${theme.colors.brass}`, display: 'grid', placeItems: 'center', color: '#FFF', fontFamily, fontSize: 120, textShadow: '0 8px 20px #000'}}>톡</div></EventShell>;
    case 'sensory_bridge':
      return <EventShell event={event}><BrassLabel text="귀  ↔  혀" size={105} /></EventShell>;
    case 'double_change':
      return <EventShell event={event}><BrassLabel text="두 번의 변화" size={105} /></EventShell>;
    case 'closing':
      return <EventShell event={event}><BrassLabel text="까스활명수의 탄생" size={82} /></EventShell>;
    default:
      return null;
  }
};

const SemanticLayer: React.FC = () => {
  const frame = useCurrentFrame();
  return <>{semantic.semantic_events.filter((event) => frame >= event.start_frame && frame <= event.end_frame).map((event) => <SemanticGraphic key={event.event_id} event={event} />)}</>;
};

const SoundLayer: React.FC = () => (
  <>
    {semantic.semantic_events.filter((event) => event.sound_asset).map((event) => {
      const from = Math.max(0, event.start_frame - event.sound_lead_frames);
      return (
        <Sequence key={`snd-${event.event_id}`} from={from} durationInFrames={30} premountFor={8}>
          <Audio src={staticFile(`sfx/${event.sound_asset}`)} volume={event.kind.includes('hiss') ? 0.22 : 0.14} />
        </Sequence>
      );
    })}
  </>
);

export const GasHwalmyeongsuFinal: React.FC = () => (
  <AbsoluteFill style={{backgroundColor: theme.colors.bg}}>
    <FontContract />
    <GasHwalmyeongsuRoughCut />
    <SemanticLayer />
    <CaptionTrack />
    <SoundLayer />
  </AbsoluteFill>
);
