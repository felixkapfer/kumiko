const SUPPORTED_LANGUAGES = new Set(["de", "en"]);


export function changeLanguage(state, nextLanguage) {
  if (!SUPPORTED_LANGUAGES.has(nextLanguage)) {
    throw new Error(`Unsupported language '${nextLanguage}'.`);
  }
  if (state.language === nextLanguage) return false;
  state.language = nextLanguage;
  return true;
}
