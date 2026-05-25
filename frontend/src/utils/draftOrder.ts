export type DraftMode = 'SOLOQ' | 'CLASH';
export type DraftSide = 'BLUE' | 'RED';

export interface DraftSlot {
  side: DraftSide;
  isBan: boolean;
  position: number;
}

const SIDES = {
  B: 'BLUE' as DraftSide,
  R: 'RED' as DraftSide,
};

function buildSlots(banSides: DraftSide[], pickSides: DraftSide[]): DraftSlot[] {
  const banPos = { BLUE: 0, RED: 0 };
  const pickPos = { BLUE: 0, RED: 0 };
  const out: DraftSlot[] = [];

  for (const side of banSides) {
    const position = banPos[side];
    out.push({ side, isBan: true, position });
    banPos[side] += 1;
  }

  for (const side of pickSides) {
    const position = pickPos[side];
    out.push({ side, isBan: false, position });
    pickPos[side] += 1;
  }

  return out;
}

const SOLOQ_BAN_SIDES: DraftSide[] = [
  SIDES.B, SIDES.B, SIDES.R, SIDES.R, SIDES.B,
  SIDES.R, SIDES.B, SIDES.R, SIDES.B, SIDES.R,
];

const SOLOQ_PICK_SIDES: DraftSide[] = [
  SIDES.B, SIDES.R, SIDES.R, SIDES.B, SIDES.B,
  SIDES.R, SIDES.R, SIDES.B, SIDES.B, SIDES.R,
];

const SOLOQ_SEQUENCE = buildSlots(SOLOQ_BAN_SIDES, SOLOQ_PICK_SIDES);

// CLASH sequence is built manually to properly interleave ban/pick phases
// Tournament Draft: Ban Phase 1 -> Pick Phase 1 -> Ban Phase 2 -> Pick Phase 2
const CLASH_SEQUENCE: DraftSlot[] = [
  // Ban Phase 1 (turns 0-5): B, R, B, R, B, R
  { side: 'BLUE', isBan: true, position: 0 },
  { side: 'RED', isBan: true, position: 0 },
  { side: 'BLUE', isBan: true, position: 1 },
  { side: 'RED', isBan: true, position: 1 },
  { side: 'BLUE', isBan: true, position: 2 },
  { side: 'RED', isBan: true, position: 2 },
  // Pick Phase 1 (turns 6-11): B, R, R, B, B, R
  { side: 'BLUE', isBan: false, position: 0 },
  { side: 'RED', isBan: false, position: 0 },
  { side: 'RED', isBan: false, position: 1 },
  { side: 'BLUE', isBan: false, position: 1 },
  { side: 'BLUE', isBan: false, position: 2 },
  { side: 'RED', isBan: false, position: 2 },
  // Ban Phase 2 (turns 12-15): R, B, R, B
  { side: 'RED', isBan: true, position: 3 },
  { side: 'BLUE', isBan: true, position: 3 },
  { side: 'RED', isBan: true, position: 4 },
  { side: 'BLUE', isBan: true, position: 4 },
  // Pick Phase 2 (turns 16-19): R, B, B, R
  { side: 'RED', isBan: false, position: 3 },
  { side: 'BLUE', isBan: false, position: 3 },
  { side: 'BLUE', isBan: false, position: 4 },
  { side: 'RED', isBan: false, position: 4 },
];

export function getDraftSequence(mode: DraftMode): DraftSlot[] {
  return mode === 'CLASH' ? CLASH_SEQUENCE : SOLOQ_SEQUENCE;
}

export function getTurnFromSlot(mode: DraftMode, side: DraftSide, position: number, isBan: boolean): number {
  const seq = getDraftSequence(mode);
  return seq.findIndex((slot) => slot.side === side && slot.position === position && slot.isBan === isBan);
}
