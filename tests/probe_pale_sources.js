const puppeteer = require('puppeteer');

(async () => {
  let browser;
  try {
    browser = await puppeteer.launch({
      executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
      headless: 'new',
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    const page = await browser.newPage();
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');

    const targets = [
      'https://www.jewishgen.org/Communities/Search.asp',
      'https://www.jewishgen.org/belarus/',
      'https://sztetl.org.pl/en/towns?country=BY',
      'https://dir.icm.edu.pl/Slownik_geograficzny/',
      'https://www.demoscope.ru/weekly/ssp/census.php'
    ];

    for (const url of targets) {
      try {
        const resp = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 25000 });
        await new Promise(r => setTimeout(r, 3000));
        const title = await page.title();
        const textLen = await page.evaluate(() => document.body ? document.body.innerText.length : 0);
        const snippet = await page.evaluate(() => document.body ? document.body.innerText.slice(0, 300).replace(/\s+/g, ' ') : '');
        console.log(`[${resp ? resp.status() : 'ERR'}] ${url} | title="${title}" | textLen=${textLen} | ${snippet}`);
      } catch (err) {
        console.log(`[ERR] ${url} | ${err.message}`);
      }
    }
  } finally {
    if (browser) await browser.close();
  }
})();
