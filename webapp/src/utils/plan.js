// The backend's `plan_name` for a trial subscription is the literal string
// "Trial" — translate it for display without touching the value itself,
// since it's also used elsewhere (analytics, admin panel) in its original form.
export function planLabel(name) {
  return name === "Trial" ? "Пробный" : name;
}
