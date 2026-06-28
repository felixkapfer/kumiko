async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error || `HTTP ${response.status}`);
  }
  return response.json();
}

export function fetchCatalog() {
  return requestJson("/api/catalog", { cache: "no-store" });
}

export function fetchState(courseId, examId) {
  const params = new URLSearchParams();
  if (courseId) params.set("course", courseId);
  if (examId) params.set("exam", examId);
  const query = params.size ? `?${params}` : "";
  return requestJson(`/api/state${query}`, { cache: "no-store" });
}

export function putState(payload) {
  return requestJson("/api/state", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function fetchExamContent(courseId, examId) {
  const course = encodeURIComponent(courseId);
  const exam = encodeURIComponent(examId);
  return requestJson(
    `/api/courses/${course}/exams/${exam}/content`,
    { cache: "no-store" },
  );
}
