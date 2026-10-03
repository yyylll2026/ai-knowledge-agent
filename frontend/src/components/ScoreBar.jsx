/**
 * 相似度可视化
 * ------------------------------------------------------------
 * 这是本项目的"特色组件" —— 它把后端的 score 变成一眼能懂的东西。
 *
 * 为什么要显示阈值线？
 *   因为后端 MIN_SCORE=0.46，低于它的结果会被丢弃。
 *   把这条线画出来，用户就能直观理解"为什么我这个问题搜不到东西"——
 *   不是系统坏了，是相似度确实不够。
 */

const MIN_SCORE = 0.46   // 与后端 app/core/config.py 的 MIN_SCORE 保持一致

export function scoreTier(score) {
  if (score >= 0.55) return 'high'
  if (score >= MIN_SCORE) return 'mid'
  return 'low'
}

export function ScoreBar({ score, showThreshold = true }) {
  const tier = scoreTier(score)
  const pct = Math.max(0, Math.min(100, score * 100))

  return (
    <div className="score-bar-wrap">
      <div className="score-bar">
        <div className={`score-fill score-${tier}`} style={{ width: `${pct}%` }} />
        {showThreshold && (
          <div
            className="score-threshold"
            style={{ left: `${MIN_SCORE * 100}%` }}
            title={`阈值 ${MIN_SCORE}：低于此分数的结果不会返回`}
          />
        )}
      </div>
      <span className={`score-num score-${tier}`}>{score.toFixed(3)}</span>
    </div>
  )
}

/**
 * 空结果提示。
 * 这是很关键的一处 UX：检索返回 0 条不是错误，
 * 但用户会以为是错误，所以必须解释清楚。
 */
export function EmptyResult({ query, topK }) {
  return (
    <div className="empty-result">
      <div className="empty-icon">∅</div>
      <h3>没有找到足够相关的内容</h3>
      <p>
        查询「{query}」在前 {topK} 条结果中，相似度都低于阈值{' '}
        <code>{MIN_SCORE}</code>，因此没有返回。
      </p>
      <div className="empty-hints">
        <div className="hint-title">可以试试：</div>
        <ul>
          <li>换用更贴近文档原文的措辞（向量检索对措辞敏感）</li>
          <li>用更短的关键词，长疑问句会稀释相似度</li>
          <li>确认相关文档已经上传到知识库</li>
        </ul>
      </div>
    </div>
  )
}
