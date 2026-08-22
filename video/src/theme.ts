import {Easing} from 'remotion';

export const theme = {
  colors: {
    bg: '#130d08',
    walnut: '#2b1b11',
    brass: '#d7a44d',
    amber: '#b8661d',
    teal: '#2b7773',
    ink: '#f4e9da',
  },
  ease: {
    in: Easing.bezier(0.55, 0.055, 0.675, 0.19),
    out: Easing.bezier(0.215, 0.61, 0.355, 1),
    inOut: Easing.bezier(0.645, 0.045, 0.355, 1),
  },
} as const;
