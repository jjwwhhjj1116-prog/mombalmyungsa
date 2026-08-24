import React from 'react';
import {Composition} from 'remotion';
import timeline from './data/gas-hwalmyeongsu-v6-timeline.json';
import {GasHwalmyeongsuFinal} from './GasHwalmyeongsuFinal';
import {GasHwalmyeongsuRoughCut} from './GasHwalmyeongsuRoughCut';
import blackDeathTimeline from './data/black-death-v1-timeline.json';
import {BlackDeathFinal} from './BlackDeathFinal';

export const Root: React.FC = () => {
  return (
    <>
      <Composition
        id="GasHwalmyeongsuRough"
        component={GasHwalmyeongsuRoughCut}
        durationInFrames={timeline.total_frames}
        fps={timeline.fps}
        width={1080}
        height={1920}
      />
      <Composition
        id="GasHwalmyeongsuFinal"
        component={GasHwalmyeongsuFinal}
        durationInFrames={timeline.total_frames}
        fps={timeline.fps}
        width={1080}
        height={1920}
      />
      <Composition
        id="BlackDeathFinal"
        component={BlackDeathFinal}
        durationInFrames={blackDeathTimeline.total_frames}
        fps={blackDeathTimeline.fps}
        width={blackDeathTimeline.width}
        height={blackDeathTimeline.height}
      />
    </>
  );
};
