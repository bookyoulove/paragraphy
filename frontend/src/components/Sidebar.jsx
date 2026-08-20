import { NavLink } from 'react-router-dom';

const items = [
  ['/problems', '문제 선택'],
  ['/history', '답안 기록'],
  ['/compare', '채점 비교'],
];
export default function Sidebar() {
  return (
    <nav className="sidebar">
      <ul className="sidebar-menu">
        {items.map(([path, label], index) => (
          <li key={path}>
            {index === 1 && <div className="sidebar-sep" />}
            <NavLink
              to={path}
              end={path === '/problems'}
              className={({ isActive }) => `sidebar-item ${isActive ? 'active' : ''}`}
            >
              {label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
