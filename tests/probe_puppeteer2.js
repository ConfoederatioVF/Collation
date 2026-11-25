const puppeteer = require('puppeteer');

(async () => {
  let browser;
  try {
    browser = await puppeteer.launch({
      headless: true,
      executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
      args: ['--no-sandbox']
    });
    const page = await browser.newPage();
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');

    console.log('=== Checking osp.stat.gov.lt with wait ===');
    await page.goto('https://osp.stat.gov.lt/gyventoju-ir-bustu-surasymai1', { waitUntil: 'domcontentloaded', timeout: 30000 }).catch(e => console.log('err:', e.message));
    await new Promise(r => setTimeout(r, 15000));
    const res1 = await page.evaluate(() => ({
      title: document.title,
      url: location.href,
      text: document.body.innerText.slice(0, 1000),
      links: Array.from(document.querySelectorAll('a')).map(a => ({ t: a.innerText.trim(), h: a.href })).filter(x => /xlsx|csv|xls|zip|json|sura|gyvent|rodikl/i.test(x.h + ' ' + x.t)).slice(0, 25)
    }));
    console.log(JSON.stringify(res1, null, 2));

    console.log('=== Checking dir.icm.edu.pl/pl/Slownik_geograficzny/ ===');
    await page.goto('https://dir.icm.edu.pl/pl/Slownik_geograficzny/', { waitUntil: 'networkidle2', timeout: 30000 }).catch(e => console.log('err:', e.message));
    const res2 = await page.evaluate(() => ({
      title: document.title,
      text: document.body.innerText.slice(0, 800),
      links: Array.from(document.querySelectorAll('a')).map(a => ({ t: a.innerText.trim(), h: a.href })).slice(0, 20)
    }));
    console.log(JSON.stringify(res2, null, 2));
  } finally {
    if (browser) await browser.close();
  }
})();
