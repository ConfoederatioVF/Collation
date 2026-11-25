const puppeteer = require('puppeteer');

(async () => {
  let browser;
  try {
    browser = await puppeteer.launch({
      headless: true,
      executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
      args: ['--no-sandbox', '--ignore-certificate-errors']
    });
    const page = await browser.newPage();
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');

    await page.goto('https://stat.gov.lv/lv/statistikas-temas/iedzivotaji/iedzivotaju-skaits/publikacijas-un-infografikas/1302-ceturta-tautas', { waitUntil: 'networkidle2', timeout: 30000 }).catch(e => console.log('err1:', e.message));
    const r1 = await page.evaluate(() => ({
      title: document.title,
      text: document.body.innerText.slice(0, 2000),
      links: Array.from(document.querySelectorAll('a')).map(a => ({ t: a.innerText.trim(), h: a.href })).filter(x => /pdf|media|download|skait|1935|1930|1925|1920/i.test(x.h + ' ' + x.t)).slice(0, 30)
    }));
    console.log('=== 1302-ceturta-tautas ===');
    console.log(JSON.stringify(r1, null, 2));

    await page.goto('https://stat.gov.lv/lv/statistikas-temas/iedzivotaji/iedzivotaju-skaits/publikacijas-un-infografikas?title=tautas+skait%C4%AB%C5%A1ana', { waitUntil: 'networkidle2', timeout: 30000 }).catch(e => console.log('err2:', e.message));
    const r2 = await page.evaluate(() => ({
      links: Array.from(document.querySelectorAll('a')).map(a => ({ t: a.innerText.trim(), h: a.href })).filter(x => /tautas|skait|1920|1925|1930|1935|1959/i.test(x.h + ' ' + x.t)).slice(0, 30)
    }));
    console.log('=== search tautas skaitisana ===');
    console.log(JSON.stringify(r2, null, 2));
  } finally {
    if (browser) await browser.close();
  }
})();
