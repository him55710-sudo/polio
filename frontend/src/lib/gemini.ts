export function getGemini(): never {
  throw new Error(
    'Client-side Gemini access is disabled. Route model calls through the backend so secrets are not exposed in the browser bundle.',
  );
}
