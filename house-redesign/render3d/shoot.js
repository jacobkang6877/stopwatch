const { chromium } = require('playwright');
const V = require('./views.json');
(async () => {
  const b = await chromium.launch({args:['--use-gl=angle','--use-angle=swiftshader','--ignore-gpu-blocklist']});
  const p = await b.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 2 });
  p.on('console', m => { if (m.type()==='error') console.log('ERR', m.text()); });
  p.on('pageerror', e => console.log('PAGEERR', e.message));
  await p.goto('http://127.0.0.1:8765/index.html');
  await p.waitForFunction('window.READY === true', null, {timeout: 120000});
  const only = process.argv.slice(2);
  for (const v of V) {
    if (only.length && !only.includes(v.file)) continue;
    await p.evaluate(v => window.renderView(v), v);
    await p.waitForTimeout(300);
    await p.screenshot({ path: __dirname + '/out/' + v.file + '.png' });
    console.log('shot', v.file);
  }
  await b.close();
})();
