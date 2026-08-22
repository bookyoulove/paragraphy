import { useState } from 'react';

const NATIONAL_KOREAN_LANGUAGE_INSTITUTE = '국립국어원';

function compareKoreanText(left, right) {
  return left.localeCompare(right, 'ko-KR');
}

function compareProblemTitle(left, right) {
  return compareKoreanText(left.title, right.title);
}

function compareOfficialProblems(left, right) {
  const leftIsNational = left.raw.university === NATIONAL_KOREAN_LANGUAGE_INSTITUTE;
  const rightIsNational = right.raw.university === NATIONAL_KOREAN_LANGUAGE_INSTITUTE;
  if (leftIsNational !== rightIsNational) return leftIsNational ? 1 : -1;

  const leftSchool = left.raw.university?.trim() ?? '';
  const rightSchool = right.raw.university?.trim() ?? '';
  const leftHasSchool = Boolean(leftSchool);
  const rightHasSchool = Boolean(rightSchool);
  if (leftHasSchool !== rightHasSchool) return leftHasSchool ? -1 : 1;

  const schoolComparison = compareKoreanText(leftSchool, rightSchool);
  if (schoolComparison !== 0) return schoolComparison;

  const leftYear = Number(left.raw.year);
  const rightYear = Number(right.raw.year);
  const leftHasYear = Number.isFinite(leftYear);
  const rightHasYear = Number.isFinite(rightYear);
  if (leftHasYear !== rightHasYear) return leftHasYear ? -1 : 1;
  if (leftHasYear && leftYear !== rightYear) return leftYear - rightYear;
  return compareProblemTitle(left, right);
}

export default function ProblemPicker({ problems, selectedId, onSelect, onRefresh, onDelete }) {
  const [deletingId, setDeletingId] = useState(null);
  const personalizedProblems = problems.filter((problem) => problem.raw.source_report_id);
  const regularProblems = problems.filter((problem) => !problem.raw.source_report_id);
  const userProblems = regularProblems
    .filter((problem) => problem.raw.created_by_user)
    .sort(compareProblemTitle);
  const officialProblems = regularProblems
    .filter((problem) => !problem.raw.created_by_user)
    .sort(compareOfficialProblems);
  const sortedRegularProblems = [...userProblems, ...officialProblems];

  const removeProblem = async (event, problem) => {
    event.stopPropagation();
    if (
      !window.confirm(
        '정말 삭제하시겠습니까?\n이 문제로 작성한 답안과 채점 결과도 함께 삭제됩니다.',
      )
    )
      return;
    setDeletingId(problem.id);
    try {
      await onDelete(problem.id);
    } finally {
      setDeletingId(null);
    }
  };
  const renderDeletableProblem = (problem, meta, className = '') => (
    <div key={problem.id} className={`problem-card round-card ${className}`}>
      <button className="round-card-main" onClick={() => onSelect(problem)}>
        <span className="card-title">{problem.title}</span>
        <span className="card-meta">{meta}</span>
      </button>
      {onDelete && (
        <button
          className="ghost-btn round-delete-btn"
          disabled={deletingId === problem.id}
          onClick={(event) => removeProblem(event, problem)}
        >
          {deletingId === problem.id ? '삭제 중...' : '삭제'}
        </button>
      )}
    </div>
  );
  return (
    <div className="picker-view">
      <div className="picker-view-header">
        <div>
          <div className="label-title">문제 선택</div>
          <div className="label-sub">
            등록된 문제 중 하나를 선택하면 바로 답안 작성으로 이동합니다.
          </div>
        </div>
        <button className="ghost-btn" onClick={onRefresh}>
          문제 새로고침
        </button>
      </div>
      {personalizedProblems.length > 0 && (
        <section className="personalized-problem-section">
          <div className="personalized-problem-heading">AI 맞춤 문제</div>
          {personalizedProblems.map((problem) =>
            renderDeletableProblem(
              problem,
              '최근 분석 리포트를 바탕으로 취약한 부분을 보완하도록 만든 문제입니다.',
              'personalized-problem-card',
            ),
          )}
        </section>
      )}
      <div className="problem-list">
        {sortedRegularProblems.map((problem) => {
          const meta = [problem.meta.school, problem.meta.exam_type, problem.meta.year]
            .filter(Boolean)
            .join(' · ');
          if (problem.raw.created_by_user) {
            return renderDeletableProblem(
              problem,
              meta,
              selectedId === problem.id ? 'selected' : '',
            );
          }
          return (
            <button
              key={problem.id}
              className={`problem-card ${selectedId === problem.id ? 'selected' : ''}`}
              onClick={() => onSelect(problem)}
            >
              <span className="card-title">{problem.title}</span>
              <span className="card-meta">{meta}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
