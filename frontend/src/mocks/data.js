export const problems = [
  {
    id: 1,
    title: '한양대학교 2026 상경계열 모의논술',
    source: '한양대학교',
    meta: { school: '한양대학교', exam_type: '상경계열 모의논술', year: '2026' },
    content:
      '[문제] 시장의 효율성과 공정성은 언제 충돌하는지 설명하고, 이를 조정하기 위한 정책 방향을 논하시오.\n\n[제시문] 시장은 자원을 효율적으로 배분하지만, 출발선의 차이가 결과의 격차로 이어질 수 있다.',
    rubric: [
      {
        criteria: '제시문의 핵심 쟁점 파악',
        description: '제시문의 핵심 쟁점을 정확하게 파악한다.',
      },
      {
        criteria: '효율성과 공정성 분석',
        description: '효율성과 공정성의 관계를 논리적으로 분석한다.',
      },
      { criteria: '정책 대안 제시', description: '근거를 바탕으로 현실적인 정책 대안을 제시한다.' },
    ],
  },
  {
    id: 2,
    title: '국립국어원 논증적 글쓰기',
    source: '국립국어원',
    meta: { school: '국립국어원', exam_type: '논증적 글쓰기', year: '2026' },
    content:
      '인공지능의 교육 활용은 학습 격차를 줄이는가, 혹은 새로운 격차를 만드는가? 자신의 입장을 정하고 근거를 들어 논술하시오.',
    rubric: [
      { criteria: '입장 명확성', description: '입장이 명확하다.' },
      { criteria: '근거와 사례의 연결', description: '근거와 사례가 주장에 적절히 연결된다.' },
      { criteria: '반론 고려', description: '예상되는 반론을 고려하여 논지를 보완한다.' },
    ],
  },
];

export const starterAnswer =
  '시장 효율성과 공정성은 자원의 배분 기준이 달라질 때 충돌한다. 효율성만 강조하면 취약한 계층의 기회가 줄어들 수 있으므로, 국가는 교육과 사회 안전망을 통해 출발선의 격차를 완화해야 한다.';
