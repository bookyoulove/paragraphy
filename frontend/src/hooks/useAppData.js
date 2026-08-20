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

  const saveAnswer = useCallback(async (answer, options) => {
    if (!session) return;
    const updated = await api.saveAnswer(session, answer, options);
    setSession(updated);
    await refreshSessions();
    return updated;
  }, [refreshSessions, session]);

  const grade = useCallback(async (sessionToGrade) => {
    if (!sessionToGrade) return;
    const updated = await api.grade(sessionToGrade);
    setSession({ ...sessionToGrade, results: [...sessionToGrade.results, updated] });
    await refreshSessions();
  }, [refreshSessions]);

  const createProblem = useCallback(async (form) => {
    const created = await api.createProblem(form);
    await refreshProblems();
    return createSession(created);
  }, [createSession, refreshProblems]);

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
    createProblem,
    clear,
  };
}
