import Brand from './Brand';

export default function Landing({ onStart }) {
  return (
    <div className="landing-view">
      <div className="landing-inner">
        <Brand landing />
        <h1 className="landing-title">
          대학 채점 기준으로,
          <br />내 논술 점수를 바로 확인하세요
        </h1>
        <p className="landing-sub">
          대학별 모의논술과 국립국어원 논증적 글쓰기 주제로 직접 답안을 작성해보세요.
          <br />
          대학별 채점 기준을 바탕으로 점수부터 감점 이유, 개선할 부분까지 확인할 수 있습니다.
        </p>
        <button className="landing-cta" onClick={onStart}>
          Paragraphy 시작하기
        </button>
      </div>
    </div>
  );
}
