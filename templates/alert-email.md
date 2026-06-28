<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body { font-family: -apple-system, sans-serif; line-height: 1.6; color: #1a1a1a; }
    .header { background: #dc2626; color: white; padding: 16px; border-radius: 8px; }
    .sku { background: #fef2f2; border-left: 4px solid #dc2626; padding: 16px; margin: 16px 0; }
    .action { background: #f0f9ff; padding: 12px; border-radius: 4px; margin: 8px 0; }
    .footer { color: #666; font-size: 12px; margin-top: 24px; }
  </style>
</head>
<body>
  <div class="header">
    <h2>⚠️ CPSC 高风险告警 - {date}</h2>
    <p>{high_risk_count} 个 SKU 需要立刻处理</p>
  </div>

  {for each high_risk_sku}
  <div class="sku">
    <h3>🔴 {sku_name} (ASIN: {asin})</h3>
    <p><strong>风险：</strong>{specific_risk}</p>
    <p><strong>截止：</strong>{deadline_date}（还剩 {days_left} 天）</p>
    <div class="action">
      <strong>立刻行动：</strong>
      <ol>
        <li>{action_1}</li>
        <li>{action_2}</li>
        <li>{action_3}</li>
      </ol>
    </div>
    <p><a href="{full_report_link}">查看完整报告 →</a></p>
  </div>
  {end for}

  <div class="footer">
    <p>本邮件由 CPSC 监控 Skill 自动发送</p>
    <p>完整报告：<a href="{full_report_link}">{full_report_link}</a></p>
    <p>取消订阅：回复"unsubscribe"</p>
  </div>
</body>
</html>