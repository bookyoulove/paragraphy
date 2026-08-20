import { Link } from 'react-router-dom';
import logo from '../assets/logo.png';

export default function Brand({ landing = false, link = true }) {
  const badge = (
    <div className={landing ? 'landing-badge' : 'brand-badge'}>
      <img src={logo} alt="Paragraphy" />
    </div>
  );
  const text = !landing && <div className="brand-text">Paragraphy</div>;
  if (landing || !link) {
    return (
      <div className="brand-block">
        {badge}
        {text}
      </div>
    );
  }
  return (
    <Link to="/problems" className="brand-block brand-link">
      {badge}
      {text}
    </Link>
  );
}
