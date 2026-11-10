const { chromium } = require('playwright'); const fs = require('fs');
(async () => {
  const dir = process.argv[2], out = process.argv[3]; fs.mkdirSync(out, {recursive: true});
  const V = JSON.parse(fs.readFileSync('views3.json')); let LB = {};
  try { LB = JSON.parse(fs.readFileSync(dir + '/labels.json')); } catch (e) {}
  const b = await chromium.launch(); const p = await b.newPage({viewport: {width: 1440, height: 900}, deviceScaleFactor: 1});
  for (const v of V) {
    if (!fs.existsSync(dir + '/' + v.file + '.png')) continue;
    const labs = (LB[v.file] || []).filter(l => l[3] > 0).map(l => `<div class="l" style="left:${l[1] * 1440}px;top:${(1 - l[2]) * 900}px">${l[0]}</div>`).join('');
    const html = `<html><body style="margin:0;font-family:'WenQuanYi Zen Hei',sans-serif"><style>.l{position:absolute;transform:translate(-50%,-50%);font-size:13px;font-weight:700;background:rgba(255,255,255,.86);padding:2px 6px;border-radius:4px;white-space:nowrap}</style>
      <img src="file://${process.cwd()}/${dir}/${v.file}.png" style="width:1440px;height:900px;display:block">${labs}
      <div style="position:absolute;left:16px;top:12px;font-size:21px;font-weight:700;background:rgba(255,255,255,.82);padding:5px 12px;border-radius:6px">${v.title}</div>
      <div style="position:absolute;left:16px;bottom:12px;font-size:13px;background:rgba(255,255,255,.8);padding:4px 10px;border-radius:5px">${v.sub}</div></body></html>`;
    fs.writeFileSync('comp_tmp.html', html); await p.goto('file://' + process.cwd() + '/comp_tmp.html'); await p.waitForTimeout(700);
    await p.screenshot({path: out + '/' + v.file + '.jpg', type: 'jpeg', quality: 90});
  }
  await b.close();
})();
