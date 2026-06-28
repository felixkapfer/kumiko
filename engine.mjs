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

export function scoreQuestion(question, selectedIds = [], scoring = {}) {
  const options = question.options || [];
  const type = scoring?.type || "exact-match";
  const selected = new Set(selectedIds);
  const correctOptions = options.filter((option) => option.correct);
  const selectedCorrect = options.filter(
    (option) => option.correct && selected.has(option.id),
  ).length;
  const selectedIncorrect = options.filter(
    (option) => !option.correct && selected.has(option.id),
  ).length;
  const missedCorrect = correctOptions.length - selectedCorrect;

  if (type === "signed-selection") {
    const correctSelectedPoints = Number(scoring.correctSelected ?? 1);
    const incorrectSelectedPoints = Number(scoring.incorrectSelected ?? -1);
    const points =
      selectedCorrect * correctSelectedPoints +
      selectedIncorrect * incorrectSelectedPoints;
    const maximum = correctOptions.length * correctSelectedPoints;
    const correct =
      missedCorrect === 0 &&
      selectedIncorrect === 0 &&
      points === maximum;
    return {
      id: question.id,
      correct,
      points,
      maximum,
      selectedCorrect,
      selectedIncorrect,
      missedCorrect,
    };
  }

  const correct = exactMatch(selectedIds, options);
  return {
    id: question.id,
    correct,
    points: correct ? 1 : 0,
    maximum: 1,
    selectedCorrect,
    selectedIncorrect,
    missedCorrect,
  };
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

function questionMatchesExamGroup(question, group) {
  const topicIds = new Set(group.topicIds || []);
  const excludeTopicIds = new Set(group.excludeTopicIds || []);
  if (topicIds.size && !topicIds.has(question.topic)) return false;
  if (excludeTopicIds.has(question.topic)) return false;
  return true;
}

export function buildSplitExam(
  questions,
  count,
  groups = [],
  random = Math.random,
) {
  const limit = Math.min(Math.max(Number(count) || 0, 0), questions.length);
  if (!limit || !groups.length) return buildExam(questions, limit, random);

  const selected = [];
  const selectedIds = new Set();
  const targets = [];
  let assignedTarget = 0;

  groups.forEach((group, index) => {
    const isLast = index === groups.length - 1;
    const rawTarget =
      group.count !== undefined
        ? Number(group.count)
        : isLast
          ? limit - assignedTarget
          : Math.round(limit * Number(group.ratio || 0));
    const target = Math.max(
      0,
      Math.min(limit - assignedTarget, Number.isFinite(rawTarget) ? rawTarget : 0),
    );
    targets.push(target);
    assignedTarget += target;
  });

  if (assignedTarget < limit && targets.length) {
    targets[targets.length - 1] += limit - assignedTarget;
  }

  groups.forEach((group, index) => {
    const bucket = questions.filter(
      (question) =>
        !selectedIds.has(question.id) && questionMatchesExamGroup(question, group),
    );
    for (const question of buildExam(bucket, targets[index], random)) {
      if (!selectedIds.has(question.id)) {
        selected.push(question);
        selectedIds.add(question.id);
      }
    }
  });

  if (selected.length < limit) {
    const remaining = questions.filter((question) => !selectedIds.has(question.id));
    for (const question of buildExam(remaining, limit - selected.length, random)) {
      selected.push(question);
      selectedIds.add(question.id);
    }
  }

  return shuffle(selected, random);
}

export function scoreExam(questions, answers, scoring = {}) {
  const details = questions.map((question) =>
    scoreQuestion(question, answers[question.id] || [], scoring),
  );
  const points = details.reduce((sum, entry) => sum + entry.points, 0);
  const maximum = details.reduce((sum, entry) => sum + entry.maximum, 0);
  return {
    points,
    maximum,
    percentage: maximum
      ? Math.round((points / maximum) * 100)
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
