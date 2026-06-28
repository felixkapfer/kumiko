const QUESTION_LANGUAGES = ["de", "en"];

export function hasLocalizedQuestionValue(value, language) {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    return typeof value[language] === "string" && value[language].trim() !== "";
  }
  return language === "de" && typeof value === "string" && value.trim() !== "";
}

export function questionSupportsLanguage(question, language) {
  if (!QUESTION_LANGUAGES.includes(language)) return false;
  if (!hasLocalizedQuestionValue(question.prompt, language)) return false;
  if (!hasLocalizedQuestionValue(question.explanation, language)) return false;
  if (
    question.context !== undefined &&
    !hasLocalizedQuestionValue(question.context, language)
  ) {
    return false;
  }
  return (
    Array.isArray(question.options) &&
    question.options.length >= 2 &&
    question.options.every(
      (option) =>
        hasLocalizedQuestionValue(option.text, language) &&
        hasLocalizedQuestionValue(option.explanation, language),
    )
  );
}

export function supportedQuestionLanguages(question) {
  return QUESTION_LANGUAGES.filter((language) =>
    questionSupportsLanguage(question, language),
  );
}
