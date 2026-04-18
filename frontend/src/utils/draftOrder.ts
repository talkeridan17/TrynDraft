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

const CLASH_BAN_SIDES: DraftSide[] = [
  SIDES.B, SIDES.R, SIDES.B, SIDES.R, SIDES.B, SIDES.R,
  SIDES.B, SIDES.R, SIDES.B, SIDES.R,
];

const CLASH_PICK_SIDES: DraftSide[] = [
  SIDES.B, SIDES.R, SIDES.R, SIDES.B, SIDES.B, SIDES.R,
  SIDES.R, SIDES.B, SIDES.B, SIDES.R,
];

const SOLOQ_SEQUENCE = buildSlots(SOLOQ_BAN_SIDES, SOLOQ_PICK_SIDES);
const CLASH_SEQUENCE = buildSlots(CLASH_BAN_SIDES, CLASH_PICK_SIDES);

export function getDraftSequence(mode: DraftMode): DraftSlot[] {
  return mode === 'CLASH' ? CLASH_SEQUENCE : SOLOQ_SEQUENCE;
}

export function getTurnFromSlot(mode: DraftMode, side: DraftSide, position: number, isBan: boolean): number {
  const seq = getDraftSequence(mode);
  return seq.findIndex((slot) => slot.side === side && slot.position === position && slot.isBan === isBan);
}
