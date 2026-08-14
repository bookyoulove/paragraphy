import logo from '../../../frontend_old/logo.png';

export default function Brand({ landing = false }) {
  return (
    <div className="brand-block">
      <div className={landing ? 'landing-badge' : 'brand-badge'}>
        <img src={logo} alt="Paragraphy" />
      </div>
      {!landing && <div className="brand-text">Paragraphy</div>}
    </div>
  );
}
