export function findCourse(catalog, courseId) {
  return catalog?.courses?.find((course) => course.id === courseId) || null;
}

export function findExam(course, examId) {
  return course?.exams?.find((exam) => exam.id === examId) || null;
}

export function defaultContext(catalog) {
  const course = catalog?.courses?.[0];
  if (!course) throw new Error("No course is configured.");
  return {
    courseId: course.id,
    examId: course.defaultExamId || course.exams[0]?.id,
  };
}

export function normalizeContext(catalog, courseId, examId) {
  const fallback = defaultContext(catalog);
  const course = findCourse(catalog, courseId) ||
    findCourse(catalog, fallback.courseId);
  const exam = findExam(course, examId) ||
    findExam(course, course.defaultExamId) ||
    course.exams[0];
  return { courseId: course.id, examId: exam.id };
}
