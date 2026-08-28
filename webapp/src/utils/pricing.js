/**
 * Цена за произвольный срок по лестнице тарифов.
 *
 * Плоская дневная ставка убила бы скидку за длительность: 180 дней по
 * месячной ставке стоили бы 594 ⭐ вместо нынешних 449 ⭐. Поэтому берём
 * ставку самого длинного тарифа, который уже «открыт» выбранным сроком,
 * и отдельно не даём цене превысить стоимость более длинного тарифа,
 * который и так покрывает этот срок — иначе 179 дней стоили бы дороже,
 * чем 180.
 *
 * @param {number} days   выбранный срок
 * @param {Array}  plans  тарифы (порядок любой, сортируем сами)
 * @param {"price"|"rub"} field  в звёздах или в рублях
 */
export function priceFor(days, plans, field) {
  const ladder = [...plans].sort((a, b) => a.days - b.days);
  const unlocked = ladder.filter((p) => p.days <= days).pop() || ladder[0];
  const rate = unlocked[field] / unlocked.days;
  const covering = ladder.find((p) => p.days >= days);
  const byRate = Math.round(days * rate);
  return Math.max(1, covering ? Math.min(byRate, covering[field]) : byRate);
}

/** Границы срока в шторке продления. */
export const DAYS_MIN = 7;
export const DAYS_MAX = 365;
export const DAYS_PRESETS = [30, 90, 180];

export const clampDays = (raw) =>
  Math.max(DAYS_MIN, Math.min(DAYS_MAX, Number(raw) || DAYS_MIN));
