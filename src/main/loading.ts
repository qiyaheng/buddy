/** 应用启动时（sidecar 就绪前）展示的加载页。 */
export function loadingDataUrl(): string {
  const html = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8" />
<style>
  html,body{margin:0;height:100%;background:#f5f6f8;font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;}
  .wrap{height:100%;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px;color:#1f2329;}
  .logo{width:52px;height:52px;border-radius:14px;background:linear-gradient(135deg,#4f7cff,#7b5cff);
    display:flex;align-items:center;justify-content:center;color:#fff;font-size:26px;font-weight:700;
    box-shadow:0 8px 24px rgba(79,124,255,.35);}
  .title{font-size:15px;font-weight:600;}
  .tip{font-size:12px;color:#8a8f99;}
  .spin{width:20px;height:20px;border:2.5px solid #d6dae0;border-top-color:#4f7cff;border-radius:50%;animation:s .8s linear infinite;}
  @keyframes s{to{transform:rotate(360deg)}}
</style></head>
<body><div class="wrap">
  <div class="logo">S</div>
  <div class="title">SMEbuddy 工作台</div>
  <div class="spin"></div>
  <div class="tip">正在启动本地引擎…</div>
</div></body></html>`
  return `data:text/html;charset=utf-8,${encodeURIComponent(html)}`
}
