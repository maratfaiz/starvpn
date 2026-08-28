/** Склонение дней: 1 день, 2 дня, 5 дней. */
export function dayWord(n) {
  const mod100 = Math.abs(n) % 100;
  if (mod100 >= 11 && mod100 <= 14) return "дней";
  switch (Math.abs(n) % 10) {
    case 1: return "день";
    case 2:
    case 3:
    case 4: return "дня";
    default: return "дней";
  }
}

/** «5 дней» одной строкой. */
export const days = (n) => `${n} ${dayWord(n)}`;
