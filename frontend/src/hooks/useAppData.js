import { useCallback, useEffect, useState } from 'react';
import { api } from '../api/client';

export default function useAppData(user) {
  const [problems, setProblems] = useState([]);
  const [session, setSession] = useState(null);
  const [sessions, setSessions] = useState([]);

  const refreshProblems = useCallback(async () => {
    setProblems(await api.getProblems());
  }, []);

  const refreshSessions = useCallback(async () => {
    setSessions(await api.getSessions());
  }, []);

  useEffect(() => {
    if (!user) return;
    Promise.all([api.getProblems(), api.getSessions()]).then(([loadedProblems, loadedSessions]) => {
      setProblems(loadedProblems);
      setSessions(loadedSessions);
    });
  }, [user]);

  const createSession = useCallback(async (problem) => {
    const created = await api.createSession(problem);
    setSession(created);
    return created;
  }, []);

  const loadSession = useCallback(async (sessionId) => {
    const loaded = await api.getSession(sessionId);
    setSession(loaded);
    return loaded;
  }, []);

  const saveAnswer = useCallback(async (answer, pendingName) => {
    if (!session) return;
    const updated = await api.saveAnswer(session, answer, pendingName);
    setSession(updated);
    await refreshSessions();
    return updated;
  }, [refreshSessions, session]);

  const grade = useCallback(async (sessionToGrade) => {
    if (!sessionToGrade) return;
    const updated = await api.grade(sessionToGrade);
    setSession({
      ...sessionToGrade,
      results: [...sessionToGrade.results, updated],
      answers: sessionToGrade.answers.map((item) =>
        item.id === updated.answerId ? { ...item, result: updated } : item,
      ),
      answerSubmitted: true,
    });
    await refreshSessions();
  }, [refreshSessions]);

  const renameAnswer = useCallback(async (answerId, name) => {
    if (!answerId) return;
    await api.renameAnswer(session.id, answerId, name);
    setSession((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        answerName: prev.answerId === answerId ? name : prev.answerName,
        results: prev.results.map((item) =>
          item.answerId === answerId ? { ...item, name } : item,
        ),
        answers: prev.answers.map((item) =>
          item.id === answerId ? { ...item, name } : item,
        ),
      };
    });
  }, [session]);

  const deleteAnswer = useCallback(async (sessionId, answerId) => {
    await api.deleteAnswer(sessionId, answerId);
    const reloaded = await api.getSession(sessionId);
    setSession((prev) => (prev && prev.id === sessionId ? reloaded : prev));
    await refreshSessions();
    return reloaded;
  }, [refreshSessions]);

  const deleteSession = useCallback(async (sessionId) => {
    await api.deleteSession(sessionId);
    setSession((prev) => (prev && prev.id === sessionId ? null : prev));
    await refreshSessions();
  }, [refreshSessions]);

  const createProblem = useCallback(async (form) => {
    const created = await api.createProblem(form);
    await refreshProblems();
    return createSession(created);
  }, [createSession, refreshProblems]);

  const deleteProblem = useCallback(async (problemId) => {
    await api.deleteProblem(problemId);
    setSession((prev) => (prev && prev.problem.id === problemId ? null : prev));
    await Promise.all([refreshProblems(), refreshSessions()]);
  }, [refreshProblems, refreshSessions]);

  const clear = useCallback(() => {
    setProblems([]);
    setSession(null);
    setSessions([]);
  }, []);

  return {
    problems,
    session,
    sessions,
    refreshProblems,
    createSession,
    loadSession,
    saveAnswer,
    grade,
    renameAnswer,
    deleteAnswer,
    deleteSession,
    createProblem,
    deleteProblem,
    clear,
  };
}
