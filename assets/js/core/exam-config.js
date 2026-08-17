import { buildExam, buildSplitExam, formatDue, scoreQuestion } from "../../../engine.mjs";
import { translated } from "./i18n.js";

export function scoringConfig(data) {
  return data?.scoring || { type: "exact-match" };
}

export function examConfig(data) {
  return data?.examConfig || {};
}

export function examDefaults(data) {
  return examConfig(data).defaults || {};
}

export function officialExamConfig(data) {
  return examConfig(data).official || {};
}

export function clampInteger(value, fallback, min, max) {
  const parsed = Number.parseInt(value, 10);
  const safe = Number.isFinite(parsed) ? parsed : fallback;
  return Math.min(Math.max(safe, min), max);
}

export function examSplitGroups(data, count) {
  const groups = examConfig(data).split || [];
  const official = officialExamConfig(data);
  const useOfficialCounts = Number(official.questionCount) === Number(count);
  return groups.map((group) => ({
    topicIds: group.topicIds || [],
    excludeTopicIds: group.excludeTopicIds || [],
    ratio: Number(group.ratio || 0),
    count: useOfficialCounts ? group.officialCount : undefined,
  }));
}

export function buildConfiguredExam(data, questions, count) {
  const groups = examSplitGroups(data, count);
  if (!groups.length) return buildExam(questions, count);
  return buildSplitExam(questions, count, groups);
}

export function applyExamDefaults(examSetup, data) {
  const defaults = data.examConfig?.defaults;
  if (!defaults) return;
  const questionCount = Number(defaults.questionCount);
  const durationMinutes = Number(defaults.durationMinutes);
  if (Number.isFinite(questionCount) && questionCount > 0) {
    examSetup.count = String(Math.min(questionCount, data.questions.length));
  }
  if (Number.isFinite(durationMinutes) && durationMinutes > 0) {
    examSetup.duration = String(durationMinutes);
  }
}

export function examSetupValues(data, examSetup, available) {
  const defaults = examDefaults(data);
  const countFallback = Number(defaults.questionCount || examSetup.count || 20);
  const durationFallback = Number(defaults.durationMinutes || examSetup.duration || 40);
  return {
    available,
    count: clampInteger(examSetup.count, countFallback, 1, Math.max(available, 1)),
    duration: clampInteger(examSetup.duration, durationFallback, 1, 240),
  };
}

export function examSplitSummary(data, language) {
  const split = examConfig(data).split || [];
  if (!split.length) return "";
  return split
    .map((group) => {
      const label = translated(group.label, language);
      const percentage = Math.round(Number(group.ratio || 0) * 100);
      const officialCount = group.officialCount ? ` / ${group.officialCount}` : "";
      return `${label}: ${percentage}%${officialCount}`;
    })
    .join(" · ");
}

export function scoringLabels(data, language) {
  const labels = scoringConfig(data).labels;
  return labels?.[language] || labels?.de || {};
}

export function signedSelectionScoring(data) {
  return scoringConfig(data).type === "signed-selection";
}

export function scoringNote(data, language) {
  const labels = scoringLabels(data, language);
  if (labels.note) return labels.note;
  return language === "de"
    ? "Markiere exakt alle richtigen Aussagen. Es können 0 bis alle Optionen richtig sein."
    : "Select exactly all correct statements. From 0 to all options may be correct.";
}

export function scoringShortLabel(data, language) {
  const labels = scoringLabels(data, language);
  if (labels.short) return labels.short;
  return language === "de"
    ? "Alles-oder-nichts-Wertung"
    : "All-or-nothing scoring";
}

export function fullCreditLabel(data, language) {
  if (signedSelectionScoring(data)) {
    return language === "de" ? "maximal" : "maximum";
  }
  return language === "de" ? "exakt richtig" : "exactly correct";
}

export function formatPoints(value, data) {
  if (!signedSelectionScoring(data)) return String(value);
  return value > 0 ? `+${value}` : String(value);
}

export function questionScore(data, question, selectedIds) {
  return scoreQuestion(question, selectedIds, scoringConfig(data));
}

export function dueLabel(timestamp, language) {
  if (language === "de") return formatDue(timestamp);
  if (!timestamp || timestamp <= Date.now()) return "now";
  const delta = timestamp - Date.now();
  const minutes = Math.ceil(delta / 60000);
  if (minutes < 60) return `in ${minutes} min`;
  const hours = Math.ceil(minutes / 60);
  if (hours < 48) return `in ${hours} h`;
  return `in ${Math.ceil(hours / 24)} days`;
}
