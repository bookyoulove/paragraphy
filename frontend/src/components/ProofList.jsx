export default function ProofList({ errors }) {
  if (!errors.length) {
    return (
      <div className="proof-box">
        <div className="proof-tag">정보</div>
        <div className="proof-text">감지된 문법/맞춤법 오류가 없습니다.</div>
      </div>
    );
  }
  return (
    <>
      <div className="proof-count">감지된 오류 {errors.length}건</div>
      <div className="proof-list">
        {errors.map((item, index) => (
          <div className="proof-box" key={`${item.before}-${index}`}>
            <div className="proof-tag warning">{item.type}</div>
            <div className="proof-text">
              <del>{item.before}</del> → {item.after}
            </div>
            {item.note && <div className="proof-meta">{item.note}</div>}
            {item.ruleArticle && (
              <div className="proof-meta">
                <strong>관련 규정</strong> {item.ruleArticle}
              </div>
            )}
            {item.examples?.length > 0 && (
              <div className="proof-examples">
                <strong>예시</strong>
                <ul>
                  {item.examples.map((example) => (
                    <li key={example}>{example}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>
    </>
  );
}
