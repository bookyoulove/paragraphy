const items = [
  ['pick-existing', '문제 선택'],
  ['pick-custom', '문제 직접 입력'],
  ['history', '답안 기록'],
  ['compare', '채점 비교'],
];
export default function Sidebar({ active, onChange }) {
  return (
    <nav className="sidebar">
      <ul className="sidebar-menu">
        {items.map(([id, label], index) => (
          <li key={id}>
            {index === 2 && <div className="sidebar-sep" />}
            <button
              className={`sidebar-item ${active === id ? 'active' : ''}`}
              onClick={() => onChange(id)}
            >
              {label}
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
