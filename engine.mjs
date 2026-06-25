export const DIFFICULTY_LABELS = {
  1: "Basis",
  2: "Leicht",
  3: "Mittel",
  4: "Schwer",
  5: "Extrem",
};

export const REVIEW_INTERVALS = [
  10 * 60 * 1000,
  60 * 60 * 1000,
  24 * 60 * 60 * 1000,
  3 * 24 * 60 * 60 * 1000,
  7 * 24 * 60 * 60 * 1000,
  14 * 24 * 60 * 60 * 1000,
  30 * 24 * 60 * 60 * 1000,
];

export function exactMatch(selectedIds, options) {
  const selected = new Set(selectedIds);
  const expected = new Set(
    options.filter((option) => option.correct).map((option) => option.id),
  );
  if (selected.size !== expected.size) return false;
  return [...expected].every((id) => selected.has(id));
}

export function updateProgress(previous = {}, correct, now = Date.now()) {
  const attempts = (previous.attempts || 0) + 1;
  const oldBox = previous.box || 0;
  const box = correct ? Math.min(6, oldBox + 1) : Math.max(0, oldBox - 2);
  const dueAt = now + REVIEW_INTERVALS[box];
  return {
    ...previous,
    attempts,
    correct: (previous.correct || 0) + (correct ? 1 : 0),
    wrong: (previous.wrong || 0) + (correct ? 0 : 1),
    streak: correct ? (previous.streak || 0) + 1 : 0,
    box,
    dueAt,
    lastAt: now,
    lastResult: correct,
  };
}

export function shuffle(items, random = Math.random) {
  const result = [...items];
  for (let index = result.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(random() * (index + 1));
    [result[index], result[swapIndex]] = [result[swapIndex], result[index]];
  }
  return result;
}

export function questionStatus(progress, now = Date.now()) {
  if (!progress?.attempts) return "new";
  if (progress.dueAt <= now) return "due";
  if (progress.lastResult === false) return "wrong";
  if ((progress.box || 0) >= 4) return "mastered";
  return "learning";
}

export function selectQuestions(
  questions,
  progressMap,
  filters,
  now = Date.now(),
) {
  const topics = new Set(filters.topics || []);
  const difficulties = new Set(
    (filters.difficulties || []).map((value) => Number(value)),
  );

  return questions.filter((question) => {
    if (topics.size && !topics.has(question.topic)) return false;
    if (difficulties.size && !difficulties.has(Number(question.difficulty))) {
      return false;
    }

    const progress = progressMap[question.id];
    const status = questionStatus(progress, now);
    switch (filters.status) {
      case "due":
        return status === "due" || status === "wrong";
      case "new":
        return status === "new";
      case "wrong":
        return progress?.lastResult === false;
      case "correct":
        return progress?.lastResult === true;
      case "mastered":
        return status === "mastered";
      default:
        return true;
    }
  });
}

export function buildExam(questions, count, random = Math.random) {
  const byTopic = new Map();
  for (const question of questions) {
    const bucket = byTopic.get(question.topic) || [];
    bucket.push(question);
    byTopic.set(question.topic, bucket);
  }

  const topicIds = shuffle([...byTopic.keys()], random);
  const selected = [];
  let cursor = 0;
  while (selected.length < Math.min(count, questions.length)) {
    const topic = topicIds[cursor % topicIds.length];
    const bucket = byTopic.get(topic);
    if (bucket.length) {
      const difficultyWeighted = [...bucket].sort(
        (a, b) => Number(b.difficulty) - Number(a.difficulty),
      );
      const pickIndex = Math.floor(random() * difficultyWeighted.length);
      selected.push(difficultyWeighted.splice(pickIndex, 1)[0]);
      byTopic.set(topic, difficultyWeighted);
    }
    cursor += 1;
    if (cursor > questions.length * topicIds.length) break;
  }
  return shuffle(selected, random);
}

export function scoreExam(questions, answers) {
  const details = questions.map((question) => ({
    id: question.id,
    correct: exactMatch(answers[question.id] || [], question.options),
  }));
  const points = details.filter((entry) => entry.correct).length;
  return {
    points,
    maximum: questions.length,
    percentage: questions.length
      ? Math.round((points / questions.length) * 100)
      : 0,
    details,
  };
}

export function masteryForTopic(questions, progressMap) {
  if (!questions.length) return 0;
  const earned = questions.reduce(
    (sum, question) => sum + Math.min(4, progressMap[question.id]?.box || 0),
    0,
  );
  return Math.round((earned / (questions.length * 4)) * 100);
}

export function formatDue(timestamp, now = Date.now()) {
  if (!timestamp || timestamp <= now) return "jetzt";
  const delta = timestamp - now;
  const minutes = Math.ceil(delta / 60000);
  if (minutes < 60) return `in ${minutes} Min.`;
  const hours = Math.ceil(minutes / 60);
  if (hours < 48) return `in ${hours} Std.`;
  return `in ${Math.ceil(hours / 24)} Tagen`;
}
